from sqlalchemy.util import defaultdict
from sqlalchemy.engine import url, default
import shutil
import os
import itertools
from sqlalchemy import create_engine

staging_directory = os.path.join(os.path.dirname(__file__), 'scratch')

_dialects = defaultdict(lambda name:url.URL(drivername).get_dialect()())
def _get_dialect(name):
    if name is None:
        return default.DefaultDialect()
    else:
        return _dialects[name]


def assert_compiled(element, assert_string, dialect=None):
    dialect = _get_dialect(dialect)
    eq_(
        unicode(element.compile(dialect=dialect)).replace("\n", "").replace("\t", ""),
        assert_string.replace("\n", "").replace("\t", "")
    )

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

def _sqlite_testing_config():
    cfg = _testing_config()
    dir_ = os.path.join(staging_directory, 'scripts')
    file(cfg.config_file_name, 'w').write("""
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
