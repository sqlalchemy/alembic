from sqlalchemy.engine import url, default
import shutil
import os
import itertools
from sqlalchemy import create_engine, text
from alembic import context, util
import re
from alembic.script import ScriptDirectory
from alembic.context import Context
from alembic import ddl
import StringIO
from alembic.ddl.impl import _impls

staging_directory = os.path.join(os.path.dirname(__file__), 'scratch')
files_directory = os.path.join(os.path.dirname(__file__), 'files')

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

def capture_context_buffer():
    buf = StringIO.StringIO()

    class capture(object):
        def __enter__(self):
            context._context_opts['output_buffer'] = buf
            return buf

        def __exit__(self, *arg, **kw):
            print buf.getvalue()
            context._context_opts.pop('output_buffer', None)

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

def _testing_config():
    from alembic.config import Config
    if not os.access(staging_directory, os.F_OK):
        os.mkdir(staging_directory)
    return Config(os.path.join(staging_directory, 'test_alembic.ini'))

def _op_fixture(dialect='default', as_sql=False):
    impl = _impls[dialect]
    class Impl(impl):
        def __init__(self, dialect, as_sql):
            self.assertion = []
            self.dialect = dialect
            self.as_sql = as_sql

        def _exec(self, construct, *args, **kw):
            if isinstance(construct, basestring):
                construct = text(construct)
            sql = unicode(construct.compile(dialect=self.dialect))
            sql = re.sub(r'[\n\t]', '', sql)
            self.assertion.append(
                sql
            )


    class ctx(Context):
        def __init__(self, dialect='default', as_sql=False):
            self.dialect = _get_dialect(dialect)
            self.impl = Impl(self.dialect, as_sql)

            context._context = self
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
    return ctx(dialect, as_sql)

def _env_file_fixture(txt):
    dir_ = os.path.join(staging_directory, 'scripts')
    txt = """
from alembic import context

config = context.config
""" + txt

    path = os.path.join(dir_, "env.py")
    pyc_path = util.pyc_file_from_path(path)
    if os.access(pyc_path, os.F_OK):
        os.unlink(pyc_path)

    file(path, 'w').write(txt)

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


def _no_sql_testing_config():
    """use a postgresql url with no host so that connections guaranteed to fail"""
    dir_ = os.path.join(staging_directory, 'scripts')
    return _write_config_file("""
[alembic]
script_location = %s
sqlalchemy.url = postgresql://

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

""" % (dir_))

def _write_config_file(text):
    cfg = _testing_config()
    open(cfg.config_file_name, 'w').write(text)
    return cfg

def sqlite_db():
    # sqlite caches table pragma info 
    # per connection, so create a new
    # engine for each assertion
    dir_ = os.path.join(staging_directory, 'scripts')
    return create_engine('sqlite:///%s/foo.db' % dir_)

def staging_env(create=True, template="generic"):
    from alembic import command, script
    cfg = _testing_config()
    if create:
        command.init(cfg, os.path.join(staging_directory, 'scripts'))
    return script.ScriptDirectory.from_config(cfg)

def clear_staging_env():
    shutil.rmtree(staging_directory, True)
    context._clear()

def three_rev_fixture(cfg):
    a = util.rev_id()
    b = util.rev_id()
    c = util.rev_id()

    script = ScriptDirectory.from_config(cfg)
    script.generate_rev(a, None)
    script.write(a, """
down_revision = None

from alembic.op import *

def upgrade():
    execute("CREATE STEP 1")

def downgrade():
    execute("DROP STEP 1")

""")

    script.generate_rev(b, None)
    script.write(b, """
down_revision = '%s'

from alembic.op import *

def upgrade():
    execute("CREATE STEP 2")

def downgrade():
    execute("DROP STEP 2")

""" % a)

    script.generate_rev(c, None)
    script.write(c, """
down_revision = '%s'

from alembic.op import *

def upgrade():
    execute("CREATE STEP 3")

def downgrade():
    execute("DROP STEP 3")

""" % b)
    return a, b, c