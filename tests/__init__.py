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

def _testing_options(**kw):
    from alembic.options import Options, get_option_parser
    if not os.access(staging_directory, os.F_OK):
        os.mkdir(staging_directory)
    kw.setdefault(
            'config', 
            os.path.join(staging_directory, 'test_alembic.ini')
        )

    return Options(
                get_option_parser(), 
                ["./scripts/alembic"] + \
                list(itertools.chain(*[["--%s" % k, "%s" % v] for k, v in kw.items()])) + \
                ["init"] +\
                [os.path.join(staging_directory, 'scripts')]
            )
    
def staging_env(create=True):
    from alembic import command, script
    opt = _testing_options()
    if create:
        command.init(opt)
    return script.ScriptDirectory.from_options(opt)
    
def clear_staging_env():
    shutil.rmtree(staging_directory, True)
    