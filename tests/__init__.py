# coding: utf-8
import io
import os
import re
import shutil
import textwrap

from nose import SkipTest
from sqlalchemy.engine import default
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.util import decorator

import alembic
from alembic.compat import configparser
from alembic import util
from alembic.compat import string_types, text_type, u, py33
from alembic.migration import MigrationContext
from alembic.environment import EnvironmentContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory, Script
from alembic.ddl.impl import _impls
from contextlib import contextmanager

staging_directory = os.path.join(os.path.dirname(__file__), 'scratch')
files_directory = os.path.join(os.path.dirname(__file__), 'files')

testing_config = configparser.ConfigParser()
testing_config.read(['test.cfg'])

if py33:
    from unittest.mock import Mock, call
    from unittest import mock
else:
    try:
        from mock import Mock, call
        import mock
    except ImportError:
        raise ImportError(
                "Alembic's test suite requires the "
                "'mock' library as of 0.6.1.")


def sqlite_db():
    # sqlite caches table pragma info
    # per connection, so create a new
    # engine for each assertion
    dir_ = os.path.join(staging_directory, 'scripts')
    return create_engine('sqlite:///%s/foo.db' % dir_)

def capture_db():
    buf = []
    def dump(sql, *multiparams, **params):
        buf.append(str(sql.compile(dialect=engine.dialect)))
    engine = create_engine("postgresql://", strategy="mock", executor=dump)
    return engine, buf

_engs = {}
def db_for_dialect(name):
    if name in _engs:
        return _engs[name]
    else:
        try:
            cfg = testing_config.get("db", name)
        except configparser.NoOptionError:
            raise SkipTest("No dialect %r in test.cfg" % name)
        try:
            eng = create_engine(cfg, echo='debug')
        except ImportError as er1:
            raise SkipTest("Can't import DBAPI: %s" % er1)
        try:
            eng.connect()
        except SQLAlchemyError as er2:
            raise SkipTest("Can't connect to database: %s" % er2)
        _engs[name] = eng
        return eng


@decorator
def requires_08(fn, *arg, **kw):
    if not util.sqla_08:
        raise SkipTest("SQLAlchemy 0.8.0b2 or greater required")
    return fn(*arg, **kw)

@decorator
def requires_09(fn, *arg, **kw):
    if not util.sqla_09:
        raise SkipTest("SQLAlchemy 0.9 or greater required")
    return fn(*arg, **kw)

@decorator
def requires_092(fn, *arg, **kw):
    if not util.sqla_092:
        raise SkipTest("SQLAlchemy 0.9.2 or greater required")
    return fn(*arg, **kw)

@decorator
def requires_094(fn, *arg, **kw):
    if not util.sqla_094:
        raise SkipTest("SQLAlchemy 0.9.4 or greater required")
    return fn(*arg, **kw)

_dialects = {}
def _get_dialect(name):
    if name is None or name == 'default':
        return default.DefaultDialect()
    else:
        try:
            return _dialects[name]
        except KeyError:
            dialect_mod = getattr(__import__('sqlalchemy.dialects.%s' % name).dialects, name)
            _dialects[name] = d = dialect_mod.dialect()
            if name == 'postgresql':
                d.implicit_returning = True
            return d

def assert_compiled(element, assert_string, dialect=None):
    dialect = _get_dialect(dialect)
    eq_(
        text_type(element.compile(dialect=dialect)).\
                    replace("\n", "").replace("\t", ""),
        assert_string.replace("\n", "").replace("\t", "")
    )

@contextmanager
def capture_context_buffer(**kw):
    if kw.pop('bytes_io', False):
        buf = io.BytesIO()
    else:
        buf = io.StringIO()

    kw.update({
                'dialect_name': "sqlite",
                'output_buffer': buf
    })
    conf = EnvironmentContext.configure
    def configure(*arg, **opt):
        opt.update(**kw)
        return conf(*arg, **opt)

    with mock.patch.object(EnvironmentContext, "configure", configure):
        yield buf

def eq_ignore_whitespace(a, b, msg=None):
    a = re.sub(r'^\s+?|\n', "", a)
    a = re.sub(r' {2,}', " ", a)
    b = re.sub(r'^\s+?|\n', "", b)
    b = re.sub(r' {2,}', " ", b)
    assert a == b, msg or "%r != %r" % (a, b)

def eq_(a, b, msg=None):
    """Assert a == b, with repr messaging on failure."""
    assert a == b, msg or "%r != %r" % (a, b)

def ne_(a, b, msg=None):
    """Assert a != b, with repr messaging on failure."""
    assert a != b, msg or "%r == %r" % (a, b)

def is_(a, b, msg=None):
    """Assert a is b, with repr messaging on failure."""
    assert a is b, msg or "%r is not %r" % (a, b)

def assert_raises_message(except_cls, msg, callable_, *args, **kwargs):
    try:
        callable_(*args, **kwargs)
        assert False, "Callable did not raise an exception"
    except except_cls as e:
        assert re.search(msg, str(e)), "%r !~ %s" % (msg, e)
        print(text_type(e))

def op_fixture(dialect='default', as_sql=False, naming_convention=None):
    impl = _impls[dialect]
    class Impl(impl):
        def __init__(self, dialect, as_sql):
            self.assertion = []
            self.dialect = dialect
            self.as_sql = as_sql
            # TODO: this might need to
            # be more like a real connection
            # as tests get more involved
            self.connection = None
        def _exec(self, construct, *args, **kw):
            if isinstance(construct, string_types):
                construct = text(construct)
            assert construct.supports_execution
            sql = text_type(construct.compile(dialect=self.dialect))
            sql = re.sub(r'[\n\t]', '', sql)
            self.assertion.append(
                sql
            )

    opts = {}
    if naming_convention:
        if not util.sqla_092:
            raise SkipTest(
                        "naming_convention feature requires "
                        "sqla 0.9.2 or greater")
        opts['target_metadata'] = MetaData(naming_convention=naming_convention)

    class ctx(MigrationContext):
        def __init__(self, dialect='default', as_sql=False):
            self.dialect = _get_dialect(dialect)
            self.impl = Impl(self.dialect, as_sql)
            self.opts = opts
            self.as_sql = as_sql

        def assert_(self, *sql):
            # TODO: make this more flexible about
            # whitespace and such
            eq_(self.impl.assertion, list(sql))

        def assert_contains(self, sql):
            for stmt in self.impl.assertion:
                if sql in stmt:
                    return
            else:
                assert False, "Could not locate fragment %r in %r" % (
                    sql,
                    self.impl.assertion
                )
    context = ctx(dialect, as_sql)
    alembic.op._proxy = Operations(context)
    return context

def script_file_fixture(txt):
    dir_ = os.path.join(staging_directory, 'scripts')
    path = os.path.join(dir_, "script.py.mako")
    with open(path, 'w') as f:
        f.write(txt)

def env_file_fixture(txt):
    dir_ = os.path.join(staging_directory, 'scripts')
    txt = """
from alembic import context

config = context.config
""" + txt

    path = os.path.join(dir_, "env.py")
    pyc_path = util.pyc_file_from_path(path)
    if os.access(pyc_path, os.F_OK):
        os.unlink(pyc_path)

    with open(path, 'w') as f:
        f.write(txt)

def _sqlite_testing_config(sourceless=False):
    dir_ = os.path.join(staging_directory, 'scripts')
    return _write_config_file("""
[alembic]
script_location = %s
sqlalchemy.url = sqlite:///%s/foo.db
sourceless = %s

[loggers]
keys = root

[handlers]
keys = console

[logger_root]
level = WARN
handlers = console
qualname =

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatters]
keys = generic

[formatter_generic]
format = %%(levelname)-5.5s [%%(name)s] %%(message)s
datefmt = %%H:%%M:%%S
    """ % (dir_, dir_, "true" if sourceless else "false"))


def _no_sql_testing_config(dialect="postgresql", directives=""):
    """use a postgresql url with no host so that connections guaranteed to fail"""
    dir_ = os.path.join(staging_directory, 'scripts')
    return _write_config_file("""
[alembic]
script_location = %s
sqlalchemy.url = %s://
%s

[loggers]
keys = root

[handlers]
keys = console

[logger_root]
level = WARN
handlers = console
qualname =

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatters]
keys = generic

[formatter_generic]
format = %%(levelname)-5.5s [%%(name)s] %%(message)s
datefmt = %%H:%%M:%%S

""" % (dir_, dialect, directives))

def _write_config_file(text):
    cfg = _testing_config()
    with open(cfg.config_file_name, 'w') as f:
        f.write(text)
    return cfg

def _testing_config():
    from alembic.config import Config
    if not os.access(staging_directory, os.F_OK):
        os.mkdir(staging_directory)
    return Config(os.path.join(staging_directory, 'test_alembic.ini'))


def staging_env(create=True, template="generic", sourceless=False):
    from alembic import command, script
    cfg = _testing_config()
    if create:
        path = os.path.join(staging_directory, 'scripts')
        if os.path.exists(path):
            shutil.rmtree(path)
        command.init(cfg, path)
        if sourceless:
            try:
                # do an import so that a .pyc/.pyo is generated.
                util.load_python_file(path, 'env.py')
            except AttributeError:
                # we don't have the migration context set up yet
                # so running the .env py throws this exception.
                # theoretically we could be using py_compiler here to
                # generate .pyc/.pyo without importing but not really
                # worth it.
                pass
            make_sourceless(os.path.join(path, "env.py"))

    sc = script.ScriptDirectory.from_config(cfg)
    return sc

def clear_staging_env():
    shutil.rmtree(staging_directory, True)


def write_script(scriptdir, rev_id, content, encoding='ascii', sourceless=False):
    old = scriptdir._revision_map[rev_id]
    path = old.path

    content = textwrap.dedent(content)
    if encoding:
        content = content.encode(encoding)
    with open(path, 'wb') as fp:
        fp.write(content)
    pyc_path = util.pyc_file_from_path(path)
    if os.access(pyc_path, os.F_OK):
        os.unlink(pyc_path)
    script = Script._from_path(scriptdir, path)
    old = scriptdir._revision_map[script.revision]
    if old.down_revision != script.down_revision:
        raise Exception("Can't change down_revision "
                            "on a refresh operation.")
    scriptdir._revision_map[script.revision] = script
    script.nextrev = old.nextrev

    if sourceless:
        make_sourceless(path)

def make_sourceless(path):
    # note that if -O is set, you'd see pyo files here,
    # the pyc util function looks at sys.flags.optimize to handle this
    pyc_path = util.pyc_file_from_path(path)
    assert os.access(pyc_path, os.F_OK)

    # look for a non-pep3147 path here.
    # if not present, need to copy from __pycache__
    simple_pyc_path = util.simple_pyc_file_from_path(path)

    if not os.access(simple_pyc_path, os.F_OK):
        shutil.copyfile(pyc_path, simple_pyc_path)
    os.unlink(path)

def three_rev_fixture(cfg):
    a = util.rev_id()
    b = util.rev_id()
    c = util.rev_id()

    script = ScriptDirectory.from_config(cfg)
    script.generate_revision(a, "revision a", refresh=True)
    write_script(script, a, """\
"Rev A"
revision = '%s'
down_revision = None

from alembic import op

def upgrade():
    op.execute("CREATE STEP 1")

def downgrade():
    op.execute("DROP STEP 1")

""" % a)

    script.generate_revision(b, "revision b", refresh=True)
    write_script(script, b, u("""# coding: utf-8
"Rev B, méil"
revision = '%s'
down_revision = '%s'

from alembic import op

def upgrade():
    op.execute("CREATE STEP 2")

def downgrade():
    op.execute("DROP STEP 2")

""") % (b, a), encoding="utf-8")

    script.generate_revision(c, "revision c", refresh=True)
    write_script(script, c, """\
"Rev C"
revision = '%s'
down_revision = '%s'

from alembic import op

def upgrade():
    op.execute("CREATE STEP 3")

def downgrade():
    op.execute("DROP STEP 3")

""" % (c, b))
    return a, b, c
