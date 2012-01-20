"""Test op functions against MSSQL."""
from __future__ import with_statement
from tests import op_fixture, capture_context_buffer, \
    _no_sql_testing_config, assert_raises_message, staging_env, \
    three_rev_fixture, clear_staging_env
from alembic import op, command, util
from sqlalchemy import Integer, Column, ForeignKey, \
            UniqueConstraint, Table, MetaData, String
from sqlalchemy.sql import table
from unittest import TestCase


class FullEnvironmentTests(TestCase):
    @classmethod
    def setup_class(cls):
        env = staging_env()
        cls.cfg = cfg = _no_sql_testing_config("mssql")

        cls.a, cls.b, cls.c = \
            three_rev_fixture(cfg)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_begin_comit(self):
        with capture_context_buffer(transactional_ddl=True) as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "BEGIN TRANSACTION;" in buf.getvalue()
        assert "COMMIT;" in buf.getvalue()

    def test_batch_separator_default(self):
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "GO" in buf.getvalue()

    def test_batch_separator_custom(self):
        with capture_context_buffer(mssql_batch_separator="BYE") as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "BYE" in buf.getvalue()

class OpTest(TestCase):
    def test_add_column(self):
        context = op_fixture('mssql')
        op.add_column('t1', Column('c1', Integer, nullable=False))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL")


    def test_add_column_with_default(self):
        context = op_fixture("mssql")
        op.add_column('t1', Column('c1', Integer, nullable=False, server_default="12"))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL DEFAULT '12'")

    def test_alter_column_rename_mssql(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", name="x")
        context.assert_(
            "EXEC sp_rename 't.c', 'x', 'COLUMN'"
        )

    def test_alter_column_new_type(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", type_=Integer)
        context.assert_(
            'ALTER TABLE t ALTER COLUMN c INTEGER'
        )

    def test_drop_column_w_default(self):
        context = op_fixture('mssql')
        op.drop_column('t1', 'c1', mssql_drop_default=True)
        op.drop_column('t1', 'c2', mssql_drop_default=True)
        context.assert_contains("exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")


    def test_drop_column_w_check(self):
        context = op_fixture('mssql')
        op.drop_column('t1', 'c1', mssql_drop_check=True)
        op.drop_column('t1', 'c2', mssql_drop_check=True)
        context.assert_contains("exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_alter_column_nullable_w_existing_type(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", nullable=True, existing_type=Integer)
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c INTEGER NULL"
        )

    def test_alter_column_not_nullable_w_existing_type(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", nullable=False, existing_type=Integer)
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c INTEGER NOT NULL"
        )

    def test_alter_column_nullable_w_new_type(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", nullable=True, type_=Integer)
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c INTEGER NULL"
        )

    def test_alter_column_not_nullable_w_new_type(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", nullable=False, type_=Integer)
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c INTEGER NOT NULL"
        )

    def test_alter_column_nullable_type_required(self):
        context = op_fixture('mssql')
        assert_raises_message(
            util.CommandError,
            "MS-SQL ALTER COLUMN operations with NULL or "
            "NOT NULL require the existing_type or a new "
            "type_ be passed.",
            op.alter_column, "t", "c", nullable=False
        )

    def test_alter_add_server_default(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", server_default="5")
        context.assert_(
            "ALTER TABLE t ADD DEFAULT '5' FOR c"
        )

    def test_alter_replace_server_default(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", server_default="5", existing_server_default="6")
        context.assert_contains("exec('alter table t drop constraint ' + @const_name)")
        context.assert_contains(
            "ALTER TABLE t ADD DEFAULT '5' FOR c"
        )

    def test_alter_remove_server_default(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", server_default=None)
        context.assert_contains("exec('alter table t drop constraint ' + @const_name)")

    def test_alter_do_everything(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", name="c2", nullable=True, type_=Integer, server_default="5")
        context.assert_(
            'ALTER TABLE t ALTER COLUMN c INTEGER NULL', 
            "ALTER TABLE t ADD DEFAULT '5' FOR c", 
            "EXEC sp_rename 't.c', 'c2', 'COLUMN'"
        )

    # TODO: when we add schema support
    #def test_alter_column_rename_mssql_schema(self):
    #    context = op_fixture('mssql')
    #    op.alter_column("t", "c", name="x", schema="y")
    #    context.assert_(
    #        "EXEC sp_rename 'y.t.c', 'x', 'COLUMN'"
    #    )

