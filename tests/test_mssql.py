"""Test op functions against MSSQL."""

from alembic.testing.fixtures import TestBase

from sqlalchemy import Integer, Column

from alembic import op, command, util

from alembic.testing import eq_, assert_raises_message
from alembic.testing.fixtures import capture_context_buffer, op_fixture
from alembic.testing.env import staging_env, _no_sql_testing_config, \
    three_rev_fixture, clear_staging_env
from alembic.testing import config


class FullEnvironmentTests(TestBase):

    @classmethod
    def setup_class(cls):
        staging_env()
        if util.sqla_105:
            directives = "sqlalchemy.legacy_schema_aliasing=false"
        else:
            directives = ""
        cls.cfg = cfg = _no_sql_testing_config("mssql", directives)

        cls.a, cls.b, cls.c = \
            three_rev_fixture(cfg)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_begin_commit(self):
        with capture_context_buffer(transactional_ddl=True) as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "BEGIN TRANSACTION;" in buf.getvalue()

        # ensure ends in COMMIT; GO
        eq_(
            [x for x in buf.getvalue().splitlines() if x][-2:],
            ['COMMIT;', 'GO']
        )

    @config.requirements.sqlalchemy_08
    def test_batch_separator_default(self):
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "GO" in buf.getvalue()

    @config.requirements.sqlalchemy_08
    def test_batch_separator_custom(self):
        with capture_context_buffer(mssql_batch_separator="BYE") as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "BYE" in buf.getvalue()


class OpTest(TestBase):

    def test_add_column(self):
        context = op_fixture('mssql')
        op.add_column('t1', Column('c1', Integer, nullable=False))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL")

    def test_add_column_with_default(self):
        context = op_fixture("mssql")
        op.add_column(
            't1', Column('c1', Integer, nullable=False, server_default="12"))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL DEFAULT '12'")

    def test_alter_column_rename_mssql(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", new_column_name="x")
        context.assert_(
            "EXEC sp_rename 't.c', x, 'COLUMN'"
        )

    def test_alter_column_rename_quoted_mssql(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", new_column_name="SomeFancyName")
        context.assert_(
            "EXEC sp_rename 't.c', [SomeFancyName], 'COLUMN'"
        )

    def test_alter_column_new_type(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", type_=Integer)
        context.assert_(
            'ALTER TABLE t ALTER COLUMN c INTEGER'
        )

    def test_alter_column_dont_touch_constraints(self):
        context = op_fixture('mssql')
        from sqlalchemy import Boolean
        op.alter_column('tests', 'col',
                        existing_type=Boolean(),
                        nullable=False)
        context.assert_('ALTER TABLE tests ALTER COLUMN col BIT NOT NULL')

    @config.requirements.fail_before_sqla_084
    def test_drop_index(self):
        context = op_fixture('mssql')
        op.drop_index('my_idx', 'my_table')
        context.assert_contains("DROP INDEX my_idx ON my_table")

    def test_drop_column_w_default(self):
        context = op_fixture('mssql')
        op.drop_column('t1', 'c1', mssql_drop_default=True)
        op.drop_column('t1', 'c2', mssql_drop_default=True)
        context.assert_contains(
            "exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_column_w_default_in_batch(self):
        context = op_fixture('mssql')
        with op.batch_alter_table('t1', schema=None) as batch_op:
            batch_op.drop_column('c1', mssql_drop_default=True)
            batch_op.drop_column('c2', mssql_drop_default=True)
        context.assert_contains(
            "exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_alter_column_drop_default(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", server_default=None)
        context.assert_contains(
            "exec('alter table t drop constraint ' + @const_name)")

    def test_alter_column_dont_drop_default(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", server_default=False)
        context.assert_()

    def test_drop_column_w_schema(self):
        context = op_fixture('mssql')
        op.drop_column('t1', 'c1', schema='xyz')
        context.assert_contains("ALTER TABLE xyz.t1 DROP COLUMN c1")

    def test_drop_column_w_check(self):
        context = op_fixture('mssql')
        op.drop_column('t1', 'c1', mssql_drop_check=True)
        op.drop_column('t1', 'c2', mssql_drop_check=True)
        context.assert_contains(
            "exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_column_w_check_in_batch(self):
        context = op_fixture('mssql')
        with op.batch_alter_table('t1', schema=None) as batch_op:
            batch_op.drop_column('c1', mssql_drop_check=True)
            batch_op.drop_column('c2', mssql_drop_check=True)
        context.assert_contains(
            "exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_column_w_check_quoting(self):
        context = op_fixture('mssql')
        op.drop_column('table', 'column', mssql_drop_check=True)
        context.assert_contains(
            "exec('alter table [table] drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE [table] DROP COLUMN [column]")

    def test_alter_column_nullable_w_existing_type(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", nullable=True, existing_type=Integer)
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c INTEGER NULL"
        )

    def test_drop_column_w_fk(self):
        context = op_fixture('mssql')
        op.drop_column('t1', 'c1', mssql_drop_foreign_key=True)
        context.assert_contains(
            "exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_column_w_fk_in_batch(self):
        context = op_fixture('mssql')
        with op.batch_alter_table('t1', schema=None) as batch_op:
            batch_op.drop_column('c1', mssql_drop_foreign_key=True)
        context.assert_contains(
            "exec('alter table t1 drop constraint ' + @const_name)")
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

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
        op.alter_column(
            "t", "c", server_default="5", existing_server_default="6")
        context.assert_contains(
            "exec('alter table t drop constraint ' + @const_name)")
        context.assert_contains(
            "ALTER TABLE t ADD DEFAULT '5' FOR c"
        )

    def test_alter_remove_server_default(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", server_default=None)
        context.assert_contains(
            "exec('alter table t drop constraint ' + @const_name)")

    def test_alter_do_everything(self):
        context = op_fixture('mssql')
        op.alter_column("t", "c", new_column_name="c2", nullable=True,
                        type_=Integer, server_default="5")
        context.assert_(
            'ALTER TABLE t ALTER COLUMN c INTEGER NULL',
            "ALTER TABLE t ADD DEFAULT '5' FOR c",
            "EXEC sp_rename 't.c', c2, 'COLUMN'"
        )

    def test_rename_table(self):
        context = op_fixture('mssql')
        op.rename_table('t1', 't2')
        context.assert_contains("EXEC sp_rename 't1', t2")

    # TODO: when we add schema support
    # def test_alter_column_rename_mssql_schema(self):
    #    context = op_fixture('mssql')
    #    op.alter_column("t", "c", name="x", schema="y")
    #    context.assert_(
    #        "EXEC sp_rename 'y.t.c', 'x', 'COLUMN'"
    #    )
