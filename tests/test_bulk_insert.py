from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import text
from sqlalchemy.sql import column
from sqlalchemy.sql import table
from sqlalchemy.types import TypeEngine

from alembic import op
from alembic.migration import MigrationContext
from alembic.testing import assert_raises_message
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing.fixtures import op_fixture
from alembic.testing.fixtures import TestBase


class BulkInsertTest(TestBase):
    def _table_fixture(self, dialect, as_sql):
        context = op_fixture(dialect, as_sql)
        t1 = table(
            "ins_table",
            column("id", Integer),
            column("v1", String()),
            column("v2", String()),
        )
        return context, t1

    def _big_t_table_fixture(self, dialect, as_sql):
        context = op_fixture(dialect, as_sql)
        t1 = Table(
            "ins_table",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("v1", String()),
            Column("v2", String()),
        )
        return context, t1

    def _test_bulk_insert(self, dialect, as_sql):
        context, t1 = self._table_fixture(dialect, as_sql)

        op.bulk_insert(
            t1,
            [
                {"id": 1, "v1": "row v1", "v2": "row v5"},
                {"id": 2, "v1": "row v2", "v2": "row v6"},
                {"id": 3, "v1": "row v3", "v2": "row v7"},
                {"id": 4, "v1": "row v4", "v2": "row v8"},
            ],
        )
        return context

    def _test_bulk_insert_single(self, dialect, as_sql):
        context, t1 = self._table_fixture(dialect, as_sql)

        op.bulk_insert(t1, [{"id": 1, "v1": "row v1", "v2": "row v5"}])
        return context

    def _test_bulk_insert_single_bigt(self, dialect, as_sql):
        context, t1 = self._big_t_table_fixture(dialect, as_sql)

        op.bulk_insert(t1, [{"id": 1, "v1": "row v1", "v2": "row v5"}])
        return context

    def test_bulk_insert(self):
        context = self._test_bulk_insert("default", False)
        context.assert_(
            "INSERT INTO ins_table (id, v1, v2) VALUES (:id, :v1, :v2)"
        )

    def test_bulk_insert_wrong_cols(self):
        context = op_fixture("postgresql")
        t1 = table(
            "ins_table",
            column("id", Integer),
            column("v1", String()),
            column("v2", String()),
        )
        op.bulk_insert(t1, [{"v1": "row v1"}])
        context.assert_(
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (%(id)s, %(v1)s, %(v2)s)"
        )

    def test_bulk_insert_no_rows(self):
        context, t1 = self._table_fixture("default", False)

        op.bulk_insert(t1, [])
        context.assert_()

    def test_bulk_insert_pg(self):
        context = self._test_bulk_insert("postgresql", False)
        context.assert_(
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (%(id)s, %(v1)s, %(v2)s)"
        )

    def test_bulk_insert_pg_single(self):
        context = self._test_bulk_insert_single("postgresql", False)
        context.assert_(
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (%(id)s, %(v1)s, %(v2)s)"
        )

    def test_bulk_insert_pg_single_as_sql(self):
        context = self._test_bulk_insert_single("postgresql", True)
        context.assert_(
            "INSERT INTO ins_table (id, v1, v2) VALUES (1, 'row v1', 'row v5')"
        )

    def test_bulk_insert_pg_single_big_t_as_sql(self):
        context = self._test_bulk_insert_single_bigt("postgresql", True)
        context.assert_(
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (1, 'row v1', 'row v5')"
        )

    def test_bulk_insert_mssql(self):
        context = self._test_bulk_insert("mssql", False)
        context.assert_(
            "INSERT INTO ins_table (id, v1, v2) VALUES (:id, :v1, :v2)"
        )

    def test_bulk_insert_inline_literal_as_sql(self):
        context = op_fixture("postgresql", True)

        class MyType(TypeEngine):
            pass

        t1 = table("t", column("id", Integer), column("data", MyType()))

        op.bulk_insert(
            t1,
            [
                {"id": 1, "data": op.inline_literal("d1")},
                {"id": 2, "data": op.inline_literal("d2")},
            ],
        )
        context.assert_(
            "INSERT INTO t (id, data) VALUES (1, 'd1')",
            "INSERT INTO t (id, data) VALUES (2, 'd2')",
        )

    def test_bulk_insert_as_sql(self):
        context = self._test_bulk_insert("default", True)
        context.assert_(
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (1, 'row v1', 'row v5')",
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (2, 'row v2', 'row v6')",
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (3, 'row v3', 'row v7')",
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (4, 'row v4', 'row v8')",
        )

    def test_bulk_insert_as_sql_pg(self):
        context = self._test_bulk_insert("postgresql", True)
        context.assert_(
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (1, 'row v1', 'row v5')",
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (2, 'row v2', 'row v6')",
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (3, 'row v3', 'row v7')",
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (4, 'row v4', 'row v8')",
        )

    def test_bulk_insert_as_sql_mssql(self):
        context = self._test_bulk_insert("mssql", True)
        # SQL server requires IDENTITY_INSERT
        # TODO: figure out if this is safe to enable for a table that
        # doesn't have an IDENTITY column
        context.assert_(
            "SET IDENTITY_INSERT ins_table ON",
            "GO",
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (1, 'row v1', 'row v5')",
            "GO",
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (2, 'row v2', 'row v6')",
            "GO",
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (3, 'row v3', 'row v7')",
            "GO",
            "INSERT INTO ins_table (id, v1, v2) "
            "VALUES (4, 'row v4', 'row v8')",
            "GO",
            "SET IDENTITY_INSERT ins_table OFF",
            "GO",
        )

    def test_bulk_insert_from_new_table(self):
        context = op_fixture("postgresql", True)
        t1 = op.create_table(
            "ins_table",
            Column("id", Integer),
            Column("v1", String()),
            Column("v2", String()),
        )
        op.bulk_insert(
            t1,
            [
                {"id": 1, "v1": "row v1", "v2": "row v5"},
                {"id": 2, "v1": "row v2", "v2": "row v6"},
            ],
        )
        context.assert_(
            "CREATE TABLE ins_table (id INTEGER, v1 VARCHAR, v2 VARCHAR)",
            "INSERT INTO ins_table (id, v1, v2) VALUES "
            "(1, 'row v1', 'row v5')",
            "INSERT INTO ins_table (id, v1, v2) VALUES "
            "(2, 'row v2', 'row v6')",
        )

    def test_invalid_format(self):
        context, t1 = self._table_fixture("sqlite", False)
        assert_raises_message(
            TypeError, "List expected", op.bulk_insert, t1, {"id": 5}
        )

        assert_raises_message(
            TypeError,
            "List of dictionaries expected",
            op.bulk_insert,
            t1,
            [(5,)],
        )


class RoundTripTest(TestBase):
    __only_on__ = "sqlite"

    def setUp(self):
        self.conn = config.db.connect()
        with self.conn.begin():
            self.conn.execute(
                text(
                    """
                create table foo(
                    id integer primary key,
                    data varchar(50),
                    x integer
                )
            """
                )
            )
        context = MigrationContext.configure(self.conn)
        self.op = op.Operations(context)
        self.t1 = table("foo", column("id"), column("data"), column("x"))

        self.trans = self.conn.begin()

    def tearDown(self):
        self.trans.rollback()
        with self.conn.begin():
            self.conn.execute(text("drop table foo"))
        self.conn.close()

    def test_single_insert_round_trip(self):
        self.op.bulk_insert(self.t1, [{"data": "d1", "x": "x1"}])

        eq_(
            self.conn.execute(text("select id, data, x from foo")).fetchall(),
            [(1, "d1", "x1")],
        )

    def test_bulk_insert_round_trip(self):
        self.op.bulk_insert(
            self.t1,
            [
                {"data": "d1", "x": "x1"},
                {"data": "d2", "x": "x2"},
                {"data": "d3", "x": "x3"},
            ],
        )

        eq_(
            self.conn.execute(text("select id, data, x from foo")).fetchall(),
            [(1, "d1", "x1"), (2, "d2", "x2"), (3, "d3", "x3")],
        )

    def test_bulk_insert_inline_literal(self):
        class MyType(TypeEngine):
            pass

        t1 = table("foo", column("id", Integer), column("data", MyType()))

        self.op.bulk_insert(
            t1,
            [
                {"id": 1, "data": self.op.inline_literal("d1")},
                {"id": 2, "data": self.op.inline_literal("d2")},
            ],
            multiinsert=False,
        )

        eq_(
            self.conn.execute(text("select id, data from foo")).fetchall(),
            [(1, "d1"), (2, "d2")],
        )

    def test_bulk_insert_from_new_table(self):
        t1 = self.op.create_table(
            "ins_table",
            Column("id", Integer),
            Column("v1", String()),
            Column("v2", String()),
        )
        self.op.bulk_insert(
            t1,
            [
                {"id": 1, "v1": "row v1", "v2": "row v5"},
                {"id": 2, "v1": "row v2", "v2": "row v6"},
            ],
        )
        eq_(
            self.conn.execute(
                text("select id, v1, v2 from ins_table order by id")
            ).fetchall(),
            [(1, "row v1", "row v5"), (2, "row v2", "row v6")],
        )
