from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import func
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import text
from sqlalchemy import TIMESTAMP
from sqlalchemy.engine.reflection import Inspector

from alembic import op
from alembic import util
from alembic.migration import MigrationContext
from alembic.testing import assert_raises_message
from alembic.testing import config
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.fixtures import op_fixture
from alembic.testing.fixtures import TestBase


class MySQLOpTest(TestBase):
    def test_rename_column(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1", "c1", new_column_name="c2", existing_type=Integer
        )
        context.assert_("ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL")

    def test_rename_column_quotes_needed_one(self):
        context = op_fixture("mysql")
        op.alter_column(
            "MyTable",
            "ColumnOne",
            new_column_name="ColumnTwo",
            existing_type=Integer,
        )
        context.assert_(
            "ALTER TABLE `MyTable` CHANGE `ColumnOne` `ColumnTwo` INTEGER NULL"
        )

    def test_rename_column_quotes_needed_two(self):
        context = op_fixture("mysql")
        op.alter_column(
            "my table",
            "column one",
            new_column_name="column two",
            existing_type=Integer,
        )
        context.assert_(
            "ALTER TABLE `my table` CHANGE `column one` "
            "`column two` INTEGER NULL"
        )

    def test_rename_column_serv_default(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1",
            "c1",
            new_column_name="c2",
            existing_type=Integer,
            existing_server_default="q",
        )
        context.assert_("ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL DEFAULT 'q'")

    def test_rename_column_serv_compiled_default(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1",
            "c1",
            existing_type=Integer,
            server_default=func.utc_thing(func.current_timestamp()),
        )
        # this is not a valid MySQL default but the point is to just
        # test SQL expression rendering
        context.assert_(
            "ALTER TABLE t1 ALTER COLUMN c1 "
            "SET DEFAULT utc_thing(CURRENT_TIMESTAMP)"
        )

    def test_rename_column_autoincrement(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1",
            "c1",
            new_column_name="c2",
            existing_type=Integer,
            existing_autoincrement=True,
        )
        context.assert_(
            "ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL AUTO_INCREMENT"
        )

    def test_col_add_autoincrement(self):
        context = op_fixture("mysql")
        op.alter_column("t1", "c1", existing_type=Integer, autoincrement=True)
        context.assert_("ALTER TABLE t1 MODIFY c1 INTEGER NULL AUTO_INCREMENT")

    def test_col_remove_autoincrement(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1",
            "c1",
            existing_type=Integer,
            existing_autoincrement=True,
            autoincrement=False,
        )
        context.assert_("ALTER TABLE t1 MODIFY c1 INTEGER NULL")

    def test_col_dont_remove_server_default(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1",
            "c1",
            existing_type=Integer,
            existing_server_default="1",
            server_default=False,
        )

        context.assert_()

    def test_alter_column_drop_default(self):
        context = op_fixture("mysql")
        op.alter_column("t", "c", existing_type=Integer, server_default=None)
        context.assert_("ALTER TABLE t ALTER COLUMN c DROP DEFAULT")

    def test_alter_column_remove_schematype(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t",
            "c",
            type_=Integer,
            existing_type=Boolean(create_constraint=True, name="ck1"),
            server_default=None,
        )
        context.assert_("ALTER TABLE t MODIFY c INTEGER NULL")

    def test_alter_column_modify_default(self):
        context = op_fixture("mysql")
        # notice we dont need the existing type on this one...
        op.alter_column("t", "c", server_default="1")
        context.assert_("ALTER TABLE t ALTER COLUMN c SET DEFAULT '1'")

    def test_col_not_nullable(self):
        context = op_fixture("mysql")
        op.alter_column("t1", "c1", nullable=False, existing_type=Integer)
        context.assert_("ALTER TABLE t1 MODIFY c1 INTEGER NOT NULL")

    def test_col_not_nullable_existing_serv_default(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1",
            "c1",
            nullable=False,
            existing_type=Integer,
            existing_server_default="5",
        )
        context.assert_(
            "ALTER TABLE t1 MODIFY c1 INTEGER NOT NULL DEFAULT '5'"
        )

    def test_col_nullable(self):
        context = op_fixture("mysql")
        op.alter_column("t1", "c1", nullable=True, existing_type=Integer)
        context.assert_("ALTER TABLE t1 MODIFY c1 INTEGER NULL")

    def test_col_multi_alter(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1", "c1", nullable=False, server_default="q", type_=Integer
        )
        context.assert_(
            "ALTER TABLE t1 MODIFY c1 INTEGER NOT NULL DEFAULT 'q'"
        )

    def test_alter_column_multi_alter_w_drop_default(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1", "c1", nullable=False, server_default=None, type_=Integer
        )
        context.assert_("ALTER TABLE t1 MODIFY c1 INTEGER NOT NULL")

    def test_col_alter_type_required(self):
        op_fixture("mysql")
        assert_raises_message(
            util.CommandError,
            "MySQL CHANGE/MODIFY COLUMN operations require the existing type.",
            op.alter_column,
            "t1",
            "c1",
            nullable=False,
            server_default="q",
        )

    def test_drop_fk(self):
        context = op_fixture("mysql")
        op.drop_constraint("f1", "t1", "foreignkey")
        context.assert_("ALTER TABLE t1 DROP FOREIGN KEY f1")

    def test_drop_fk_quoted(self):
        context = op_fixture("mysql")
        op.drop_constraint("MyFk", "MyTable", "foreignkey")
        context.assert_("ALTER TABLE `MyTable` DROP FOREIGN KEY `MyFk`")

    def test_drop_constraint_primary(self):
        context = op_fixture("mysql")
        op.drop_constraint("primary", "t1", type_="primary")
        context.assert_("ALTER TABLE t1 DROP PRIMARY KEY")

    def test_drop_unique(self):
        context = op_fixture("mysql")
        op.drop_constraint("f1", "t1", "unique")
        context.assert_("ALTER TABLE t1 DROP INDEX f1")

    def test_drop_unique_quoted(self):
        context = op_fixture("mysql")
        op.drop_constraint("MyUnique", "MyTable", "unique")
        context.assert_("ALTER TABLE `MyTable` DROP INDEX `MyUnique`")

    def test_drop_check(self):
        context = op_fixture("mysql")
        op.drop_constraint("f1", "t1", "check")
        context.assert_("ALTER TABLE t1 DROP CONSTRAINT f1")

    def test_drop_check_quoted(self):
        context = op_fixture("mysql")
        op.drop_constraint("MyCheck", "MyTable", "check")
        context.assert_("ALTER TABLE `MyTable` DROP CONSTRAINT `MyCheck`")

    def test_drop_unknown(self):
        op_fixture("mysql")
        assert_raises_message(
            TypeError,
            "'type' can be one of 'check', 'foreignkey', "
            "'primary', 'unique', None",
            op.drop_constraint,
            "f1",
            "t1",
            "typo",
        )

    def test_drop_generic_constraint(self):
        op_fixture("mysql")
        assert_raises_message(
            NotImplementedError,
            "No generic 'DROP CONSTRAINT' in MySQL - please "
            "specify constraint type",
            op.drop_constraint,
            "f1",
            "t1",
        )


class MySQLDefaultCompareTest(TestBase):
    __only_on__ = "mysql"
    __backend__ = True

    __requires__ = ("mysql_timestamp_reflection",)

    @classmethod
    def setup_class(cls):
        cls.bind = config.db
        staging_env()
        context = MigrationContext.configure(
            connection=cls.bind.connect(),
            opts={"compare_type": True, "compare_server_default": True},
        )
        connection = context.bind
        cls.autogen_context = {
            "imports": set(),
            "connection": connection,
            "dialect": connection.dialect,
            "context": context,
        }

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def setUp(self):
        self.metadata = MetaData(self.bind)

    def tearDown(self):
        self.metadata.drop_all()

    def _compare_default_roundtrip(self, type_, txt, alternate=None):
        if alternate:
            expected = True
        else:
            alternate = txt
            expected = False
        t = Table(
            "test",
            self.metadata,
            Column(
                "somecol", type_, server_default=text(txt) if txt else None
            ),
        )
        t2 = Table(
            "test",
            MetaData(),
            Column("somecol", type_, server_default=text(alternate)),
        )
        assert (
            self._compare_default(t, t2, t2.c.somecol, alternate) is expected
        )

    def _compare_default(self, t1, t2, col, rendered):
        t1.create(self.bind)
        insp = Inspector.from_engine(self.bind)
        cols = insp.get_columns(t1.name)
        refl = Table(t1.name, MetaData())
        insp.reflecttable(refl, None)
        ctx = self.autogen_context["context"]
        return ctx.impl.compare_server_default(
            refl.c[cols[0]["name"]], col, rendered, cols[0]["default"]
        )

    def test_compare_timestamp_current_timestamp(self):
        self._compare_default_roundtrip(TIMESTAMP(), "CURRENT_TIMESTAMP")

    def test_compare_timestamp_current_timestamp_diff(self):
        self._compare_default_roundtrip(TIMESTAMP(), None, "CURRENT_TIMESTAMP")

    def test_compare_integer_same(self):
        self._compare_default_roundtrip(Integer(), "5")

    def test_compare_integer_diff(self):
        self._compare_default_roundtrip(Integer(), "5", "7")

    def test_compare_boolean_same(self):
        self._compare_default_roundtrip(Boolean(), "1")

    def test_compare_boolean_diff(self):
        self._compare_default_roundtrip(Boolean(), "1", "0")
