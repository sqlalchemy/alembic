from __future__ import with_statement

from sqlalchemy.engine import url, default
import shutil
import os
import itertools
from sqlalchemy import create_engine, text, MetaData
from alembic import util
from alembic.migration import MigrationContext
from alembic.environment import EnvironmentContext
import re
import alembic
from alembic.operations import Operations
from alembic.script import ScriptDirectory, Script
from alembic import ddl
import StringIO
from alembic.ddl.impl import _impls
import ConfigParser
from nose import SkipTest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.util import decorator
import shutil
import textwrap

staging_directory = os.path.join(os.path.dirname(__file__), 'scratch')
files_directory = os.path.join(os.path.dirname(__file__), 'files')

testing_config = ConfigParser.ConfigParser()
testing_config.read(['test.cfg'])

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
        except ConfigParser.NoOptionError:
            raise SkipTest("No dialect %r in test.cfg" % name)
        try:
            eng = create_engine(cfg, echo=True)
        except ImportError, er1:
            raise SkipTest("Can't import DBAPI: %s" % er1)
        try:
            conn = eng.connect()
        except SQLAlchemyError, er2:
            raise SkipTest("Can't connect to database: %s" % er2)
        _engs[name] = eng
        return eng

@decorator
def requires_07(fn, *arg, **kw):
    if not util.sqla_07:
        raise SkipTest("SQLAlchemy 0.7 required")
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
            return d

def assert_compiled(element, assert_string, dialect=None):
    dialect = _get_dialect(dialect)
    eq_(
        unicode(element.compile(dialect=dialect)).\
                    replace("\n", "").replace("\t", ""),
        assert_string.replace("\n", "").replace("\t", "")
    )

def capture_context_buffer(**kw):
    buf = StringIO.StringIO()

    class capture(object):
        def __enter__(self):
            EnvironmentContext._default_opts = {
                'dialect_name':"sqlite",
                'output_buffer':buf
            }
            EnvironmentContext._default_opts.update(kw)
            return buf

        def __exit__(self, *arg, **kwarg):
            print buf.getvalue()
            EnvironmentContext._default_opts = None

    return capture()

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

def assert_raises_message(except_cls, msg, callable_, *args, **kwargs):
    try:
        callable_(*args, **kwargs)
        assert False, "Callable did not raise an exception"
    except except_cls, e:
        assert re.search(msg, str(e)), "%r !~ %s" % (msg, e)
        print str(e)

def op_fixture(dialect='default', as_sql=False):
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
            if isinstance(construct, basestring):
                construct = text(construct)
            sql = unicode(construct.compile(dialect=self.dialect))
            sql = re.sub(r'[\n\t]', '', sql)
            self.assertion.append(
                sql
            )


    class ctx(MigrationContext):
        def __init__(self, dialect='default', as_sql=False):
            self.dialect = _get_dialect(dialect)
            self.impl = Impl(self.dialect, as_sql)

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

def _sqlite_testing_config():
    dir_ = os.path.join(staging_directory, 'scripts')
    return _write_config_file("""
[alembic]
script_location = %s
sqlalchemy.url = sqlite:///%s/foo.db

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
    """ % (dir_, dir_))


def _no_sql_testing_config(dialect="postgresql"):
    """use a postgresql url with no host so that connections guaranteed to fail"""
    dir_ = os.path.join(staging_directory, 'scripts')
    return _write_config_file("""
[alembic]
script_location = %s
sqlalchemy.url = %s://

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

""" % (dir_, dialect))

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


def staging_env(create=True, template="generic"):
    from alembic import command, script
    cfg = _testing_config()
    if create:
        path = os.path.join(staging_directory, 'scripts')
        if os.path.exists(path):
            shutil.rmtree(path)
        command.init(cfg, path)
    sc = script.ScriptDirectory.from_config(cfg)
    return sc

def clear_staging_env():
    shutil.rmtree(staging_directory, True)


def write_script(scriptdir, rev_id, content):
    old = scriptdir._revision_map[rev_id]
    path = old.path
    with open(path, 'w') as fp:
        fp.write(textwrap.dedent(content))
    pyc_path = util.pyc_file_from_path(path)
    if os.access(pyc_path, os.F_OK):
        os.unlink(pyc_path)
    script = Script.from_path(path)
    old = scriptdir._revision_map[script.revision]
    if old.down_revision != script.down_revision:
        raise Exception("Can't change down_revision "
                            "on a refresh operation.")
    scriptdir._revision_map[script.revision] = script
    script.nextrev = old.nextrev


def three_rev_fixture(cfg):
    a = util.rev_id()
    b = util.rev_id()
    c = util.rev_id()

    script = ScriptDirectory.from_config(cfg)
    script.generate_rev(a, "revision a", refresh=True)
    write_script(script, a, """
revision = '%s'
down_revision = None

from alembic import op

def upgrade():
    op.execute("CREATE STEP 1")

def downgrade():
    op.execute("DROP STEP 1")

""" % a)

    script.generate_rev(b, "revision b", refresh=True)
    write_script(script, b, """
revision = '%s'
down_revision = '%s'

from alembic import op

def upgrade():
    op.execute("CREATE STEP 2")

def downgrade():
    op.execute("DROP STEP 2")

""" % (b, a))

    script.generate_rev(c, "revision c", refresh=True)
    write_script(script, c, """
revision = '%s'
down_revision = '%s'

from alembic import op

def upgrade():
    op.execute("CREATE STEP 3")

def downgrade():
    op.execute("DROP STEP 3")

""" % (c, b))
    return a, b, c