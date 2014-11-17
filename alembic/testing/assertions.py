import re
from alembic import util
from sqlalchemy.engine import default
from alembic.compat import text_type, py3k

if not util.sqla_094:
    def eq_(a, b, msg=None):
        """Assert a == b, with repr messaging on failure."""
        assert a == b, msg or "%r != %r" % (a, b)

    def ne_(a, b, msg=None):
        """Assert a != b, with repr messaging on failure."""
        assert a != b, msg or "%r == %r" % (a, b)

    def is_(a, b, msg=None):
        """Assert a is b, with repr messaging on failure."""
        assert a is b, msg or "%r is not %r" % (a, b)

    def assert_raises(except_cls, callable_, *args, **kw):
        try:
            callable_(*args, **kw)
            success = False
        except except_cls:
            success = True

        # assert outside the block so it works for AssertionError too !
        assert success, "Callable did not raise an exception"

    def assert_raises_message(except_cls, msg, callable_, *args, **kwargs):
        try:
            callable_(*args, **kwargs)
            assert False, "Callable did not raise an exception"
        except except_cls as e:
            assert re.search(
                msg, text_type(e), re.UNICODE), "%r !~ %s" % (msg, e)
            print(text_type(e).encode('utf-8'))

else:
    from sqlalchemy.testing.assertions import eq_, ne_, is_, \
        assert_raises_message, assert_raises


def eq_ignore_whitespace(a, b, msg=None):
    a = re.sub(r'^\s+?|\n', "", a)
    a = re.sub(r' {2,}', " ", a)
    b = re.sub(r'^\s+?|\n', "", b)
    b = re.sub(r' {2,}', " ", b)

    # convert for unicode string rendering,
    # using special escape character "!U"
    if py3k:
        b = re.sub(r'!U', '', b)
    else:
        b = re.sub(r'!U', 'u', b)

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

