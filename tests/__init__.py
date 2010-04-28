from sqlalchemy.test.testing import eq_
from sqlalchemy.util import defaultdict
from sqlalchemy.engine import url, default
import shutil
import os
import itertools

testing_directory = os.path.join(os.path.dirname(__file__), 'scratch')

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
    os.mkdir(testing_directory)
    kw.setdefault(
            'config', 
            os.path.join(testing_directory, 'test_alembic.ini')
        )
    return Options(
                get_option_parser(), 
                list(itertools.chain(*[["--%s" % k, "%r" % v] for k, v in kw.items()]) )
                + [os.path.join(testing_directory, 'scripts')]
            )
    
def _testing_env():
    from alembic import command, script
    opt = _testing_options()
    command.init(opt)
    return script.ScriptDirectory.from_options(opt)
    
def _clear_testing_directory():
    shutil.rmtree(testing_directory, True)
    