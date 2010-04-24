from sqlalchemy.test.testing import eq_
from sqlalchemy.util import defaultdict
from sqlalchemy.engine import url, default

_dialects = defaultdict(lambda name:url.URL(drivername).get_dialect()())
def _get_dialect(name):
    if name is None:
        return default.DefaultDialect()
    else:
        return _dialects[name]
    
    
def assert_compiled(element, assert_string, dialect=None):
    dialect = _get_dialect(dialect)
    eq_(unicode(element.compile(dialect=dialect)), assert_string)