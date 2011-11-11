from sqlalchemy.engine import url, default
import shutil
import os
import itertools
from sqlalchemy import create_engine, text
from alembic import context
import re
from alembic.context import _context_impls
from alembic import ddl
import StringIO

staging_directory = os.path.join(os.path.dirname(__file__), 'scratch')

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

def eq_(a, b, msg=None):
    """Assert a == b, with repr messaging on failure."""
    assert a == b, msg or "%r != %r" % (a, b)

def ne_(a, b, msg=None):
    """Assert a != b, with repr messaging on failure."""
    assert a != b, msg or "%r == %r" % (a, b)

def _testing_config():
    from alembic.config import Config
    if not os.access(staging_directory, os.F_OK):
        os.mkdir(staging_directory)
    return Config(os.path.join(staging_directory, 'test_alembic.ini'))

def _op_fixture(dialect='default', as_sql=False):
    _base = _context_impls[dialect]
    class ctx(_base):
        def __init__(self, dialect='default', as_sql=False):
            self._dialect = _get_dialect(dialect)

            context._context = self
            self.as_sql = as_sql
            self.assertion = []

        @property
        def dialect(self):
            return self._dialect

        def _exec(self, construct, *args, **kw):
            if isinstance(construct, basestring):
                construct = text(construct)
            sql = unicode(construct.compile(dialect=self.dialect))
            sql = re.sub(r'[\n\t]', '', sql)
            self.assertion.append(
                sql
            )

        def assert_(self, *sql):
            # TODO: make this more flexible about 
            # whitespace and such
            eq_(self.assertion, list(sql))
    return ctx(dialect, as_sql)

def _sqlite_testing_config():
    cfg = _testing_config()
    dir_ = os.path.join(staging_directory, 'scripts')
    open(cfg.config_file_name, 'w').write("""
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
    return cfg

def _no_sql_testing_config():
    """use a postgresql url with no host so that connections guaranteed to fail"""
    cfg = _testing_config()
    dir_ = os.path.join(staging_directory, 'scripts')
    open(cfg.config_file_name, 'w').write("""
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
    return cfg

def sqlite_db():
    # sqlite caches table pragma info 
    # per connection, so create a new
    # engine for each assertion
    dir_ = os.path.join(staging_directory, 'scripts')
    return create_engine('sqlite:///%s/foo.db' % dir_)

def staging_env(create=True):
    from alembic import command, script
    cfg = _testing_config()
    if create:
        command.init(cfg, os.path.join(staging_directory, 'scripts'))
    return script.ScriptDirectory.from_config(cfg)

def clear_staging_env():
    shutil.rmtree(staging_directory, True)
