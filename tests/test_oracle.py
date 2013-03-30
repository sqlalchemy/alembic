"""Test op functions against ORACLE."""
from __future__ import with_statement
from tests import op_fixture, capture_context_buffer, \
    _no_sql_testing_config, staging_env, \
    three_rev_fixture, clear_staging_env
from alembic import op, command
from sqlalchemy import Integer, Column
from unittest import TestCase


class FullEnvironmentTests(TestCase):
    @classmethod
    def setup_class(cls):
        env = staging_env()
        cls.cfg = cfg = _no_sql_testing_config("oracle")

        cls.a, cls.b, cls.c = \
            three_rev_fixture(cfg)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_begin_comit(self):
        with capture_context_buffer(transactional_ddl=True) as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "SET TRANSACTION READ WRITE\n\n/" in buf.getvalue()
        assert "COMMIT\n\n/" in buf.getvalue()

    def test_batch_separator_default(self):
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "/" in buf.getvalue()
        assert ";" not in buf.getvalue()

    def test_batch_separator_custom(self):
        with capture_context_buffer(oracle_batch_separator="BYE") as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "BYE" in buf.getvalue()

class OpTest(TestCase):
    def test_add_column(self):
        context = op_fixture('oracle')
        op.add_column('t1', Column('c1', Integer, nullable=False))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL")


    def test_add_column_with_default(self):
        context = op_fixture("oracle")
        op.add_column('t1', Column('c1', Integer, nullable=False, server_default="12"))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER DEFAULT '12' NOT NULL")

    def test_alter_column_rename_oracle(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", name="x")
        context.assert_(
            "ALTER TABLE t RENAME COLUMN c TO x"
        )

    def test_alter_column_new_type(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", type_=Integer)
        context.assert_(
            'ALTER TABLE t MODIFY c INTEGER'
        )

    def test_drop_index(self):
        context = op_fixture('oracle')
        op.drop_index('my_idx', 'my_table')
        context.assert_contains("DROP INDEX my_idx")

    def test_drop_column_w_default(self):
        context = op_fixture('oracle')
        op.drop_column('t1', 'c1')
        context.assert_(
            "ALTER TABLE t1 DROP COLUMN c1"
        )

    def test_drop_column_w_check(self):
        context = op_fixture('oracle')
        op.drop_column('t1', 'c1')
        context.assert_(
            "ALTER TABLE t1 DROP COLUMN c1"
        )

    def test_alter_column_nullable_w_existing_type(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", nullable=True, existing_type=Integer)
        context.assert_(
            "ALTER TABLE t MODIFY c NULL"
        )

    def test_alter_column_not_nullable_w_existing_type(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", nullable=False, existing_type=Integer)
        context.assert_(
            "ALTER TABLE t MODIFY c NOT NULL"
        )

    def test_alter_column_nullable_w_new_type(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", nullable=True, type_=Integer)
        context.assert_(
            "ALTER TABLE t MODIFY c NULL",
            'ALTER TABLE t MODIFY c INTEGER'
        )

    def test_alter_column_not_nullable_w_new_type(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", nullable=False, type_=Integer)
        context.assert_(
            "ALTER TABLE t MODIFY c NOT NULL",
            "ALTER TABLE t MODIFY c INTEGER"
        )

    def test_alter_add_server_default(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", server_default="5")
        context.assert_(
            "ALTER TABLE t MODIFY c DEFAULT '5'"
        )

    def test_alter_replace_server_default(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", server_default="5", existing_server_default="6")
        context.assert_(
            "ALTER TABLE t MODIFY c DEFAULT '5'"
        )

    def test_alter_remove_server_default(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", server_default=None)
        context.assert_(
            "ALTER TABLE t MODIFY c DEFAULT NULL"
        )

    def test_alter_do_everything(self):
        context = op_fixture('oracle')
        op.alter_column("t", "c", name="c2", nullable=True, type_=Integer, server_default="5")
        context.assert_(
            'ALTER TABLE t MODIFY c NULL',
            "ALTER TABLE t MODIFY c DEFAULT '5'",
            'ALTER TABLE t MODIFY c INTEGER',
            'ALTER TABLE t RENAME COLUMN c TO c2'
        )

    # TODO: when we add schema support
    #def test_alter_column_rename_oracle_schema(self):
    #    context = op_fixture('oracle')
    #    op.alter_column("t", "c", name="x", schema="y")
    #    context.assert_(
    #        'ALTER TABLE y.t RENAME COLUMN c TO c2'
    #    )

