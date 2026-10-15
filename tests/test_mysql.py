from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Computed
from sqlalchemy import DATETIME
from sqlalchemy import Enum
from sqlalchemy import exc
from sqlalchemy import Float
from sqlalchemy import func
from sqlalchemy import Identity
from sqlalchemy import Index
from sqlalchemy import inspect
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import text
from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.mysql import DOUBLE as MySQL_DOUBLE
from sqlalchemy.dialects.mysql import ENUM as MySQL_ENUM
from sqlalchemy.dialects.mysql import TINYINT as MySQL_TINYINT
from sqlalchemy.dialects.mysql import VARCHAR

from alembic import autogenerate
from alembic import op
from alembic import testing
from alembic import util
from alembic.autogenerate import api
from alembic.autogenerate.compare.constraints import _compare_nullable
from alembic.migration import MigrationContext
from alembic.operations import ops
from alembic.testing import assert_raises_message
from alembic.testing import combinations
from alembic.testing import config
from alembic.testing import eq_ignore_whitespace
from alembic.testing import is_
from alembic.testing.fixtures import AlterColRoundTripFixture
from alembic.testing.fixtures import op_fixture
from alembic.testing.fixtures import TestBase

if True:
    from alembic.autogenerate.compare.server_defaults import (
        _user_compare_server_default,
    )
    from alembic.autogenerate.compare.types import (
        _dialect_impl_compare_type as _compare_type,
    )
    from alembic.ddl.mysql import MySQLImpl


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

    def test_add_column_with_empty_comment(self):
        context = op_fixture("mysql")
        op.add_column("t", Column("q", Integer, comment=""))
        context.assert_("ALTER TABLE t ADD COLUMN q INTEGER COMMENT ''")

    def test_add_column_if_not_exists(self):
        context = op_fixture("mysql")
        op.add_column("t", Column("c", Integer), if_not_exists=True)
        context.assert_("ALTER TABLE t ADD COLUMN IF NOT EXISTS c INTEGER")

    def test_drop_column_if_exists(self):
        context = op_fixture("mysql")
        op.drop_column("t", "c", if_exists=True)
        context.assert_("ALTER TABLE t DROP COLUMN IF EXISTS c")

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
            _compare_nullable,
            _compare_type,
            # note that _user_compare_server_default does not actually
            # do a server default compare here, compare_server_default
            # is False so this just assigns the existing default to the
            # AlterColumnOp
            _user_compare_server_default,
        ):
            fn(
                autogen_context,
                operation,
                None,
                "t",
                "c",
                Column("c", Float(), nullable=False, server_default=text("0")),
                Column("c", Float(), nullable=True, server_default=text("0")),
            )

        op.invoke(operation)
        context.assert_("ALTER TABLE t MODIFY c FLOAT NULL DEFAULT 0")

    def test_alter_column_change_collation(self):
        context = op_fixture("mysql")
        op.alter_column(
            "t1",
            "c1",
            nullable=False,
            existing_type=String(50),
            type_=VARCHAR(
                50, charset="utf8mb4", collation="utf8mb4/utf8mb4_unicode_ci"
            ),
        )
        context.assert_(
            "ALTER TABLE t1 MODIFY c1 VARCHAR(50) "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4/utf8mb4_unicode_ci NOT NULL"
        )

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

    def test_add_column_computed(self):
        context = op_fixture("mysql")
        op.add_column(
            "t1",
            Column("some_column", Integer, Computed("foo * 5")),
        )
        context.assert_(
            "ALTER TABLE t1 ADD COLUMN some_column "
            "INTEGER GENERATED ALWAYS AS (foo * 5)"
        )

    def test_drop_fk(self):
        context = op_fixture("mysql")
        op.drop_constraint("f1", "t1", type_="foreignkey")
        context.assert_("ALTER TABLE t1 DROP FOREIGN KEY f1")

    def test_drop_fk_legacy(self):
        """#1245"""
        context = op_fixture("mysql")
        op.drop_constraint("f1", "t1", "foreignkey")
        context.assert_("ALTER TABLE t1 DROP FOREIGN KEY f1")

    def test_drop_fk_quoted(self):
        context = op_fixture("mysql")
        op.drop_constraint("MyFk", "MyTable", type_="foreignkey")
        context.assert_("ALTER TABLE `MyTable` DROP FOREIGN KEY `MyFk`")

    def test_drop_constraint_primary(self):
        context = op_fixture("mysql")
        op.drop_constraint("primary", "t1", type_="primary")
        context.assert_("ALTER TABLE t1 DROP PRIMARY KEY")

    def test_drop_unique(self):
        context = op_fixture("mysql")
        op.drop_constraint("f1", "t1", type_="unique")
        context.assert_("ALTER TABLE t1 DROP INDEX f1")

    def test_drop_unique_quoted(self):
        context = op_fixture("mysql")
        op.drop_constraint("MyUnique", "MyTable", type_="unique")
        context.assert_("ALTER TABLE `MyTable` DROP INDEX `MyUnique`")

    def test_drop_check_mariadb(self):
        context = op_fixture("mariadb")
        op.drop_constraint("f1", "t1", type_="check")
        context.assert_("ALTER TABLE t1 DROP CONSTRAINT f1")

    def test_drop_check_quoted_mariadb(self):
        context = op_fixture("mariadb")
        op.drop_constraint("MyCheck", "MyTable", type_="check")
        context.assert_("ALTER TABLE `MyTable` DROP CONSTRAINT `MyCheck`")

    def test_drop_check_mysql(self):
        context = op_fixture("mysql")
        op.drop_constraint("f1", "t1", type_="check")
        context.assert_("ALTER TABLE t1 DROP CHECK f1")

    def test_drop_check_quoted_mysql(self):
        context = op_fixture("mysql")
        op.drop_constraint("MyCheck", "MyTable", type_="check")
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
            type_="typo",
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
        (lambda: Computed("foo * 5"), lambda: None),
        (lambda: None, lambda: Computed("foo * 5")),
        (
            lambda: Computed("foo * 42"),
            lambda: Computed("foo * 5"),
        ),
    )
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
        (lambda: Identity(), lambda: None),
        (lambda: None, lambda: Identity()),
        (lambda: Identity(), lambda: Identity()),
    )
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


_server_default_combinations = combinations(
    (Integer(), None, "5", "5", "'5'", "5", False),
    (Integer(), None, "5", "7", "'5'", "5", True),
    (Integer(), None, None, "0", None, None, True),
    # a Boolean column is reflected as TINYINT(1)
    (
        Boolean(),
        MySQL_TINYINT(display_width=1),
        "1",
        "1",
        "'1'",
        "1",
        False,
    ),
    (Boolean(), MySQL_TINYINT(display_width=1), "1", "0", "'1'", "1", True),
    (MySQL_TINYINT(display_width=1), None, "1", "1", "'1'", "1", False),
    (MySQL_TINYINT(display_width=1), None, "1", "0", "'1'", "1", True),
    (Float(), None, "1", "1", "'1'", "1", False),
    (Float(), None, "1", "2", "'1'", "1", True),
    # SQLAlchemy renders a fractional literal as an expression default,
    # e.g. "DEFAULT (2.5)", which MySQL then reports with the parenthesis
    (MySQL_DOUBLE(), None, "2.5", "2.5", "(2.5)", "2.5", False),
    (MySQL_DOUBLE(), None, "2.5", "3.5", "(2.5)", "2.5", True),
    (MySQL_DOUBLE(), None, "3", "3", "'3'", "3", False),
    (Numeric(10, 2), None, "3.50", "3.50", "(3.50)", "3.50", False),
    (Numeric(10, 2), None, "3.50", "4.50", "(3.50)", "3.50", True),
    (String(20), None, "'x'", "'x'", "'x'", "'x'", False),
    (String(20), None, "'x'", "'y'", "'x'", "'x'", True),
    # an expression default is reported by MySQL with the parenthesis
    # SQLAlchemy rendered and by MariaDB without them; either form
    # compares as equal to either form in the metadata, and the
    # comparison remains case insensitive
    (
        Float(),
        None,
        "(rand())",
        "(rand())",
        "(rand())",
        "rand()",
        False,
        config.requirements.expression_server_defaults,
    ),
    (
        Float(),
        None,
        "(rand())",
        "(RAND())",
        "(rand())",
        "rand()",
        False,
        config.requirements.expression_server_defaults,
    ),
    (
        Float(),
        None,
        "(rand())",
        "rand()",
        "(rand())",
        "rand()",
        False,
        config.requirements.expression_server_defaults,
    ),
    (
        Float(),
        None,
        "(rand())",
        "1",
        "(rand())",
        "rand()",
        True,
        config.requirements.expression_server_defaults,
    ),
    # MariaDB renders CURRENT_TIMESTAMP as the function call
    # "current_timestamp()"
    (
        TIMESTAMP(),
        None,
        "CURRENT_TIMESTAMP",
        "CURRENT_TIMESTAMP",
        "CURRENT_TIMESTAMP",
        "current_timestamp()",
        False,
    ),
    (
        TIMESTAMP(),
        None,
        None,
        "CURRENT_TIMESTAMP",
        None,
        None,
        True,
    ),
    # note SQLAlchemy reflection bundles the ON UPDATE part into the
    # server default reflection, see
    # https://github.com/sqlalchemy/sqlalchemy/issues/4652
    (
        TIMESTAMP(),
        None,
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "current_timestamp() ON UPDATE current_timestamp()",
        False,
    ),
    (
        TIMESTAMP(),
        None,
        None,
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        None,
        None,
        True,
    ),
    argnames="type_, inspector_type, ddl_default, "
    "rendered_metadata_default, mysql_inspector_default, "
    "mariadb_inspector_default, expected",
    # ids read as "<repr of type_>-<ddl_default>-<metadata default>"; the
    # remaining positions are passed to the test but left out of the id
    id_="rassaaa",
)
"""Server default comparison cases shared by the unit tests and the round
trip test below.

``ddl_default`` is the default as rendered into the CREATE TABLE
statement, or ``None`` for a column created with no default.
``mysql_inspector_default`` and ``mariadb_inspector_default`` are what
each backend reports for such a column, and ``inspector_type`` the type
it reports where that differs from ``type_``; the round trip test gets
all three from reflection against the database actually being tested
instead.

"""


class _CompareServerDefaultFixture(TestBase):
    """Run the shared combinations against
    :meth:`.MySQLImpl.compare_server_default` for a single dialect.

    """

    __dialect__: str

    @testing.fixture
    def impl(self):
        return MigrationContext.configure(dialect_name=self.__dialect__).impl

    def _inspector_default(
        self, mysql_inspector_default, mariadb_inspector_default
    ):
        raise NotImplementedError()

    @_server_default_combinations
    def test_compare_server_default(
        self,
        impl,
        type_,
        inspector_type,
        ddl_default,
        rendered_metadata_default,
        mysql_inspector_default,
        mariadb_inspector_default,
        expected,
    ):
        is_(
            impl.compare_server_default(
                Column("somecol", inspector_type or type_),
                Column("somecol", type_),
                rendered_metadata_default,
                self._inspector_default(
                    mysql_inspector_default, mariadb_inspector_default
                ),
            ),
            expected,
        )


class MySQLCompareServerDefaultTest(_CompareServerDefaultFixture):
    """unit tests for :meth:`.MySQLImpl.compare_server_default` against the
    values MySQL 8 / MySQL 9 report.

    MySQL reports a literal server default in quoted form, e.g. ``'1'``,
    and an expression default with the parenthesis included, e.g.
    ``(rand())``.

    """

    __dialect__ = "mysql"

    def _inspector_default(
        self, mysql_inspector_default, mariadb_inspector_default
    ):
        return mysql_inspector_default


class MariaDBCompareServerDefaultTest(_CompareServerDefaultFixture):
    """unit tests for :meth:`.MySQLImpl.compare_server_default` against the
    values MariaDB reports.

    MariaDB reports a literal server default unquoted, an expression
    default without the parenthesis SQLAlchemy rendered, and a
    no-argument function such as ``CURRENT_TIMESTAMP`` as a function
    call.

    """

    __dialect__ = "mariadb"

    def _inspector_default(
        self, mysql_inspector_default, mariadb_inspector_default
    ):
        return mariadb_inspector_default


class MySQLCompareServerDefaultRoundTripTest(TestBase):
    """round trip tests for :meth:`.MySQLImpl.compare_server_default`.

    the table is created on the target backend and the reflected server
    default is compared against the metadata default, so that the
    quoting and casing conventions of the backend in use are those
    actually tested.

    """

    __only_on__ = "mysql", "mariadb"
    __backend__ = True

    @_server_default_combinations
    def test_compare_server_default(
        self,
        connection,
        metadata,
        type_,
        inspector_type,
        ddl_default,
        rendered_metadata_default,
        mysql_inspector_default,
        mariadb_inspector_default,
        expected,
    ):
        Table(
            "test",
            metadata,
            Column(
                "somecol",
                type_,
                server_default=text(ddl_default) if ddl_default else None,
            ),
        ).create(connection)

        reflected = Table("test", MetaData(), autoload_with=connection)
        inspector_default = inspect(connection).get_columns("test")[0][
            "default"
        ]

        impl = MigrationContext.configure(
            connection,
            opts={"compare_type": True, "compare_server_default": True},
        ).impl

        is_(
            impl.compare_server_default(
                reflected.c.somecol,
                Column("somecol", type_),
                rendered_metadata_default,
                inspector_default,
            ),
            expected,
        )


class MySQLAutogenRenderTest(TestBase):
    def setUp(self):
        ctx_opts = {
            "sqlalchemy_module_prefix": "sa.",
            "alembic_module_prefix": "op.",
            "target_metadata": MetaData(),
        }
        context = MigrationContext.configure(
            dialect_name="mysql", opts=ctx_opts
        )

        self.autogen_context = api.AutogenContext(context)

    def test_render_add_index_expr_binary(self):
        m = MetaData()
        t = Table(
            "t",
            m,
            Column("x", Integer, primary_key=True),
            Column("y", Integer),
        )
        idx = Index("foo_idx", t.c.x > 5)

        eq_ignore_whitespace(
            autogenerate.render_op_text(
                self.autogen_context, ops.CreateIndexOp.from_index(idx)
            ),
            "op.create_index('foo_idx', 't', "
            "[sa.literal_column('(x > 5)')], unique=False)",
        )

    def test_render_add_index_expr_unary(self):
        m = MetaData()
        t = Table(
            "t",
            m,
            Column("x", Integer, primary_key=True),
            Column("y", Integer),
        )
        idx1 = Index("foo_idx", -t.c.x)
        idx2 = Index("foo_idx", t.c.x.desc())

        eq_ignore_whitespace(
            autogenerate.render_op_text(
                self.autogen_context, ops.CreateIndexOp.from_index(idx1)
            ),
            "op.create_index('foo_idx', 't', "
            "[sa.literal_column('(-x)')], unique=False)",
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(
                self.autogen_context, ops.CreateIndexOp.from_index(idx2)
            ),
            "op.create_index('foo_idx', 't', "
            "[sa.literal_column('x DESC')], unique=False)",
        )

    def test_render_add_index_expr_func(self):
        m = MetaData()
        t = Table(
            "t",
            m,
            Column("x", Integer, primary_key=True),
            Column("y", Integer, nullable=True),
        )
        idx = Index("foo_idx", t.c.x, func.coalesce(t.c.y, 0))

        eq_ignore_whitespace(
            autogenerate.render_op_text(
                self.autogen_context, ops.CreateIndexOp.from_index(idx)
            ),
            "op.create_index('foo_idx', 't', "
            "['x', sa.literal_column('(coalesce(y, 0))')], unique=False)",
        )


class MySQLEnumCompareTest(TestBase):
    """Test MySQL native ENUM comparison in autogenerate."""

    __only_on__ = "mysql", "mariadb"
    __backend__ = True

    @testing.fixture()
    def connection(self):
        with config.db.begin() as conn:
            yield conn

    # note False means the two enums are equivalent, True means they
    # are different
    @testing.combinations(
        (
            Enum("A", "B", "C", native_enum=True),
            Enum("A", "B", "C", native_enum=True),
            False,
        ),
        (
            Enum("A", "B", "C", native_enum=True),
            Enum("A", "B", "C", "D", native_enum=True),
            True,
        ),
        (
            Enum("A", "B", "C", "D", native_enum=True),
            Enum("A", "B", "C", native_enum=True),
            True,
        ),
        (
            Enum("A", "B", "C", native_enum=True),
            Enum("C", "B", "A", native_enum=True),
            False,  # These two enums are equivalent, change in order is not
            # counted
        ),
        (MySQL_ENUM("A", "B", "C"), MySQL_ENUM("A", "B", "C"), False),
        (MySQL_ENUM("A", "B", "C"), MySQL_ENUM("A", "B", "C", "D"), True),
        id_="ssa",
        argnames="inspected_type,metadata_type,expected",
    )
    def test_compare_enum_types(
        self, inspected_type, metadata_type, expected, connection
    ):
        impl = MySQLImpl(connection.dialect, connection, False, None, None, {})

        is_(
            impl.compare_type(
                Column("x", inspected_type), Column("x", metadata_type)
            ),
            expected,
        )
