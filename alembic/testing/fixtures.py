# coding: utf-8
from contextlib import contextmanager
import io
import re

from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import text

import alembic
from . import config
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
    if dialect == "mariadb":
        ctx_dialect = _get_dialect("mysql")
        ctx_dialect.server_version_info = (10, 0, 0, "MariaDB")

    else:
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


class AlterColRoundTripFixture(object):

    # since these tests are about syntax, use more recent SQLAlchemy as some of
    # the type / server default compare logic might not work on older
    # SQLAlchemy versions as seems to be the case for SQLAlchemy 1.1 on Oracle

    __requires__ = ("alter_column", "sqlalchemy_12")

    def setUp(self):
        self.conn = config.db.connect()
        self.ctx = MigrationContext.configure(self.conn)
        self.op = Operations(self.ctx)
        self.metadata = MetaData()

    def _compare_type(self, t1, t2):
        c1 = Column("q", t1)
        c2 = Column("q", t2)
        assert not self.ctx.impl.compare_type(
            c1, c2
        ), "Type objects %r and %r didn't compare as equivalent" % (t1, t2)

    def _compare_server_default(self, t1, s1, t2, s2):
        c1 = Column("q", t1, server_default=s1)
        c2 = Column("q", t2, server_default=s2)
        assert not self.ctx.impl.compare_server_default(
            c1, c2, s2, s1
        ), "server defaults %r and %r didn't compare as equivalent" % (s1, s2)

    def tearDown(self):
        self.metadata.drop_all(self.conn)
        self.conn.close()

    def _run_alter_col(self, from_, to_, compare=None):
        column = Column(
            from_.get("name", "colname"),
            from_.get("type", String(10)),
            nullable=from_.get("nullable", True),
            server_default=from_.get("server_default", None),
            # comment=from_.get("comment", None)
        )
        t = Table("x", self.metadata, column)

        t.create(self.conn)
        insp = inspect(self.conn)
        old_col = insp.get_columns("x")[0]

        # TODO: conditional comment support
        self.op.alter_column(
            "x",
            column.name,
            existing_type=column.type,
            existing_server_default=column.server_default
            if column.server_default is not None
            else False,
            existing_nullable=True if column.nullable else False,
            # existing_comment=column.comment,
            nullable=to_.get("nullable", None),
            # modify_comment=False,
            server_default=to_.get("server_default", False),
            new_column_name=to_.get("name", None),
            type_=to_.get("type", None),
        )

        insp = inspect(self.conn)
        new_col = insp.get_columns("x")[0]

        if compare is None:
            compare = to_

        eq_(
            new_col["name"],
            compare["name"] if "name" in compare else column.name,
        )
        self._compare_type(
            new_col["type"], compare.get("type", old_col["type"])
        )
        eq_(new_col["nullable"], compare.get("nullable", column.nullable))
        self._compare_server_default(
            new_col["type"],
            new_col.get("default", None),
            compare.get("type", old_col["type"]),
            compare["server_default"].text
            if "server_default" in compare
            else column.server_default.arg.text
            if column.server_default is not None
            else None,
        )
