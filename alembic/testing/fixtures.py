# coding: utf-8
from contextlib import contextmanager
import io
import re

from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import text

import alembic
from . import mock
from .assertions import _get_dialect
from .assertions import eq_
from .plugin.plugin_base import SkipTest
from .. import util
from ..environment import EnvironmentContext
from ..migration import MigrationContext
from ..operations import Operations
from ..util.compat import configparser
from ..util.compat import string_types
from ..util.compat import text_type

testing_config = configparser.ConfigParser()
testing_config.read(["test.cfg"])


if not util.sqla_094:

    class TestBase(object):
        # A sequence of database names to always run, regardless of the
        # constraints below.
        __whitelist__ = ()

        # A sequence of requirement names matching testing.requires decorators
        __requires__ = ()

        # A sequence of dialect names to exclude from the test class.
        __unsupported_on__ = ()

        # If present, test class is only runnable for the *single* specified
        # dialect.  If you need multiple, use __unsupported_on__ and invert.
        __only_on__ = None

        # A sequence of no-arg callables. If any are True, the entire
        # testcase is skipped.
        __skip_if__ = None

        def assert_(self, val, msg=None):
            assert val, msg

        # apparently a handful of tests are doing this....OK
        def setup(self):
            if hasattr(self, "setUp"):
                self.setUp()

        def teardown(self):
            if hasattr(self, "tearDown"):
                self.tearDown()


else:
    from sqlalchemy.testing.fixtures import TestBase  # noqa


def capture_db():
    buf = []

    def dump(sql, *multiparams, **params):
        buf.append(str(sql.compile(dialect=engine.dialect)))

    engine = create_engine("postgresql://", strategy="mock", executor=dump)
    return engine, buf


_engs = {}


@contextmanager
def capture_context_buffer(**kw):
    if kw.pop("bytes_io", False):
        buf = io.BytesIO()
    else:
        buf = io.StringIO()

    kw.update({"dialect_name": "sqlite", "output_buffer": buf})
    conf = EnvironmentContext.configure

    def configure(*arg, **opt):
        opt.update(**kw)
        return conf(*arg, **opt)

    with mock.patch.object(EnvironmentContext, "configure", configure):
        yield buf


def op_fixture(
    dialect="default",
    as_sql=False,
    naming_convention=None,
    literal_binds=False,
    native_boolean=None,
):

    opts = {}
    if naming_convention:
        if not util.sqla_092:
            raise SkipTest(
                "naming_convention feature requires " "sqla 0.9.2 or greater"
            )
        opts["target_metadata"] = MetaData(naming_convention=naming_convention)

    class buffer_(object):
        def __init__(self):
            self.lines = []

        def write(self, msg):
            msg = msg.strip()
            msg = re.sub(r"[\n\t]", "", msg)
            if as_sql:
                # the impl produces soft tabs,
                # so search for blocks of 4 spaces
                msg = re.sub(r"    ", "", msg)
                msg = re.sub(r"\;\n*$", "", msg)

            self.lines.append(msg)

        def flush(self):
            pass

    buf = buffer_()

    class ctx(MigrationContext):
        def clear_assertions(self):
            buf.lines[:] = []

        def assert_(self, *sql):
            # TODO: make this more flexible about
            # whitespace and such
            eq_(buf.lines, list(sql))

        def assert_contains(self, sql):
            for stmt in buf.lines:
                if sql in stmt:
                    return
            else:
                assert False, "Could not locate fragment %r in %r" % (
                    sql,
                    buf.lines,
                )

    if as_sql:
        opts["as_sql"] = as_sql
    if literal_binds:
        opts["literal_binds"] = literal_binds
    ctx_dialect = _get_dialect(dialect)
    if native_boolean is not None:
        ctx_dialect.supports_native_boolean = native_boolean
        # this is new as of SQLAlchemy 1.2.7 and is used by SQL Server,
        # which breaks assumptions in the alembic test suite
        ctx_dialect.non_native_boolean_check_constraint = True
    if not as_sql:

        def execute(stmt, *multiparam, **param):
            if isinstance(stmt, string_types):
                stmt = text(stmt)
            assert stmt.supports_execution
            sql = text_type(stmt.compile(dialect=ctx_dialect))

            buf.write(sql)

        connection = mock.Mock(dialect=ctx_dialect, execute=execute)
    else:
        opts["output_buffer"] = buf
        connection = None
    context = ctx(ctx_dialect, connection, opts)

    alembic.op._proxy = Operations(context)
    return context
