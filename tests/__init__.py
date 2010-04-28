from sqlalchemy.test.testing import eq_, ne_
from sqlalchemy.util import defaultdict
from sqlalchemy.engine import url, default
import shutil
import os
import itertools

staging_directory = os.path.join(os.path.dirname(__file__), 'scratch')

_dialects = defaultdict(lambda name:url.URL(drivername).get_dialect()())
def _get_dialect(name):
    if name is None:
        return default.DefaultDialect()
    else:
        return _dialects[name]
    
    
def assert_compiled(element, assert_string, dialect=None):
    dialect = _get_dialect(dialect)
    eq_(unicode(element.compile(dialect=dialect)), assert_string)

def _testing_config(**kw):
    from alembic.config import Config
    if not os.access(staging_directory, os.F_OK):
        os.mkdir(staging_directory)
    return Config(os.path.join(staging_directory, 'test_alembic.ini'))
    
def staging_env(create=True):
    from alembic import command, script
    cfg = _testing_config()
    if create:
        command.init(cfg, os.path.join(staging_directory, 'scripts'))
    return script.ScriptDirectory.from_config(cfg)
    
def clear_staging_env():
    shutil.rmtree(staging_directory, True)
    