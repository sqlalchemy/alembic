import re
from sqlalchemy.engine import default
from sqlalchemy.testing.assertions import eq_, ne_, is_, \
    assert_raises_message, assert_raises
from alembic.compat import text_type


def eq_ignore_whitespace(a, b, msg=None):
    a = re.sub(r'^\s+?|\n', "", a)
    a = re.sub(r' {2,}', " ", a)
    b = re.sub(r'^\s+?|\n', "", b)
    b = re.sub(r' {2,}', " ", b)
    assert a == b, msg or "%r != %r" % (a, b)


def assert_compiled(element, assert_string, dialect=None):
    dialect = _get_dialect(dialect)
    eq_(
        text_type(element.compile(dialect=dialect)).
        replace("\n", "").replace("\t", ""),
        assert_string.replace("\n", "").replace("\t", "")
    )


_dialects = {}


def _get_dialect(name):
    if name is None or name == 'default':
        return default.DefaultDialect()
    else:
        try:
            return _dialects[name]
        except KeyError:
            dialect_mod = getattr(
                __import__('sqlalchemy.dialects.%s' % name).dialects, name)
            _dialects[name] = d = dialect_mod.dialect()
            if name == 'postgresql':
                d.implicit_returning = True
            return d

