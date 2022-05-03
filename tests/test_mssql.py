"""Test op functions against MSSQL."""
from __future__ import annotations

from typing import Any
from typing import Dict

from sqlalchemy import Column
from sqlalchemy import exc
from sqlalchemy import Integer
from sqlalchemy import String

from alembic import command
from alembic import op
from alembic import util
from alembic.testing import assert_raises_message
from alembic.testing import combinations
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import expect_warnings
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.env import three_rev_fixture
from alembic.testing.fixtures import capture_context_buffer
from alembic.testing.fixtures import op_fixture
from alembic.testing.fixtures import TestBase
from alembic.util import sqla_compat


class FullEnvironmentTests(TestBase):
    @classmethod
    def setup_class(cls):
        staging_env()
        directives = "sqlalchemy.legacy_schema_aliasing=false"
        cls.cfg = cfg = _no_sql_testing_config("mssql", directives)

        cls.a, cls.b, cls.c = three_rev_fixture(cfg)

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
            ["COMMIT;", "GO"],
        )

    def test_batch_separator_default(self):
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "GO" in buf.getvalue()

    def test_batch_separator_custom(self):
        with capture_context_buffer(mssql_batch_separator="BYE") as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "BYE" in buf.getvalue()


class OpTest(TestBase):
    def test_add_column(self):
        context = op_fixture("mssql")
        op.add_column("t1", Column("c1", Integer, nullable=False))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL")

    def test_add_column_with_default(self):
        context = op_fixture("mssql")
        op.add_column(
            "t1", Column("c1", Integer, nullable=False, server_default="12")
        )
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL DEFAULT '12'")

    def test_alter_column_rename_mssql(self):
        context = op_fixture("mssql")
        op.alter_column(
            "t",
            "c",
            new_column_name="x",
        )
        context.assert_(
            "EXEC sp_rename 't.c', x, 'COLUMN'",
        )

    def test_alter_column_rename_quoted_mssql(self):
        context = op_fixture("mssql")
        op.alter_column(
            "t",
            "c",
            new_column_name="SomeFancyName",
        )
        context.assert_(
            "EXEC sp_rename 't.c', [SomeFancyName], 'COLUMN'",
        )

    @combinations((True,), (False,), argnames="pass_existing_type")
    @combinations((True,), (False,), argnames="existing_nullability")
    @combinations((True,), (False,), argnames="change_nullability")
    def test_alter_column_type_and_nullability(
        self, pass_existing_type, existing_nullability, change_nullability
    ):
        context = op_fixture("mssql")

        args: Dict[str, Any] = dict(type_=Integer)

        if change_nullability:
            expected_nullability = not existing_nullability
            args["nullable"] = expected_nullability
        else:
            args[
                "existing_nullable"
            ] = expected_nullability = existing_nullability

        op.alter_column("t", "c", **args)

        context.assert_(
            f"ALTER TABLE t ALTER COLUMN c INTEGER "
            f"{'NOT NULL' if not expected_nullability else 'NULL'}"
        )

    def test_alter_column_type_dont_change_nullability(self):
        context = op_fixture("mssql")

        op.alter_column("t", "c", type_=String(99), existing_nullable=False)
        context.assert_contains("ALTER COLUMN c VARCHAR(99) NOT NULL")

    def test_alter_column_type_should_have_existing_nullable(self):
        context = op_fixture("mssql")  # noqa
        with expect_warnings(
            "MS-SQL ALTER COLUMN operations that specify type_= should"
        ):
            op.alter_column(
                "t",
                "c",
                type_=String(99),
            )
        context.assert_contains("ALTER COLUMN c VARCHAR(99)")

    def test_alter_column_dont_touch_constraints(self):
        context = op_fixture("mssql")
        from sqlalchemy import Boolean

        op.alter_column(
            "tests", "col", existing_type=Boolean(), nullable=False
        )
        context.assert_("ALTER TABLE tests ALTER COLUMN col BIT NOT NULL")

    def test_drop_index(self):
        context = op_fixture("mssql")
        op.drop_index("my_idx", "my_table")
        context.assert_contains("DROP INDEX my_idx ON my_table")

    def test_drop_column_w_default(self):
        context = op_fixture("mssql")
        op.drop_column("t1", "c1", mssql_drop_default=True)
        op.drop_column("t1", "c2", mssql_drop_default=True)
        context.assert_contains(
            "exec('alter table t1 drop constraint ' + @const_name)"
        )
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_column_w_default_in_batch(self):
        context = op_fixture("mssql")
        with op.batch_alter_table("t1", schema=None) as batch_op:
            batch_op.drop_column("c1", mssql_drop_default=True)
            batch_op.drop_column("c2", mssql_drop_default=True)
        context.assert_contains(
            "exec('alter table t1 drop constraint ' + @const_name)"
        )
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_alter_column_drop_default(self):
        context = op_fixture("mssql")
        op.alter_column(
            "t",
            "c",
            server_default=None,
        )
        context.assert_contains(
            "declare @const_name varchar(256)select @const_name = [name] "
            "from sys.default_constraintswhere parent_object_id = "
            "object_id('t')and col_name(parent_object_id, "
            "parent_column_id) = 'c'"
        )
        context.assert_contains(
            "exec('alter table t drop constraint ' + @const_name)"
        )

    def test_alter_column_drop_default_w_schema(self):
        context = op_fixture("mssql")
        op.alter_column(
            "t",
            "c",
            server_default=None,
            schema="xyz",
        )
        context.assert_contains(
            "declare @const_name varchar(256)select @const_name = [name] "
            "from sys.default_constraintswhere parent_object_id = "
            "object_id('xyz.t')and col_name(parent_object_id, "
            "parent_column_id) = 'c'"
        )
        context.assert_contains(
            "exec('alter table xyz.t drop constraint ' + @const_name)"
        )

    def test_alter_column_dont_drop_default(self):
        context = op_fixture("mssql")
        op.alter_column(
            "t",
            "c",
            server_default=False,
        )
        context.assert_()

    def test_drop_column_w_schema(self):
        context = op_fixture("mssql")
        op.drop_column("t1", "c1", schema="xyz")
        context.assert_contains("ALTER TABLE xyz.t1 DROP COLUMN c1")

    def test_drop_column_w_check(self):
        context = op_fixture("mssql")
        op.drop_column("t1", "c1", mssql_drop_check=True)
        op.drop_column("t1", "c2", mssql_drop_check=True)
        context.assert_contains(
            "exec('alter table t1 drop constraint ' + @const_name)"
        )
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_column_w_check_in_batch(self):
        context = op_fixture("mssql")
        with op.batch_alter_table("t1", schema=None) as batch_op:
            batch_op.drop_column("c1", mssql_drop_check=True)
            batch_op.drop_column("c2", mssql_drop_check=True)
        context.assert_contains(
            "exec('alter table t1 drop constraint ' + @const_name)"
        )
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_column_w_check_quoting(self):
        context = op_fixture("mssql")
        op.drop_column("table", "column", mssql_drop_check=True)
        context.assert_contains(
            "exec('alter table [table] drop constraint ' + @const_name)"
        )
        context.assert_contains("ALTER TABLE [table] DROP COLUMN [column]")

    def test_alter_column_nullable_w_existing_type(self):
        context = op_fixture("mssql")
        op.alter_column("t", "c", nullable=True, existing_type=Integer)
        context.assert_("ALTER TABLE t ALTER COLUMN c INTEGER NULL")

    def test_drop_column_w_fk(self):
        context = op_fixture("mssql")
        op.drop_column("t1", "c1", mssql_drop_foreign_key=True)
        context.assert_contains(
            "declare @const_name varchar(256)\n"
            "select @const_name = [name] from\n"
            "sys.foreign_keys fk join sys.foreign_key_columns fkcon "
            "fk.object_id=fkc.constraint_object_id\n"
            "where fkc.parent_object_id = object_id('t1')\nand "
            "col_name(fkc.parent_object_id, fkc.parent_column_id) = 'c1'\n"
            "exec('alter table t1 drop constraint ' + @const_name)"
        )
        context.assert_contains(
            "exec('alter table t1 drop constraint ' + @const_name)"
        )
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_column_w_fk_schema(self):
        context = op_fixture("mssql")
        op.drop_column("t1", "c1", schema="xyz", mssql_drop_foreign_key=True)
        context.assert_contains(
            "declare @const_name varchar(256)\n"
            "select @const_name = [name] from\n"
            "sys.foreign_keys fk join sys.foreign_key_columns fkcon "
            "fk.object_id=fkc.constraint_object_id\n"
            "where fkc.parent_object_id = object_id('xyz.t1')\nand "
            "col_name(fkc.parent_object_id, fkc.parent_column_id) = 'c1'\n"
            "exec('alter table xyz.t1 drop constraint ' + @const_name)"
        )
        context.assert_contains(
            "exec('alter table xyz.t1 drop constraint ' + @const_name)"
        )
        context.assert_contains("ALTER TABLE xyz.t1 DROP COLUMN c1")

    def test_drop_column_w_fk_in_batch(self):
        context = op_fixture("mssql")
        with op.batch_alter_table("t1", schema=None) as batch_op:
            batch_op.drop_column("c1", mssql_drop_foreign_key=True)
        context.assert_contains(
            "exec('alter table t1 drop constraint ' + @const_name)"
        )
        context.assert_contains("ALTER TABLE t1 DROP COLUMN c1")

    def test_alter_column_not_nullable_w_existing_type(self):
        context = op_fixture("mssql")
        op.alter_column("t", "c", nullable=False, existing_type=Integer)
        context.assert_("ALTER TABLE t ALTER COLUMN c INTEGER NOT NULL")

    def test_alter_column_nullable_w_new_type(self):
        context = op_fixture("mssql")
        op.alter_column("t", "c", nullable=True, type_=Integer)
        context.assert_("ALTER TABLE t ALTER COLUMN c INTEGER NULL")

    def test_alter_column_not_nullable_w_new_type(self):
        context = op_fixture("mssql")
        op.alter_column("t", "c", nullable=False, type_=Integer)
        context.assert_("ALTER TABLE t ALTER COLUMN c INTEGER NOT NULL")

    def test_alter_column_nullable_type_required(self):
        op_fixture("mssql")
        assert_raises_message(
            util.CommandError,
            "MS-SQL ALTER COLUMN operations with NULL or "
            "NOT NULL require the existing_type or a new "
            "type_ be passed.",
            op.alter_column,
            "t",
            "c",
            nullable=False,
        )

    def test_alter_add_server_default(self):
        context = op_fixture("mssql")
        op.alter_column(
            "t",
            "c",
            server_default="5",
        )
        context.assert_(
            "ALTER TABLE t ADD DEFAULT '5' FOR c",
        )

    def test_alter_replace_server_default(self):
        context = op_fixture("mssql")
        op.alter_column(
            "t",
            "c",
            server_default="5",
            existing_server_default="6",
        )
        context.assert_contains(
            "exec('alter table t drop constraint ' + @const_name)"
        )
        context.assert_contains("ALTER TABLE t ADD DEFAULT '5' FOR c")

    def test_alter_remove_server_default(self):
        context = op_fixture("mssql")
        op.alter_column(
            "t",
            "c",
            server_default=None,
        )
        context.assert_contains(
            "exec('alter table t drop constraint ' + @const_name)"
        )

    @config.requirements.computed_columns_api
    def test_add_column_computed(self):
        context = op_fixture("mssql")
        op.add_column(
            "t1",
            Column("some_column", Integer, sqla_compat.Computed("foo * 5")),
        )
        context.assert_("ALTER TABLE t1 ADD some_column AS (foo * 5)")

    def test_alter_do_everything(self):
        context = op_fixture("mssql")
        op.alter_column(
            "t",
            "c",
            new_column_name="c2",
            nullable=True,
            type_=Integer,
            server_default="5",
        )
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c INTEGER NULL",
            "ALTER TABLE t ADD DEFAULT '5' FOR c",
            "EXEC sp_rename 't.c', c2, 'COLUMN'",
        )

    def test_rename_table(self):
        context = op_fixture("mssql")
        op.rename_table("t1", "t2")
        context.assert_contains("EXEC sp_rename 't1', t2")

    def test_rename_table_schema(self):
        context = op_fixture("mssql")
        op.rename_table("t1", "t2", schema="foobar")
        context.assert_contains("EXEC sp_rename 'foobar.t1', t2")

    def test_rename_table_casesens(self):
        context = op_fixture("mssql")
        op.rename_table("TeeOne", "TeeTwo")
        # yup, ran this in SQL Server 2014, the two levels of quoting
        # seems to be understood.  Can't do the two levels on the
        # target name though !
        context.assert_contains("EXEC sp_rename '[TeeOne]', [TeeTwo]")

    def test_rename_table_schema_casesens(self):
        context = op_fixture("mssql")
        op.rename_table("TeeOne", "TeeTwo", schema="FooBar")
        # yup, ran this in SQL Server 2014, the two levels of quoting
        # seems to be understood.  Can't do the two levels on the
        # target name though !
        context.assert_contains("EXEC sp_rename '[FooBar].[TeeOne]', [TeeTwo]")

    def test_alter_column_rename_mssql_schema(self):
        context = op_fixture("mssql")
        op.alter_column(
            "t",
            "c",
            new_column_name="x",
            schema="y",
        )
        context.assert_(
            "EXEC sp_rename 'y.t.c', x, 'COLUMN'",
        )

    def test_create_index_mssql_include(self):
        context = op_fixture("mssql")
        op.create_index(
            op.f("ix_mytable_a_b"),
            "mytable",
            ["col_a", "col_b"],
            unique=False,
            mssql_include=["col_c"],
        )
        context.assert_contains(
            "CREATE INDEX ix_mytable_a_b ON mytable "
            "(col_a, col_b) INCLUDE (col_c)"
        )

    def test_create_index_mssql_include_is_none(self):
        context = op_fixture("mssql")
        op.create_index(
            op.f("ix_mytable_a_b"), "mytable", ["col_a", "col_b"], unique=False
        )
        context.assert_contains(
            "CREATE INDEX ix_mytable_a_b ON mytable " "(col_a, col_b)"
        )

    @combinations(
        (lambda: sqla_compat.Computed("foo * 5"), lambda: None),
        (lambda: None, lambda: sqla_compat.Computed("foo * 5")),
        (
            lambda: sqla_compat.Computed("foo * 42"),
            lambda: sqla_compat.Computed("foo * 5"),
        ),
    )
    @config.requirements.computed_columns
    def test_alter_column_computed_not_supported(self, sd, esd):
        op_fixture("mssql")
        assert_raises_message(
            exc.CompileError,
            'Adding or removing a "computed" construct, e.g. '
            "GENERATED ALWAYS AS, to or from an existing column is not "
            "supported.",
            op.alter_column,
            "t1",
            "c1",
            server_default=sd(),
            existing_server_default=esd(),
        )

    @config.requirements.identity_columns
    @combinations(
        ({},),
        (dict(always=True),),
        (dict(start=3),),
        (dict(start=3, increment=3),),
    )
    def test_add_column_identity(self, kw):
        context = op_fixture("mssql")
        op.add_column(
            "t1",
            Column("some_column", Integer, sqla_compat.Identity(**kw)),
        )
        if "start" in kw or "increment" in kw:
            options = "(%s,%s)" % (
                kw.get("start", 1),
                kw.get("increment", 1),
            )
        else:
            options = ""
        context.assert_(
            "ALTER TABLE t1 ADD some_column INTEGER NOT NULL IDENTITY%s"
            % options
        )

    @combinations(
        (lambda: sqla_compat.Identity(), lambda: None),
        (lambda: None, lambda: sqla_compat.Identity()),
        (
            lambda: sqla_compat.Identity(),
            lambda: sqla_compat.Identity(),
        ),
    )
    @config.requirements.identity_columns
    def test_alter_column_identity_add_not_supported(self, sd, esd):
        op_fixture("mssql")
        assert_raises_message(
            exc.CompileError,
            'Adding, removing or modifying an "identity" construct, '
            "e.g. GENERATED AS IDENTITY, to or from an existing "
            "column is not supported in this dialect.",
            op.alter_column,
            "t1",
            "c1",
            server_default=sd(),
            existing_server_default=esd(),
        )
