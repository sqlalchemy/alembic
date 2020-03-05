from __future__ import absolute_import

import re

from sqlalchemy import util
from sqlalchemy.engine import default
from sqlalchemy.testing.assertions import _expect_warnings
from sqlalchemy.testing.assertions import eq_  # noqa
from sqlalchemy.testing.assertions import is_  # noqa
from sqlalchemy.testing.assertions import is_false  # noqa
from sqlalchemy.testing.assertions import is_not_  # noqa
from sqlalchemy.testing.assertions import is_true  # noqa
from sqlalchemy.testing.assertions import ne_  # noqa
from sqlalchemy.util import decorator

from ..util.compat import py3k


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
        assert re.search(msg, util.text_type(e), re.UNICODE), "%r !~ %s" % (
            msg,
            e,
        )
        print(util.text_type(e).encode("utf-8"))


def eq_ignore_whitespace(a, b, msg=None):
    # sqlalchemy.testing.assertion has this function
    # but not with the special "!U" detection part

    a = re.sub(r"^\s+?|\n", "", a)
    a = re.sub(r" {2,}", " ", a)
    b = re.sub(r"^\s+?|\n", "", b)
    b = re.sub(r" {2,}", " ", b)

    # convert for unicode string rendering,
    # using special escape character "!U"
    if py3k:
        b = re.sub(r"!U", "", b)
    else:
        b = re.sub(r"!U", "u", b)

    assert a == b, msg or "%r != %r" % (a, b)


_dialect_mods = {}


def _get_dialect(name):
    if name is None or name == "default":
        return default.DefaultDialect()
    else:
        try:
            dialect_mod = _dialect_mods[name]
        except KeyError:
            dialect_mod = getattr(
                __import__("sqlalchemy.dialects.%s" % name).dialects, name
            )
            _dialect_mods[name] = dialect_mod
        d = dialect_mod.dialect()
        if name == "postgresql":
            d.implicit_returning = True
        elif name == "mssql":
            d.legacy_schema_aliasing = False
        return d


def expect_warnings(*messages, **kw):
    """Context manager which expects one or more warnings.

    With no arguments, squelches all SAWarnings emitted via
    sqlalchemy.util.warn and sqlalchemy.util.warn_limited.   Otherwise
    pass string expressions that will match selected warnings via regex;
    all non-matching warnings are sent through.

    The expect version **asserts** that the warnings were in fact seen.

    Note that the test suite sets SAWarning warnings to raise exceptions.

    """
    return _expect_warnings(Warning, messages, **kw)


def emits_python_deprecation_warning(*messages):
    """Decorator form of expect_warnings().

    Note that emits_warning does **not** assert that the warnings
    were in fact seen.

    """

    @decorator
    def decorate(fn, *args, **kw):
        with _expect_warnings(DeprecationWarning, assert_=False, *messages):
            return fn(*args, **kw)

    return decorate
