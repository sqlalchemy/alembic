from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy.sql import text

from alembic import testing
from alembic.testing import eq_
from alembic.testing.fixtures import FutureEngineMixin
from alembic.testing.fixtures import TablesTest


class ImplTest(TablesTest):
    __only_on__ = "sqlite"

    @classmethod
    def define_tables(cls, metadata):
        Table(
            "some_table", metadata, Column("x", Integer), Column("y", Integer)
        )

    @testing.fixture
    def impl(self, migration_context):
        with migration_context.begin_transaction(_per_migration=True):
            yield migration_context.impl

    @testing.fixture
    def as_sql_impl(self, as_sql_migration_context):
        with as_sql_migration_context.begin_transaction(_per_migration=True):
            yield as_sql_migration_context.impl

    def test_execute_params(self, impl):
        result = impl._exec(text("select :my_param"), params={"my_param": 5})
        eq_(result.scalar(), 5)

    def test_execute_multiparams(self, impl):
        some_table = self.tables.some_table
        impl._exec(
            some_table.insert(),
            multiparams=[{"x": 1, "y": 2}, {"x": 2, "y": 3}, {"x": 5, "y": 7}],
        )
        eq_(
            impl._exec(
                some_table.select().order_by(some_table.c.x)
            ).fetchall(),
            [(1, 2), (2, 3), (5, 7)],
        )

    def test_dont_send_both(self, impl):
        with testing.expect_raises_message(
            TypeError, "Can't send params and multiparams at the same time"
        ):
            impl._exec(
                text("select :my_param"),
                params={"my_param": 5},
                multiparams=[],
            )

    def test_no_params_w_as_sql(self, as_sql_impl):
        with testing.expect_raises_message(
            TypeError, "SQL parameters not allowed with as_sql"
        ):
            as_sql_impl._exec(text("select :my_param"), params={"my_param": 5})

    def test_no_multiparams_w_as_sql(self, as_sql_impl):
        with testing.expect_raises_message(
            TypeError, "SQL parameters not allowed with as_sql"
        ):
            as_sql_impl._exec(text("select :my_param"), multiparams=[])


class FutureImplTest(FutureEngineMixin, ImplTest):
    pass
