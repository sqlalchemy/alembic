from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DATETIME
from sqlalchemy import exc
from sqlalchemy import Float
from sqlalchemy import func
from sqlalchemy import inspect
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import text
from sqlalchemy import TIMESTAMP

from alembic import op
from alembic import util
from alembic.autogenerate import api
from alembic.autogenerate import compare
from alembic.migration import MigrationContext
from alembic.operations import ops
from alembic.testing import assert_raises_message
from alembic.testing import combinations
from alembic.testing import config
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.fixtures import AlterColRoundTripFixture
from alembic.testing.fixtures import op_fixture
from alembic.testing.fixtures import TestBase
from alembic.util import sqla_compat


class MySQLOpTest(TestBase):
    def test_create_table_with_comment(self):
        context = op_fixture("mysql")
        op.create_table(
            "t2",
            Column("c1", Integer, primary_key=True),
            comment="This is a table comment",
        )
        context.assert_contains("COMMENT='This is a table comment'")

    def test_create_table_with_column_comments(self):
        context = op_fixture("mysql")
        op.create_table(
            "t2",
            Column("c1", Integer, primary_key=True, comment="c1 comment"),
            Column("c2", Integer, comment="c2 comment"),
            comment="This is a table comment",
        )

        context.assert_(
            "CREATE TABLE t2 "
            "(c1 INTEGER NOT NULL COMMENT 'c1 comment' AUTO_INCREMENT, "
            # TODO: why is there no space at the end here? is that on the
            # SQLA side?
            "c2 INTEGER COMMENT 'c2 comment', PRIMARY KEY (c1))"
            "COMMENT='This is a table comment'"
        )

    def test_add_column_with_comment(self):
        context = op_fixture("mysql")
        op.add_column("t", Column("q", Integer, comment="This is a comment"))
        context.assert_(
            "ALTER TABLE t ADD COLUMN q INTEGER COMMENT 'This is a comment'"
        )

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

    def test_alter_column_modify_datetime_default(self):
        # use CHANGE format when the datatype is DATETIME or TIMESTAMP,
        # as this is needed for a functional default which is what you'd
        # get with a DATETIME/TIMESTAMP.  Will also work in the very unlikely
        # case the default is a fixed timestamp value.
        context = op_fixture("mysql")
        op.alter_column(
            "t",
            "c",
            existing_type=DATETIME(),
            server_default=text("CURRENT_TIMESTAMP"),
        )
        context.assert_(
            "ALTER TABLE t CHANGE c c DATETIME NULL DEFAULT CURRENT_TIMESTAMP"
        )

    def test_alter_column_modify_programmatic_default(self):
        # test issue #736
        # when autogenerate.compare creates the operation object
        # programmatically, the server_default of the op has the full
        # DefaultClause present.   make sure the usual renderer works.
        context = op_fixture("mysql")

        m1 = MetaData()

        autogen_context = api.AutogenContext(context, m1)

        operation = ops.AlterColumnOp("t", "c")
        for fn in (
            compare._compare_nullable,
            compare._compare_type,
            compare._compare_server_default,
        ):
            fn(
                autogen_context,
                operation,
                None,
                "t",
                "c",
                Column("c", Float(), nullable=False, server_default=text("0")),
                Column("c", Float(), nullable=True, default=0),
            )
        op.invoke(operation)
        context.assert_("ALTER TABLE t MODIFY c FLOAT NULL DEFAULT 0")

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

    def test_alter_column_add_comment(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1",
            "c1",
            comment="This is a column comment",
            existing_type=Boolean(),
            schema="foo",
        )

        context.assert_(
            "ALTER TABLE foo.t1 MODIFY c1 BOOL NULL "
            "COMMENT 'This is a column comment'"
        )

    def test_alter_column_add_comment_quoting(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1",
            "c1",
            comment="This is a 'column' comment",
            existing_type=Boolean(),
            schema="foo",
        )

        context.assert_(
            "ALTER TABLE foo.t1 MODIFY c1 BOOL NULL "
            "COMMENT 'This is a ''column'' comment'"
        )

    def test_alter_column_drop_comment(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t",
            "c",
            existing_type=Boolean(),
            schema="foo",
            comment=None,
            existing_comment="This is a column comment",
        )

        context.assert_("ALTER TABLE foo.t MODIFY c BOOL NULL")

    def test_alter_column_existing_comment(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1",
            "c1",
            nullable=False,
            existing_comment="existing column comment",
            existing_type=Integer,
        )

        context.assert_(
            "ALTER TABLE t1 MODIFY c1 INTEGER NOT NULL "
            "COMMENT 'existing column comment'"
        )

    def test_rename_column_existing_comment(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1",
            "c1",
            new_column_name="newc1",
            existing_nullable=False,
            existing_comment="existing column comment",
            existing_type=Integer,
        )

        context.assert_(
            "ALTER TABLE t1 CHANGE c1 newc1 INTEGER NOT NULL "
            "COMMENT 'existing column comment'"
        )

    def test_alter_column_new_comment_replaces_existing(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1",
            "c1",
            nullable=False,
            comment="This is a column comment",
            existing_comment="existing column comment",
            existing_type=Integer,
        )

        context.assert_(
            "ALTER TABLE t1 MODIFY c1 INTEGER NOT NULL "
            "COMMENT 'This is a column comment'"
        )

    def test_create_table_comment(self):
        # this is handled by SQLAlchemy's compilers
        context = op_fixture("mysql")
        op.create_table_comment("t2", comment="t2 table", schema="foo")
        context.assert_("ALTER TABLE foo.t2 COMMENT 't2 table'")

    def test_drop_table_comment(self):
        # this is handled by SQLAlchemy's compilers
        context = op_fixture("mysql")
        op.drop_table_comment("t2", existing_comment="t2 table", schema="foo")
        context.assert_("ALTER TABLE foo.t2 COMMENT ''")

    @config.requirements.computed_columns_api
    def test_add_column_computed(self):
        context = op_fixture("mysql")
        op.add_column(
            "t1",
            Column("some_column", Integer, sqla_compat.Computed("foo * 5")),
        )
        context.assert_(
            "ALTER TABLE t1 ADD COLUMN some_column "
            "INTEGER GENERATED ALWAYS AS (foo * 5)"
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

    def test_drop_check_mariadb(self):
        context = op_fixture("mariadb")
        op.drop_constraint("f1", "t1", "check")
        context.assert_("ALTER TABLE t1 DROP CONSTRAINT f1")

    def test_drop_check_quoted_mariadb(self):
        context = op_fixture("mariadb")
        op.drop_constraint("MyCheck", "MyTable", "check")
        context.assert_("ALTER TABLE `MyTable` DROP CONSTRAINT `MyCheck`")

    def test_drop_check_mysql(self):
        context = op_fixture("mysql")
        op.drop_constraint("f1", "t1", "check")
        context.assert_("ALTER TABLE t1 DROP CHECK f1")

    def test_drop_check_quoted_mysql(self):
        context = op_fixture("mysql")
        op.drop_constraint("MyCheck", "MyTable", "check")
        context.assert_("ALTER TABLE `MyTable` DROP CHECK `MyCheck`")

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

    @combinations(
        (lambda: sqla_compat.Computed("foo * 5"), lambda: None),
        (lambda: None, lambda: sqla_compat.Computed("foo * 5")),
        (
            lambda: sqla_compat.Computed("foo * 42"),
            lambda: sqla_compat.Computed("foo * 5"),
        ),
    )
    @config.requirements.computed_columns_api
    def test_alter_column_computed_not_supported(self, sd, esd):
        op_fixture("mysql")
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

    @combinations(
        (lambda: sqla_compat.Identity(), lambda: None),
        (lambda: None, lambda: sqla_compat.Identity()),
        (
            lambda: sqla_compat.Identity(),
            lambda: sqla_compat.Identity(),
        ),
    )
    @config.requirements.identity_columns_api
    def test_alter_column_identity_not_supported(self, sd, esd):
        op_fixture()
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


class MySQLBackendOpTest(AlterColRoundTripFixture, TestBase):
    __only_on__ = "mysql", "mariadb"
    __backend__ = True

    def test_add_timestamp_server_default_current_timestamp(self):
        self._run_alter_col(
            {"type": TIMESTAMP()},
            {"server_default": text("CURRENT_TIMESTAMP")},
        )

    def test_add_datetime_server_default_current_timestamp(self):
        self._run_alter_col(
            {"type": DATETIME()}, {"server_default": text("CURRENT_TIMESTAMP")}
        )

    def test_add_timestamp_server_default_now(self):
        self._run_alter_col(
            {"type": TIMESTAMP()},
            {"server_default": text("NOW()")},
            compare={"server_default": text("CURRENT_TIMESTAMP")},
        )

    def test_add_datetime_server_default_now(self):
        self._run_alter_col(
            {"type": DATETIME()},
            {"server_default": text("NOW()")},
            compare={"server_default": text("CURRENT_TIMESTAMP")},
        )

    def test_add_timestamp_server_default_current_timestamp_bundle_onupdate(
        self,
    ):
        # note SQLAlchemy reflection bundles the ON UPDATE part into the
        # server default reflection see
        # https://github.com/sqlalchemy/sqlalchemy/issues/4652
        self._run_alter_col(
            {"type": TIMESTAMP()},
            {
                "server_default": text(
                    "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
                )
            },
        )

    def test_add_datetime_server_default_current_timestamp_bundle_onupdate(
        self,
    ):
        # note SQLAlchemy reflection bundles the ON UPDATE part into the
        # server default reflection see
        # https://github.com/sqlalchemy/sqlalchemy/issues/4652
        self._run_alter_col(
            {"type": DATETIME()},
            {
                "server_default": text(
                    "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
                )
            },
        )


class MySQLDefaultCompareTest(TestBase):
    __only_on__ = "mysql", "mariadb"
    __backend__ = True

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
        self.metadata = MetaData()

    def tearDown(self):
        with config.db.begin() as conn:
            self.metadata.drop_all(conn)

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
        insp = inspect(self.bind)
        cols = insp.get_columns(t1.name)
        refl = Table(t1.name, MetaData())
        sqla_compat._reflect_table(insp, refl, None)
        ctx = self.autogen_context["context"]
        return ctx.impl.compare_server_default(
            refl.c[cols[0]["name"]], col, rendered, cols[0]["default"]
        )

    def test_compare_timestamp_current_timestamp(self):
        self._compare_default_roundtrip(TIMESTAMP(), "CURRENT_TIMESTAMP")

    def test_compare_timestamp_current_timestamp_diff(self):
        self._compare_default_roundtrip(TIMESTAMP(), None, "CURRENT_TIMESTAMP")

    def test_compare_timestamp_current_timestamp_bundle_onupdate(self):
        self._compare_default_roundtrip(
            TIMESTAMP(), "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
        )

    def test_compare_timestamp_current_timestamp_diff_bundle_onupdate(self):
        self._compare_default_roundtrip(
            TIMESTAMP(), None, "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
        )

    def test_compare_integer_from_none(self):
        self._compare_default_roundtrip(Integer(), None, "0")

    def test_compare_integer_same(self):
        self._compare_default_roundtrip(Integer(), "5")

    def test_compare_integer_diff(self):
        self._compare_default_roundtrip(Integer(), "5", "7")

    def test_compare_boolean_same(self):
        self._compare_default_roundtrip(Boolean(), "1")

    def test_compare_boolean_diff(self):
        self._compare_default_roundtrip(Boolean(), "1", "0")
