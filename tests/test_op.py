"""Test against the builders in the op.* module."""

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import event
from sqlalchemy import exc
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.sql import column
from sqlalchemy.sql import func
from sqlalchemy.sql import text
from sqlalchemy.sql.schema import quoted_name

from alembic import op
from alembic.operations import ops
from alembic.operations import schemaobj
from alembic.testing import assert_raises_message
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import is_
from alembic.testing import mock
from alembic.testing.fixtures import AlterColRoundTripFixture
from alembic.testing.fixtures import op_fixture
from alembic.testing.fixtures import TestBase
from alembic.util import sqla_compat


@event.listens_for(Table, "after_parent_attach")
def _add_cols(table, metadata):
    if table.name == "tbl_with_auto_appended_column":
        table.append_column(Column("bat", Integer))


class OpTest(TestBase):
    def test_rename_table(self):
        context = op_fixture()
        op.rename_table("t1", "t2")
        context.assert_("ALTER TABLE t1 RENAME TO t2")

    def test_rename_table_schema(self):
        context = op_fixture()
        op.rename_table("t1", "t2", schema="foo")
        context.assert_("ALTER TABLE foo.t1 RENAME TO foo.t2")

    def test_create_index_no_expr_allowed(self):
        op_fixture()
        assert_raises_message(
            ValueError,
            r"String or text\(\) construct expected",
            op.create_index,
            "name",
            "tname",
            [func.foo(column("x"))],
        )

    def test_add_column_schema_hard_quoting(self):

        context = op_fixture("postgresql")
        op.add_column(
            "somename",
            Column("colname", String),
            schema=quoted_name("some.schema", quote=True),
        )

        context.assert_(
            'ALTER TABLE "some.schema".somename ADD COLUMN colname VARCHAR'
        )

    def test_rename_table_schema_hard_quoting(self):

        context = op_fixture("postgresql")
        op.rename_table(
            "t1", "t2", schema=quoted_name("some.schema", quote=True)
        )

        context.assert_('ALTER TABLE "some.schema".t1 RENAME TO t2')

    def test_add_constraint_schema_hard_quoting(self):

        context = op_fixture("postgresql")
        op.create_check_constraint(
            "ck_user_name_len",
            "user_table",
            func.len(column("name")) > 5,
            schema=quoted_name("some.schema", quote=True),
        )
        context.assert_(
            'ALTER TABLE "some.schema".user_table ADD '
            "CONSTRAINT ck_user_name_len CHECK (len(name) > 5)"
        )

    def test_create_index_quoting(self):
        context = op_fixture("postgresql")
        op.create_index("geocoded", "locations", ["IShouldBeQuoted"])
        context.assert_(
            'CREATE INDEX geocoded ON locations ("IShouldBeQuoted")'
        )

    def test_create_index_expressions(self):
        context = op_fixture()
        op.create_index("geocoded", "locations", [text("lower(coordinates)")])
        context.assert_(
            "CREATE INDEX geocoded ON locations (lower(coordinates))"
        )

    def test_add_column(self):
        context = op_fixture()
        op.add_column("t1", Column("c1", Integer, nullable=False))
        context.assert_("ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL")

    def test_add_column_schema(self):
        context = op_fixture()
        op.add_column(
            "t1", Column("c1", Integer, nullable=False), schema="foo"
        )
        context.assert_("ALTER TABLE foo.t1 ADD COLUMN c1 INTEGER NOT NULL")

    def test_add_column_with_default(self):
        context = op_fixture()
        op.add_column(
            "t1", Column("c1", Integer, nullable=False, server_default="12")
        )
        context.assert_(
            "ALTER TABLE t1 ADD COLUMN c1 INTEGER DEFAULT '12' NOT NULL"
        )

    def test_add_column_with_index(self):
        context = op_fixture()
        op.add_column("t1", Column("c1", Integer, nullable=False, index=True))
        context.assert_(
            "ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL",
            "CREATE INDEX ix_t1_c1 ON t1 (c1)",
        )

    def test_add_column_schema_with_default(self):
        context = op_fixture()
        op.add_column(
            "t1",
            Column("c1", Integer, nullable=False, server_default="12"),
            schema="foo",
        )
        context.assert_(
            "ALTER TABLE foo.t1 ADD COLUMN c1 INTEGER DEFAULT '12' NOT NULL"
        )

    def test_add_column_fk(self):
        context = op_fixture()
        op.add_column(
            "t1", Column("c1", Integer, ForeignKey("c2.id"), nullable=False)
        )
        context.assert_(
            "ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL",
            "ALTER TABLE t1 ADD FOREIGN KEY(c1) REFERENCES c2 (id)",
        )

    def test_add_column_schema_fk(self):
        context = op_fixture()
        op.add_column(
            "t1",
            Column("c1", Integer, ForeignKey("c2.id"), nullable=False),
            schema="foo",
        )
        context.assert_(
            "ALTER TABLE foo.t1 ADD COLUMN c1 INTEGER NOT NULL",
            "ALTER TABLE foo.t1 ADD FOREIGN KEY(c1) REFERENCES c2 (id)",
        )

    def test_add_column_schema_type(self):
        """Test that a schema type generates its constraints...."""
        context = op_fixture()
        op.add_column("t1", Column("c1", Boolean, nullable=False))
        context.assert_(
            "ALTER TABLE t1 ADD COLUMN c1 BOOLEAN NOT NULL",
            "ALTER TABLE t1 ADD CHECK (c1 IN (0, 1))",
        )

    def test_add_column_schema_schema_type(self):
        """Test that a schema type generates its constraints...."""
        context = op_fixture()
        op.add_column(
            "t1", Column("c1", Boolean, nullable=False), schema="foo"
        )
        context.assert_(
            "ALTER TABLE foo.t1 ADD COLUMN c1 BOOLEAN NOT NULL",
            "ALTER TABLE foo.t1 ADD CHECK (c1 IN (0, 1))",
        )

    def test_add_column_schema_type_checks_rule(self):
        """Test that a schema type doesn't generate a
        constraint based on check rule."""
        context = op_fixture("postgresql")
        op.add_column("t1", Column("c1", Boolean, nullable=False))
        context.assert_("ALTER TABLE t1 ADD COLUMN c1 BOOLEAN NOT NULL")

    def test_add_column_fk_self_referential(self):
        context = op_fixture()
        op.add_column(
            "t1", Column("c1", Integer, ForeignKey("t1.c2"), nullable=False)
        )
        context.assert_(
            "ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL",
            "ALTER TABLE t1 ADD FOREIGN KEY(c1) REFERENCES t1 (c2)",
        )

    def test_add_column_schema_fk_self_referential(self):
        context = op_fixture()
        op.add_column(
            "t1",
            Column("c1", Integer, ForeignKey("foo.t1.c2"), nullable=False),
            schema="foo",
        )
        context.assert_(
            "ALTER TABLE foo.t1 ADD COLUMN c1 INTEGER NOT NULL",
            "ALTER TABLE foo.t1 ADD FOREIGN KEY(c1) REFERENCES foo.t1 (c2)",
        )

    def test_add_column_fk_schema(self):
        context = op_fixture()
        op.add_column(
            "t1",
            Column("c1", Integer, ForeignKey("remote.t2.c2"), nullable=False),
        )
        context.assert_(
            "ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL",
            "ALTER TABLE t1 ADD FOREIGN KEY(c1) REFERENCES remote.t2 (c2)",
        )

    def test_add_column_schema_fk_schema(self):
        context = op_fixture()
        op.add_column(
            "t1",
            Column("c1", Integer, ForeignKey("remote.t2.c2"), nullable=False),
            schema="foo",
        )
        context.assert_(
            "ALTER TABLE foo.t1 ADD COLUMN c1 INTEGER NOT NULL",
            "ALTER TABLE foo.t1 ADD FOREIGN KEY(c1) REFERENCES remote.t2 (c2)",
        )

    def test_drop_column(self):
        context = op_fixture()
        op.drop_column("t1", "c1")
        context.assert_("ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_column_schema(self):
        context = op_fixture()
        op.drop_column("t1", "c1", schema="foo")
        context.assert_("ALTER TABLE foo.t1 DROP COLUMN c1")

    def test_alter_column_nullable(self):
        context = op_fixture()
        op.alter_column("t", "c", nullable=True)
        context.assert_(
            # TODO: not sure if this is PG only or standard
            # SQL
            "ALTER TABLE t ALTER COLUMN c DROP NOT NULL"
        )

    def test_alter_column_schema_nullable(self):
        context = op_fixture()
        op.alter_column("t", "c", nullable=True, schema="foo")
        context.assert_(
            # TODO: not sure if this is PG only or standard
            # SQL
            "ALTER TABLE foo.t ALTER COLUMN c DROP NOT NULL"
        )

    def test_alter_column_not_nullable(self):
        context = op_fixture()
        op.alter_column("t", "c", nullable=False)
        context.assert_(
            # TODO: not sure if this is PG only or standard
            # SQL
            "ALTER TABLE t ALTER COLUMN c SET NOT NULL"
        )

    def test_alter_column_schema_not_nullable(self):
        context = op_fixture()
        op.alter_column("t", "c", nullable=False, schema="foo")
        context.assert_(
            # TODO: not sure if this is PG only or standard
            # SQL
            "ALTER TABLE foo.t ALTER COLUMN c SET NOT NULL"
        )

    def test_alter_column_rename(self):
        context = op_fixture()
        op.alter_column("t", "c", new_column_name="x")
        context.assert_("ALTER TABLE t RENAME c TO x")

    def test_alter_column_schema_rename(self):
        context = op_fixture()
        op.alter_column("t", "c", new_column_name="x", schema="foo")
        context.assert_("ALTER TABLE foo.t RENAME c TO x")

    def test_alter_column_type(self):
        context = op_fixture()
        op.alter_column("t", "c", type_=String(50))
        context.assert_("ALTER TABLE t ALTER COLUMN c TYPE VARCHAR(50)")

    def test_alter_column_schema_type(self):
        context = op_fixture()
        op.alter_column("t", "c", type_=String(50), schema="foo")
        context.assert_("ALTER TABLE foo.t ALTER COLUMN c TYPE VARCHAR(50)")

    def test_alter_column_set_default(self):
        context = op_fixture()
        op.alter_column("t", "c", server_default="q")
        context.assert_("ALTER TABLE t ALTER COLUMN c SET DEFAULT 'q'")

    def test_alter_column_schema_set_default(self):
        context = op_fixture()
        op.alter_column("t", "c", server_default="q", schema="foo")
        context.assert_("ALTER TABLE foo.t ALTER COLUMN c SET DEFAULT 'q'")

    def test_alter_column_set_compiled_default(self):
        context = op_fixture()
        op.alter_column(
            "t", "c", server_default=func.utc_thing(func.current_timestamp())
        )
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c "
            "SET DEFAULT utc_thing(CURRENT_TIMESTAMP)"
        )

    def test_alter_column_schema_set_compiled_default(self):
        context = op_fixture()
        op.alter_column(
            "t",
            "c",
            server_default=func.utc_thing(func.current_timestamp()),
            schema="foo",
        )
        context.assert_(
            "ALTER TABLE foo.t ALTER COLUMN c "
            "SET DEFAULT utc_thing(CURRENT_TIMESTAMP)"
        )

    def test_alter_column_drop_default(self):
        context = op_fixture()
        op.alter_column("t", "c", server_default=None)
        context.assert_("ALTER TABLE t ALTER COLUMN c DROP DEFAULT")

    def test_alter_column_schema_drop_default(self):
        context = op_fixture()
        op.alter_column("t", "c", server_default=None, schema="foo")
        context.assert_("ALTER TABLE foo.t ALTER COLUMN c DROP DEFAULT")

    @config.requirements.computed_columns_api
    def test_alter_column_computed_add_not_supported(self):
        op_fixture()
        assert_raises_message(
            exc.CompileError,
            'Adding or removing a "computed" construct, e.g. '
            "GENERATED ALWAYS AS, to or from an existing column is not "
            "supported.",
            op.alter_column,
            "t1",
            "c1",
            server_default=sqla_compat.Computed("foo * 5"),
        )

    @config.requirements.computed_columns_api
    def test_alter_column_computed_remove_not_supported(self):
        op_fixture()
        assert_raises_message(
            exc.CompileError,
            'Adding or removing a "computed" construct, e.g. '
            "GENERATED ALWAYS AS, to or from an existing column is not "
            "supported.",
            op.alter_column,
            "t1",
            "c1",
            server_default=None,
            existing_server_default=sqla_compat.Computed("foo * 5"),
        )

    def test_alter_column_schema_type_unnamed(self):
        context = op_fixture("mssql", native_boolean=False)
        op.alter_column("t", "c", type_=Boolean())
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c BIT",
            "ALTER TABLE t ADD CHECK (c IN (0, 1))",
        )

    def test_alter_column_schema_schema_type_unnamed(self):
        context = op_fixture("mssql", native_boolean=False)
        op.alter_column("t", "c", type_=Boolean(), schema="foo")
        context.assert_(
            "ALTER TABLE foo.t ALTER COLUMN c BIT",
            "ALTER TABLE foo.t ADD CHECK (c IN (0, 1))",
        )

    def test_alter_column_schema_type_named(self):
        context = op_fixture("mssql", native_boolean=False)
        op.alter_column("t", "c", type_=Boolean(name="xyz"))
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c BIT",
            "ALTER TABLE t ADD CONSTRAINT xyz CHECK (c IN (0, 1))",
        )

    def test_alter_column_schema_schema_type_named(self):
        context = op_fixture("mssql", native_boolean=False)
        op.alter_column("t", "c", type_=Boolean(name="xyz"), schema="foo")
        context.assert_(
            "ALTER TABLE foo.t ALTER COLUMN c BIT",
            "ALTER TABLE foo.t ADD CONSTRAINT xyz CHECK (c IN (0, 1))",
        )

    def test_alter_column_schema_type_existing_type(self):
        context = op_fixture("mssql", native_boolean=False)
        op.alter_column(
            "t", "c", type_=String(10), existing_type=Boolean(name="xyz")
        )
        context.assert_(
            "ALTER TABLE t DROP CONSTRAINT xyz",
            "ALTER TABLE t ALTER COLUMN c VARCHAR(10)",
        )

    def test_alter_column_schema_schema_type_existing_type(self):
        context = op_fixture("mssql", native_boolean=False)
        op.alter_column(
            "t",
            "c",
            type_=String(10),
            existing_type=Boolean(name="xyz"),
            schema="foo",
        )
        context.assert_(
            "ALTER TABLE foo.t DROP CONSTRAINT xyz",
            "ALTER TABLE foo.t ALTER COLUMN c VARCHAR(10)",
        )

    def test_alter_column_schema_type_existing_type_no_const(self):
        context = op_fixture("postgresql")
        op.alter_column("t", "c", type_=String(10), existing_type=Boolean())
        context.assert_("ALTER TABLE t ALTER COLUMN c TYPE VARCHAR(10)")

    def test_alter_column_schema_schema_type_existing_type_no_const(self):
        context = op_fixture("postgresql")
        op.alter_column(
            "t", "c", type_=String(10), existing_type=Boolean(), schema="foo"
        )
        context.assert_("ALTER TABLE foo.t ALTER COLUMN c TYPE VARCHAR(10)")

    def test_alter_column_schema_type_existing_type_no_new_type(self):
        context = op_fixture("postgresql")
        op.alter_column("t", "c", nullable=False, existing_type=Boolean())
        context.assert_("ALTER TABLE t ALTER COLUMN c SET NOT NULL")

    def test_alter_column_schema_schema_type_existing_type_no_new_type(self):
        context = op_fixture("postgresql")
        op.alter_column(
            "t", "c", nullable=False, existing_type=Boolean(), schema="foo"
        )
        context.assert_("ALTER TABLE foo.t ALTER COLUMN c SET NOT NULL")

    def test_add_foreign_key(self):
        context = op_fixture()
        op.create_foreign_key(
            "fk_test", "t1", "t2", ["foo", "bar"], ["bat", "hoho"]
        )
        context.assert_(
            "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho)"
        )

    def test_add_foreign_key_schema(self):
        context = op_fixture()
        op.create_foreign_key(
            "fk_test",
            "t1",
            "t2",
            ["foo", "bar"],
            ["bat", "hoho"],
            source_schema="foo2",
            referent_schema="bar2",
        )
        context.assert_(
            "ALTER TABLE foo2.t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES bar2.t2 (bat, hoho)"
        )

    def test_add_foreign_key_schema_same_tablename(self):
        context = op_fixture()
        op.create_foreign_key(
            "fk_test",
            "t1",
            "t1",
            ["foo", "bar"],
            ["bat", "hoho"],
            source_schema="foo2",
            referent_schema="bar2",
        )
        context.assert_(
            "ALTER TABLE foo2.t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES bar2.t1 (bat, hoho)"
        )

    def test_add_foreign_key_onupdate(self):
        context = op_fixture()
        op.create_foreign_key(
            "fk_test",
            "t1",
            "t2",
            ["foo", "bar"],
            ["bat", "hoho"],
            onupdate="CASCADE",
        )
        context.assert_(
            "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho) ON UPDATE CASCADE"
        )

    def test_add_foreign_key_ondelete(self):
        context = op_fixture()
        op.create_foreign_key(
            "fk_test",
            "t1",
            "t2",
            ["foo", "bar"],
            ["bat", "hoho"],
            ondelete="CASCADE",
        )
        context.assert_(
            "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho) ON DELETE CASCADE"
        )

    def test_add_foreign_key_deferrable(self):
        context = op_fixture()
        op.create_foreign_key(
            "fk_test",
            "t1",
            "t2",
            ["foo", "bar"],
            ["bat", "hoho"],
            deferrable=True,
        )
        context.assert_(
            "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho) DEFERRABLE"
        )

    def test_add_foreign_key_initially(self):
        context = op_fixture()
        op.create_foreign_key(
            "fk_test",
            "t1",
            "t2",
            ["foo", "bar"],
            ["bat", "hoho"],
            initially="deferred",
        )
        context.assert_(
            "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho) INITIALLY deferred"
        )

    @config.requirements.foreign_key_match
    def test_add_foreign_key_match(self):
        context = op_fixture()
        op.create_foreign_key(
            "fk_test",
            "t1",
            "t2",
            ["foo", "bar"],
            ["bat", "hoho"],
            match="SIMPLE",
        )
        context.assert_(
            "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho) MATCH SIMPLE"
        )

    def test_add_foreign_key_dialect_kw(self):
        op_fixture()
        with mock.patch("sqlalchemy.schema.ForeignKeyConstraint") as fkc:
            op.create_foreign_key(
                "fk_test",
                "t1",
                "t2",
                ["foo", "bar"],
                ["bat", "hoho"],
                foobar_arg="xyz",
            )
            if config.requirements.foreign_key_match.enabled:
                eq_(
                    fkc.mock_calls[0],
                    mock.call(
                        ["foo", "bar"],
                        ["t2.bat", "t2.hoho"],
                        onupdate=None,
                        ondelete=None,
                        name="fk_test",
                        foobar_arg="xyz",
                        deferrable=None,
                        initially=None,
                        match=None,
                    ),
                )
            else:
                eq_(
                    fkc.mock_calls[0],
                    mock.call(
                        ["foo", "bar"],
                        ["t2.bat", "t2.hoho"],
                        onupdate=None,
                        ondelete=None,
                        name="fk_test",
                        foobar_arg="xyz",
                        deferrable=None,
                        initially=None,
                    ),
                )

    def test_add_foreign_key_self_referential(self):
        context = op_fixture()
        op.create_foreign_key("fk_test", "t1", "t1", ["foo"], ["bar"])
        context.assert_(
            "ALTER TABLE t1 ADD CONSTRAINT fk_test "
            "FOREIGN KEY(foo) REFERENCES t1 (bar)"
        )

    def test_add_primary_key_constraint(self):
        context = op_fixture()
        op.create_primary_key("pk_test", "t1", ["foo", "bar"])
        context.assert_(
            "ALTER TABLE t1 ADD CONSTRAINT pk_test PRIMARY KEY (foo, bar)"
        )

    def test_add_primary_key_constraint_schema(self):
        context = op_fixture()
        op.create_primary_key("pk_test", "t1", ["foo"], schema="bar")
        context.assert_(
            "ALTER TABLE bar.t1 ADD CONSTRAINT pk_test PRIMARY KEY (foo)"
        )

    def test_add_check_constraint(self):
        context = op_fixture()
        op.create_check_constraint(
            "ck_user_name_len", "user_table", func.len(column("name")) > 5
        )
        context.assert_(
            "ALTER TABLE user_table ADD CONSTRAINT ck_user_name_len "
            "CHECK (len(name) > 5)"
        )

    def test_add_check_constraint_schema(self):
        context = op_fixture()
        op.create_check_constraint(
            "ck_user_name_len",
            "user_table",
            func.len(column("name")) > 5,
            schema="foo",
        )
        context.assert_(
            "ALTER TABLE foo.user_table ADD CONSTRAINT ck_user_name_len "
            "CHECK (len(name) > 5)"
        )

    def test_add_unique_constraint(self):
        context = op_fixture()
        op.create_unique_constraint("uk_test", "t1", ["foo", "bar"])
        context.assert_(
            "ALTER TABLE t1 ADD CONSTRAINT uk_test UNIQUE (foo, bar)"
        )

    def test_add_foreign_key_legacy_kwarg(self):
        context = op_fixture()

        op.create_foreign_key(
            name="some_fk",
            source="some_table",
            referent="referred_table",
            local_cols=["a", "b"],
            remote_cols=["c", "d"],
            ondelete="CASCADE",
        )
        context.assert_(
            "ALTER TABLE some_table ADD CONSTRAINT some_fk "
            "FOREIGN KEY(a, b) REFERENCES referred_table (c, d) "
            "ON DELETE CASCADE"
        )

    def test_add_unique_constraint_legacy_kwarg(self):
        context = op_fixture()
        op.create_unique_constraint(
            name="uk_test", source="t1", local_cols=["foo", "bar"]
        )
        context.assert_(
            "ALTER TABLE t1 ADD CONSTRAINT uk_test UNIQUE (foo, bar)"
        )

    def test_drop_constraint_legacy_kwarg(self):
        context = op_fixture()
        op.drop_constraint(
            name="pk_name", table_name="sometable", type_="primary"
        )
        context.assert_("ALTER TABLE sometable DROP CONSTRAINT pk_name")

    def test_create_pk_legacy_kwarg(self):
        context = op_fixture()
        op.create_primary_key(
            name=None,
            table_name="sometable",
            cols=["router_id", "l3_agent_id"],
        )
        context.assert_(
            "ALTER TABLE sometable ADD PRIMARY KEY (router_id, l3_agent_id)"
        )

    def test_legacy_kwarg_catches_arg_missing(self):
        op_fixture()

        assert_raises_message(
            TypeError,
            "missing required positional argument: columns",
            op.create_primary_key,
            name=None,
            table_name="sometable",
            wrong_cols=["router_id", "l3_agent_id"],
        )

    def test_add_unique_constraint_schema(self):
        context = op_fixture()
        op.create_unique_constraint(
            "uk_test", "t1", ["foo", "bar"], schema="foo"
        )
        context.assert_(
            "ALTER TABLE foo.t1 ADD CONSTRAINT uk_test UNIQUE (foo, bar)"
        )

    def test_drop_constraint(self):
        context = op_fixture()
        op.drop_constraint("foo_bar_bat", "t1")
        context.assert_("ALTER TABLE t1 DROP CONSTRAINT foo_bar_bat")

    def test_drop_constraint_schema(self):
        context = op_fixture()
        op.drop_constraint("foo_bar_bat", "t1", schema="foo")
        context.assert_("ALTER TABLE foo.t1 DROP CONSTRAINT foo_bar_bat")

    def test_create_index(self):
        context = op_fixture()
        op.create_index("ik_test", "t1", ["foo", "bar"])
        context.assert_("CREATE INDEX ik_test ON t1 (foo, bar)")

    def test_create_unique_index(self):
        context = op_fixture()
        op.create_index("ik_test", "t1", ["foo", "bar"], unique=True)
        context.assert_("CREATE UNIQUE INDEX ik_test ON t1 (foo, bar)")

    def test_create_index_quote_flag(self):
        context = op_fixture()
        op.create_index("ik_test", "t1", ["foo", "bar"], quote=True)
        context.assert_('CREATE INDEX "ik_test" ON t1 (foo, bar)')

    def test_create_index_table_col_event(self):
        context = op_fixture()

        op.create_index(
            "ik_test", "tbl_with_auto_appended_column", ["foo", "bar"]
        )
        context.assert_(
            "CREATE INDEX ik_test ON tbl_with_auto_appended_column (foo, bar)"
        )

    def test_add_unique_constraint_col_event(self):
        context = op_fixture()
        op.create_unique_constraint(
            "ik_test", "tbl_with_auto_appended_column", ["foo", "bar"]
        )
        context.assert_(
            "ALTER TABLE tbl_with_auto_appended_column "
            "ADD CONSTRAINT ik_test UNIQUE (foo, bar)"
        )

    def test_create_index_schema(self):
        context = op_fixture()
        op.create_index("ik_test", "t1", ["foo", "bar"], schema="foo")
        context.assert_("CREATE INDEX ik_test ON foo.t1 (foo, bar)")

    def test_drop_index(self):
        context = op_fixture()
        op.drop_index("ik_test")
        context.assert_("DROP INDEX ik_test")

    def test_drop_index_schema(self):
        context = op_fixture()
        op.drop_index("ik_test", schema="foo")
        context.assert_("DROP INDEX foo.ik_test")

    def test_drop_table(self):
        context = op_fixture()
        op.drop_table("tb_test")
        context.assert_("DROP TABLE tb_test")

    def test_drop_table_schema(self):
        context = op_fixture()
        op.drop_table("tb_test", schema="foo")
        context.assert_("DROP TABLE foo.tb_test")

    def test_create_table_selfref(self):
        context = op_fixture()
        op.create_table(
            "some_table",
            Column("id", Integer, primary_key=True),
            Column("st_id", Integer, ForeignKey("some_table.id")),
        )
        context.assert_(
            "CREATE TABLE some_table ("
            "id INTEGER NOT NULL, "
            "st_id INTEGER, "
            "PRIMARY KEY (id), "
            "FOREIGN KEY(st_id) REFERENCES some_table (id))"
        )

    def test_create_table_fk_and_schema(self):
        context = op_fixture()
        t1 = op.create_table(
            "some_table",
            Column("id", Integer, primary_key=True),
            Column("foo_id", Integer, ForeignKey("foo.id")),
            schema="schema",
        )
        context.assert_(
            "CREATE TABLE schema.some_table ("
            "id INTEGER NOT NULL, "
            "foo_id INTEGER, "
            "PRIMARY KEY (id), "
            "FOREIGN KEY(foo_id) REFERENCES foo (id))"
        )
        eq_(t1.c.id.name, "id")
        eq_(t1.schema, "schema")

    def test_create_table_no_pk(self):
        context = op_fixture()
        t1 = op.create_table(
            "some_table",
            Column("x", Integer),
            Column("y", Integer),
            Column("z", Integer),
        )
        context.assert_(
            "CREATE TABLE some_table (x INTEGER, y INTEGER, z INTEGER)"
        )
        assert not t1.primary_key

    def test_create_table_two_fk(self):
        context = op_fixture()
        op.create_table(
            "some_table",
            Column("id", Integer, primary_key=True),
            Column("foo_id", Integer, ForeignKey("foo.id")),
            Column("foo_bar", Integer, ForeignKey("foo.bar")),
        )
        context.assert_(
            "CREATE TABLE some_table ("
            "id INTEGER NOT NULL, "
            "foo_id INTEGER, "
            "foo_bar INTEGER, "
            "PRIMARY KEY (id), "
            "FOREIGN KEY(foo_id) REFERENCES foo (id), "
            "FOREIGN KEY(foo_bar) REFERENCES foo (bar))"
        )

    def test_inline_literal(self):
        context = op_fixture()
        from sqlalchemy.sql import table, column
        from sqlalchemy import String, Integer

        account = table(
            "account", column("name", String), column("id", Integer)
        )
        op.execute(
            account.update()
            .where(account.c.name == op.inline_literal("account 1"))
            .values({"name": op.inline_literal("account 2")})
        )
        op.execute(
            account.update()
            .where(account.c.id == op.inline_literal(1))
            .values({"id": op.inline_literal(2)})
        )
        context.assert_(
            "UPDATE account SET name='account 2' "
            "WHERE account.name = 'account 1'",
            "UPDATE account SET id=2 WHERE account.id = 1",
        )

    def test_cant_op(self):
        if hasattr(op, "_proxy"):
            del op._proxy
        assert_raises_message(
            NameError,
            "Can't invoke function 'inline_literal', as the "
            "proxy object has not yet been established "
            "for the Alembic 'Operations' class.  "
            "Try placing this code inside a callable.",
            op.inline_literal,
            "asdf",
        )

    def test_naming_changes(self):
        context = op_fixture()
        op.alter_column("t", "c", name="x")
        context.assert_("ALTER TABLE t RENAME c TO x")

        context = op_fixture()
        op.alter_column("t", "c", new_column_name="x")
        context.assert_("ALTER TABLE t RENAME c TO x")

        context = op_fixture("mysql")
        op.drop_constraint("f1", "t1", type="foreignkey")
        context.assert_("ALTER TABLE t1 DROP FOREIGN KEY f1")

        context = op_fixture("mysql")
        op.drop_constraint("f1", "t1", type_="foreignkey")
        context.assert_("ALTER TABLE t1 DROP FOREIGN KEY f1")

    def test_naming_changes_drop_idx(self):
        context = op_fixture("mssql")
        op.drop_index("ik_test", tablename="t1")
        context.assert_("DROP INDEX ik_test ON t1")

    @config.requirements.comments
    def test_create_table_comment_op(self):
        context = op_fixture()

        op.create_table_comment("some_table", "table comment")

        context.assert_("COMMENT ON TABLE some_table IS 'table comment'")

    @config.requirements.comments
    def test_drop_table_comment_op(self):
        context = op_fixture()

        op.drop_table_comment("some_table")

        context.assert_("COMMENT ON TABLE some_table IS NULL")


class SQLModeOpTest(TestBase):
    def test_auto_literals(self):
        context = op_fixture(as_sql=True, literal_binds=True)
        from sqlalchemy.sql import table, column
        from sqlalchemy import String, Integer

        account = table(
            "account", column("name", String), column("id", Integer)
        )
        op.execute(
            account.update()
            .where(account.c.name == op.inline_literal("account 1"))
            .values({"name": op.inline_literal("account 2")})
        )
        op.execute(text("update table set foo=:bar").bindparams(bar="bat"))
        context.assert_(
            "UPDATE account SET name='account 2' "
            "WHERE account.name = 'account 1'",
            "update table set foo='bat'",
        )

    def test_create_table_literal_binds(self):
        context = op_fixture(as_sql=True, literal_binds=True)

        op.create_table(
            "some_table",
            Column("id", Integer, primary_key=True),
            Column("st_id", Integer, ForeignKey("some_table.id")),
        )

        context.assert_(
            "CREATE TABLE some_table (id INTEGER NOT NULL, st_id INTEGER, "
            "PRIMARY KEY (id), FOREIGN KEY(st_id) REFERENCES some_table (id))"
        )


class CustomOpTest(TestBase):
    def test_custom_op(self):
        from alembic.operations import Operations, MigrateOperation

        @Operations.register_operation("create_sequence")
        class CreateSequenceOp(MigrateOperation):
            """Create a SEQUENCE."""

            def __init__(self, sequence_name, **kw):
                self.sequence_name = sequence_name
                self.kw = kw

            @classmethod
            def create_sequence(cls, operations, sequence_name, **kw):
                """Issue a "CREATE SEQUENCE" instruction."""

                op = CreateSequenceOp(sequence_name, **kw)
                return operations.invoke(op)

        @Operations.implementation_for(CreateSequenceOp)
        def create_sequence(operations, operation):
            operations.execute("CREATE SEQUENCE %s" % operation.sequence_name)

        context = op_fixture()
        op.create_sequence("foob")
        context.assert_("CREATE SEQUENCE foob")


class EnsureOrigObjectFromToTest(TestBase):
    """the to_XYZ and from_XYZ methods are used heavily in autogenerate.

    It's critical that these methods, at least the "drop" form,
    always return the *same* object if available so that all the info
    passed into to_XYZ is maintained in the from_XYZ.


    """

    def test_drop_index(self):
        schema_obj = schemaobj.SchemaObjects()
        idx = schema_obj.index("x", "y", ["z"])
        op = ops.DropIndexOp.from_index(idx)
        is_(op.to_index(), idx)

    def test_create_index(self):
        schema_obj = schemaobj.SchemaObjects()
        idx = schema_obj.index("x", "y", ["z"])
        op = ops.CreateIndexOp.from_index(idx)
        is_(op.to_index(), idx)

    def test_drop_table(self):
        schema_obj = schemaobj.SchemaObjects()
        table = schema_obj.table("x", Column("q", Integer))
        op = ops.DropTableOp.from_table(table)
        is_(op.to_table(), table)

    def test_create_table(self):
        schema_obj = schemaobj.SchemaObjects()
        table = schema_obj.table("x", Column("q", Integer))
        op = ops.CreateTableOp.from_table(table)
        is_(op.to_table(), table)

    def test_drop_unique_constraint(self):
        schema_obj = schemaobj.SchemaObjects()
        const = schema_obj.unique_constraint("x", "foobar", ["a"])
        op = ops.DropConstraintOp.from_constraint(const)
        is_(op.to_constraint(), const)

    def test_drop_constraint_not_available(self):
        op = ops.DropConstraintOp("x", "y", type_="unique")
        assert_raises_message(
            ValueError, "constraint cannot be produced", op.to_constraint
        )


class BackendAlterColumnTest(AlterColRoundTripFixture, TestBase):
    __backend__ = True

    def test_rename_column(self):
        self._run_alter_col({}, {"name": "newname"})

    def test_modify_type_int_str(self):
        self._run_alter_col({"type": Integer()}, {"type": String(50)})

    def test_add_server_default_int(self):
        self._run_alter_col({"type": Integer}, {"server_default": text("5")})

    def test_modify_server_default_int(self):
        self._run_alter_col(
            {"type": Integer, "server_default": text("2")},
            {"server_default": text("5")},
        )

    def test_modify_nullable_to_non(self):
        self._run_alter_col({}, {"nullable": False})

    def test_modify_non_nullable_to_nullable(self):
        self._run_alter_col({"nullable": False}, {"nullable": True})
