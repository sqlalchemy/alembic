from __future__ import annotations

import configparser
from contextlib import contextmanager
import io
import os
import re
import shutil
from typing import Any
from typing import Dict
from typing import Generator
from typing import Literal
from typing import overload

from sqlalchemy import Column
from sqlalchemy import create_mock_engine
from sqlalchemy import inspect
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import testing
from sqlalchemy import text
from sqlalchemy.testing import config
from sqlalchemy.testing import mock
from sqlalchemy.testing.assertions import eq_
from sqlalchemy.testing.fixtures import FutureEngineMixin
from sqlalchemy.testing.fixtures import TablesTest as SQLAlchemyTablesTest
from sqlalchemy.testing.fixtures import TestBase as SQLAlchemyTestBase

import alembic
from .assertions import _get_dialect
from .env import _get_staging_directory
from ..environment import EnvironmentContext
from ..migration import MigrationContext
from ..operations import Operations
from ..util import sqla_compat
from ..util.sqla_compat import sqla_2

testing_config = configparser.ConfigParser()
testing_config.read(["test.cfg"])


class TestBase(SQLAlchemyTestBase):
    is_sqlalchemy_future = sqla_2

    @testing.fixture()
    def clear_staging_dir(self):
        yield
        location = _get_staging_directory()
        for filename in os.listdir(location):
            file_path = os.path.join(location, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

    @contextmanager
    def pushd(self, dirname) -> Generator[None, None, None]:
        current_dir = os.getcwd()
        try:
            os.chdir(dirname)
            yield
        finally:
            os.chdir(current_dir)

    @testing.fixture()
    def pop_alembic_config_env(self):
        yield
        os.environ.pop("ALEMBIC_CONFIG", None)

    @testing.fixture()
    def ops_context(self, migration_context):
        with migration_context.begin_transaction(_per_migration=True):
            yield Operations(migration_context)

    @testing.fixture
    def migration_context(self, connection):
        return MigrationContext.configure(
            connection, opts=dict(transaction_per_migration=True)
        )

    @testing.fixture
    def as_sql_migration_context(self, connection):
        return MigrationContext.configure(
            connection, opts=dict(transaction_per_migration=True, as_sql=True)
        )

    @testing.fixture
    def connection(self):
        with config.db.connect() as conn:
            yield conn


class TablesTest(TestBase, SQLAlchemyTablesTest):
    pass


FutureEngineMixin.is_sqlalchemy_future = True


def capture_db(dialect="postgresql://"):
    buf = []

    def dump(sql, *multiparams, **params):
        buf.append(str(sql.compile(dialect=engine.dialect)))

    engine = create_mock_engine(dialect, dump)
    return engine, buf


_engs: Dict[Any, Any] = {}


@overload
@contextmanager
def capture_context_buffer(
    bytes_io: Literal[True], **kw: Any
) -> Generator[io.BytesIO, None, None]: ...


@overload
@contextmanager
def capture_context_buffer(
    **kw: Any,
) -> Generator[io.StringIO, None, None]: ...


@contextmanager
def capture_context_buffer(
    **kw: Any,
) -> Generator[io.StringIO | io.BytesIO, None, None]:
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


@contextmanager
def capture_engine_context_buffer(
    **kw: Any,
) -> Generator[io.StringIO, None, None]:
    from .env import _sqlite_file_db
    from sqlalchemy import event

    buf = io.StringIO()

    eng = _sqlite_file_db()

    conn = eng.connect()

    @event.listens_for(conn, "before_cursor_execute")
    def bce(conn, cursor, statement, parameters, context, executemany):
        buf.write(statement + "\n")

    kw.update({"connection": conn})
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
        opts["target_metadata"] = MetaData(naming_convention=naming_convention)

    class buffer_:
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
        def get_buf(self):
            return buf

        def clear_assertions(self):
            buf.lines[:] = []

        def assert_(self, *sql):
            # TODO: make this more flexible about
            # whitespace and such
            eq_(buf.lines, [re.sub(r"[\n\t]", "", s) for s in sql])

        def assert_contains(self, sql):
            for stmt in buf.lines:
                if re.sub(r"[\n\t]", "", sql) in stmt:
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
            if isinstance(stmt, str):
                stmt = text(stmt)
            assert stmt.supports_execution
            sql = str(stmt.compile(dialect=ctx_dialect))

            buf.write(sql)

        connection = mock.Mock(dialect=ctx_dialect, execute=execute)
    else:
        opts["output_buffer"] = buf
        connection = None
    context = ctx(ctx_dialect, connection, opts)

    alembic.op._proxy = Operations(context)
    return context


class AlterColRoundTripFixture:
    # since these tests are about syntax, use more recent SQLAlchemy as some of
    # the type / server default compare logic might not work on older
    # SQLAlchemy versions as seems to be the case for SQLAlchemy 1.1 on Oracle

    __requires__ = ("alter_column",)

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
        sqla_compat._safe_rollback_connection_transaction(self.conn)
        with self.conn.begin():
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

        with sqla_compat._ensure_scope_for_ddl(self.conn):
            t.create(self.conn)
            insp = inspect(self.conn)
            old_col = insp.get_columns("x")[0]

            # TODO: conditional comment support
            self.op.alter_column(
                "x",
                column.name,
                existing_type=column.type,
                existing_server_default=(
                    column.server_default
                    if column.server_default is not None
                    else False
                ),
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
            (
                compare["server_default"].text
                if "server_default" in compare
                else (
                    column.server_default.arg.text
                    if column.server_default is not None
                    else None
                )
            ),
        )
