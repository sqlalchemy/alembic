import itertools

from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Computed
from sqlalchemy import DateTime
from sqlalchemy import exc
from sqlalchemy import Float
from sqlalchemy import func
from sqlalchemy import Identity
from sqlalchemy import Index
from sqlalchemy import inspect
from sqlalchemy import Integer
from sqlalchemy import Interval
from sqlalchemy import MetaData
from sqlalchemy import Numeric
from sqlalchemy import Sequence
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import text
from sqlalchemy import types
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.dialects.postgresql import HSTORE
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import TSRANGE
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import column
from sqlalchemy.sql import false
from sqlalchemy.sql import table
from sqlalchemy.sql.expression import literal_column

from alembic import autogenerate
from alembic import command
from alembic import op
from alembic import testing
from alembic import util
from alembic.autogenerate import api
from alembic.autogenerate.compare import _compare_server_default
from alembic.autogenerate.compare import _compare_tables
from alembic.autogenerate.compare import _render_server_default_for_compare
from alembic.migration import MigrationContext
from alembic.operations import ops
from alembic.script import ScriptDirectory
from alembic.testing import assert_raises_message
from alembic.testing import combinations
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import eq_ignore_whitespace
from alembic.testing import provide_metadata
from alembic.testing import resolve_lambda
from alembic.testing import schemacompare
from alembic.testing.assertions import expect_warnings
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.env import write_script
from alembic.testing.fixtures import capture_context_buffer
from alembic.testing.fixtures import FutureEngineMixin
from alembic.testing.fixtures import op_fixture
from alembic.testing.fixtures import TablesTest
from alembic.testing.fixtures import TestBase
from alembic.testing.suite._autogen_fixtures import AutogenFixtureTest


class PostgresqlOpTest(TestBase):
    def test_rename_table_postgresql(self):
        context = op_fixture("postgresql")
        op.rename_table("t1", "t2")
        context.assert_("ALTER TABLE t1 RENAME TO t2")

    def test_rename_table_schema_postgresql(self):
        context = op_fixture("postgresql")
        op.rename_table("t1", "t2", schema="foo")
        context.assert_("ALTER TABLE foo.t1 RENAME TO t2")

    def test_create_index_postgresql_expressions(self):
        context = op_fixture("postgresql")
        op.create_index(
            "geocoded",
            "locations",
            [text("lower(coordinates)")],
            postgresql_where=text("locations.coordinates != Null"),
        )
        context.assert_(
            "CREATE INDEX geocoded ON locations (lower(coordinates)) "
            "WHERE locations.coordinates != Null"
        )

    def test_create_index_postgresql_where(self):
        context = op_fixture("postgresql")
        op.create_index(
            "geocoded",
            "locations",
            ["coordinates"],
            postgresql_where=text("locations.coordinates != Null"),
        )
        context.assert_(
            "CREATE INDEX geocoded ON locations (coordinates) "
            "WHERE locations.coordinates != Null"
        )

    def test_create_index_postgresql_concurrently(self):
        context = op_fixture("postgresql")
        op.create_index(
            "geocoded",
            "locations",
            ["coordinates"],
            postgresql_concurrently=True,
        )
        context.assert_(
            "CREATE INDEX CONCURRENTLY geocoded ON locations (coordinates)"
        )

    def test_create_index_postgresql_include(self):
        context = op_fixture("postgresql")
        op.create_index(
            "i", "t", ["c1", "c2"], unique=False, postgresql_include=["inc"]
        )
        context.assert_("CREATE INDEX i ON t (c1, c2) INCLUDE (inc)")

    def test_create_index_postgresql_include_is_none(self):
        context = op_fixture("postgresql")
        op.create_index("i", "t", ["c1", "c2"], unique=False)
        context.assert_("CREATE INDEX i ON t (c1, c2)")

    def test_create_index_if_not_exists(self):
        context = op_fixture("postgresql")
        op.create_index("i", "t", ["c1", "c2"], if_not_exists=True)
        context.assert_("CREATE INDEX IF NOT EXISTS i ON t (c1, c2)")

    def test_create_fk_postgresql_not_valid(self):
        context = op_fixture("postgresql")
        op.create_foreign_key(
            "i", "t1", "t2", ["c1"], ["c2"], postgresql_not_valid=True
        )
        context.assert_(
            "ALTER TABLE t1 ADD CONSTRAINT i FOREIGN KEY(c1) "
            "REFERENCES t2 (c2) NOT VALID"
        )

    @config.combinations("include_table", "no_table", argnames="include_table")
    def test_drop_index_postgresql_concurrently(self, include_table):
        context = op_fixture("postgresql")
        if include_table == "include_table":
            op.drop_index(
                "geocoded",
                table_name="locations",
                postgresql_concurrently=True,
            )
        else:
            op.drop_index("geocoded", postgresql_concurrently=True)
        context.assert_("DROP INDEX CONCURRENTLY geocoded")

    def test_drop_index_if_exists(self):
        context = op_fixture("postgresql")
        op.drop_index("geocoded", if_exists=True)
        context.assert_("DROP INDEX IF EXISTS geocoded")

    def test_alter_column_type_using(self):
        context = op_fixture("postgresql")
        op.alter_column("t", "c", type_=Integer, postgresql_using="c::integer")
        context.assert_(
            "ALTER TABLE t ALTER COLUMN c TYPE INTEGER USING c::integer"
        )

    def test_add_column_if_not_exists(self):
        context = op_fixture("postgresql")
        op.add_column("t", Column("c", Integer), if_not_exists=True)
        context.assert_("ALTER TABLE t ADD COLUMN IF NOT EXISTS c INTEGER")

    def test_drop_column_if_exists(self):
        context = op_fixture("postgresql")
        op.drop_column("t", "c", if_exists=True)
        context.assert_("ALTER TABLE t DROP COLUMN IF EXISTS c")

    def test_col_w_pk_is_serial(self):
        context = op_fixture("postgresql")
        op.add_column("some_table", Column("q", Integer, primary_key=True))
        context.assert_("ALTER TABLE some_table ADD COLUMN q SERIAL NOT NULL")

    def test_create_exclude_constraint(self):
        context = op_fixture("postgresql")
        op.create_exclude_constraint(
            "ex1", "t1", ("x", ">"), where="x > 5", using="gist"
        )
        context.assert_(
            "ALTER TABLE t1 ADD CONSTRAINT ex1 EXCLUDE USING gist (x WITH >) "
            "WHERE (x > 5)"
        )

    def test_drop_exclude_or_other_constraint(self):
        context = op_fixture("postgresql")
        op.drop_constraint("t_excl_x", "TTable", type_=None)
        context.assert_('ALTER TABLE "TTable" DROP CONSTRAINT t_excl_x')

    def test_create_exclude_constraint_quoted_literal(self):
        context = op_fixture("postgresql")
        op.create_exclude_constraint(
            "ex1",
            "SomeTable",
            (column("SomeColumn"), ">"),
            where='"SomeColumn" > 5',
            using="gist",
        )
        context.assert_(
            'ALTER TABLE "SomeTable" ADD CONSTRAINT ex1 EXCLUDE USING gist '
            '("SomeColumn" WITH >) WHERE ("SomeColumn" > 5)'
        )

    def test_create_exclude_constraint_quoted_column(self):
        context = op_fixture("postgresql")
        op.create_exclude_constraint(
            "ex1",
            "SomeTable",
            (column("SomeColumn"), ">"),
            where=column("SomeColumn") > 5,
            using="gist",
        )
        context.assert_(
            'ALTER TABLE "SomeTable" ADD CONSTRAINT ex1 EXCLUDE '
            'USING gist ("SomeColumn" WITH >) WHERE ("SomeColumn" > 5)'
        )

    def test_add_column_with_comment(self):
        context = op_fixture("postgresql")
        op.add_column("t", Column("q", Integer, comment="This is a comment"))
        context.assert_(
            "ALTER TABLE t ADD COLUMN q INTEGER",
            "COMMENT ON COLUMN t.q IS 'This is a comment'",
        )

    def test_alter_column_with_comment(self):
        context = op_fixture("postgresql")
        op.alter_column(
            "t",
            "c",
            nullable=False,
            existing_type=Boolean(),
            schema="foo",
            comment="This is a column comment",
        )

        context.assert_(
            "ALTER TABLE foo.t ALTER COLUMN c SET NOT NULL",
            "COMMENT ON COLUMN foo.t.c IS 'This is a column comment'",
        )

    def test_alter_column_add_comment(self):
        context = op_fixture("postgresql")
        op.alter_column(
            "t",
            "c",
            existing_type=Boolean(),
            schema="foo",
            comment="This is a column comment",
        )

        context.assert_(
            "COMMENT ON COLUMN foo.t.c IS 'This is a column comment'"
        )

    def test_alter_column_add_comment_table_and_column_quoting(self):
        context = op_fixture("postgresql")
        op.alter_column(
            "T",
            "C",
            existing_type=Boolean(),
            schema="foo",
            comment="This is a column comment",
        )

        context.assert_(
            'COMMENT ON COLUMN foo."T"."C" IS \'This is a column comment\''
        )

    def test_alter_column_add_comment_quoting(self):
        context = op_fixture("postgresql")
        op.alter_column(
            "t",
            "c",
            existing_type=Boolean(),
            schema="foo",
            comment="This is a column 'comment'",
        )

        context.assert_(
            "COMMENT ON COLUMN foo.t.c IS 'This is a column ''comment'''"
        )

    def test_alter_column_drop_comment(self):
        context = op_fixture("postgresql")
        op.alter_column(
            "t",
            "c",
            existing_type=Boolean(),
            schema="foo",
            comment=None,
            existing_comment="This is a column comment",
        )

        context.assert_("COMMENT ON COLUMN foo.t.c IS NULL")

    def test_create_table_with_comment(self):
        context = op_fixture("postgresql")
        op.create_table(
            "t2",
            Column("c1", Integer, primary_key=True),
            Column("c2", Integer),
            comment="t2 comment",
        )
        context.assert_(
            "CREATE TABLE t2 (c1 SERIAL NOT NULL, "
            "c2 INTEGER, PRIMARY KEY (c1))",
            "COMMENT ON TABLE t2 IS 't2 comment'",
        )

    def test_create_table_with_column_comments(self):
        context = op_fixture("postgresql")
        op.create_table(
            "t2",
            Column("c1", Integer, primary_key=True, comment="c1 comment"),
            Column("c2", Integer, comment="c2 comment"),
            comment="t2 comment",
        )
        context.assert_(
            "CREATE TABLE t2 (c1 SERIAL NOT NULL, "
            "c2 INTEGER, PRIMARY KEY (c1))",
            "COMMENT ON TABLE t2 IS 't2 comment'",
            "COMMENT ON COLUMN t2.c1 IS 'c1 comment'",
            "COMMENT ON COLUMN t2.c2 IS 'c2 comment'",
        )

    def test_create_table_comment(self):
        # this is handled by SQLAlchemy's compilers
        context = op_fixture("postgresql")
        op.create_table_comment("t2", comment="t2 table", schema="foo")
        context.assert_("COMMENT ON TABLE foo.t2 IS 't2 table'")

    def test_drop_table_comment(self):
        # this is handled by SQLAlchemy's compilers
        context = op_fixture("postgresql")
        op.drop_table_comment("t2", existing_comment="t2 table", schema="foo")
        context.assert_("COMMENT ON TABLE foo.t2 IS NULL")

    @config.requirements.computed_columns
    def test_add_column_computed(self):
        context = op_fixture("postgresql")
        op.add_column(
            "t1",
            Column("some_column", Integer, Computed("foo * 5")),
        )
        context.assert_(
            "ALTER TABLE t1 ADD COLUMN some_column "
            "INTEGER GENERATED ALWAYS AS (foo * 5) STORED"
        )

    @combinations(
        (lambda: Computed("foo * 5"), lambda: None),
        (lambda: None, lambda: Computed("foo * 5")),
        (
            lambda: Computed("foo * 42"),
            lambda: Computed("foo * 5"),
        ),
    )
    @config.requirements.computed_columns
    def test_alter_column_computed_not_supported(self, sd, esd):
        op_fixture("postgresql")
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
        ({}, None),
        (dict(always=True), None),
        (
            dict(start=3, increment=33, maxvalue=99, cycle=True),
            "INCREMENT BY 33 START WITH 3 MAXVALUE 99 CYCLE",
        ),
    )
    def test_add_column_identity(self, kw, text):
        context = op_fixture("postgresql")
        op.add_column(
            "t1",
            Column("some_column", Integer, Identity(**kw)),
        )
        qualification = "ALWAYS" if kw.get("always", False) else "BY DEFAULT"
        options = " (%s)" % text if text else ""
        context.assert_(
            "ALTER TABLE t1 ADD COLUMN some_column "
            "INTEGER GENERATED %s AS IDENTITY%s" % (qualification, options)
        )

    @config.requirements.identity_columns
    @combinations(
        ({}, None),
        (dict(always=True), None),
        (
            dict(start=3, increment=33, maxvalue=99, cycle=True),
            "INCREMENT BY 33 START WITH 3 MAXVALUE 99 CYCLE",
        ),
    )
    def test_add_identity_to_column(self, kw, text):
        context = op_fixture("postgresql")
        op.alter_column(
            "t1",
            "some_column",
            server_default=Identity(**kw),
            existing_server_default=None,
        )
        qualification = "ALWAYS" if kw.get("always", False) else "BY DEFAULT"
        options = " (%s)" % text if text else ""
        context.assert_(
            "ALTER TABLE t1 ALTER COLUMN some_column ADD "
            "GENERATED %s AS IDENTITY%s" % (qualification, options)
        )

    @config.requirements.identity_columns
    def test_remove_identity_from_column(self):
        context = op_fixture("postgresql")
        op.alter_column(
            "t1",
            "some_column",
            server_default=None,
            existing_server_default=Identity(),
        )
        context.assert_(
            "ALTER TABLE t1 ALTER COLUMN some_column DROP IDENTITY"
        )

    @config.requirements.identity_columns
    @combinations(
        ({}, dict(always=True), "SET GENERATED ALWAYS"),
        (
            dict(always=True),
            dict(always=False, start=3),
            "SET GENERATED BY DEFAULT SET START WITH 3",
        ),
        (
            dict(always=True, start=3, increment=2, minvalue=-3, maxvalue=99),
            dict(
                always=True,
                start=3,
                increment=1,
                minvalue=-3,
                maxvalue=99,
                cycle=True,
            ),
            "SET CYCLE SET INCREMENT BY 1",
        ),
        (
            dict(
                always=False,
                start=3,
                maxvalue=9999,
                minvalue=0,
            ),
            dict(always=False, start=3, cache=2),
            "SET CACHE 2",
        ),
        (
            dict(always=False),
            dict(always=None, minvalue=0),
            "SET MINVALUE 0",
        ),
    )
    def test_change_identity_in_column(self, existing, updated, text):
        context = op_fixture("postgresql")
        op.alter_column(
            "t1",
            "some_column",
            server_default=Identity(**updated),
            existing_server_default=Identity(**existing),
        )
        context.assert_("ALTER TABLE t1 ALTER COLUMN some_column %s" % text)


class PGAutocommitBlockTest(TestBase):
    __only_on__ = "postgresql"
    __backend__ = True

    def setUp(self):
        self.conn = conn = config.db.connect()

        with conn.begin():
            conn.execute(
                text("CREATE TYPE mood AS ENUM ('sad', 'ok', 'happy')")
            )

    def tearDown(self):
        with self.conn.begin():
            self.conn.execute(text("DROP TYPE mood"))

    def test_alter_enum(self, migration_context):
        with migration_context.begin_transaction(_per_migration=True):
            with migration_context.autocommit_block():
                migration_context.execute(
                    text("ALTER TYPE mood ADD VALUE 'soso'")
                )


class PGAutocommitBlockTestFuture(FutureEngineMixin, PGAutocommitBlockTest):
    pass


class PGOfflineEnumTest(TestBase):
    def setUp(self):
        staging_env()
        self.cfg = cfg = _no_sql_testing_config()

        self.rid = rid = util.rev_id()

        self.script = script = ScriptDirectory.from_config(cfg)
        script.generate_revision(rid, None, refresh=True)

    def tearDown(self):
        clear_staging_env()

    def _inline_enum_script(self):
        write_script(
            self.script,
            self.rid,
            """
revision = '%s'
down_revision = None

from alembic import op
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy import Column


def upgrade():
    op.create_table("sometable",
        Column("data", ENUM("one", "two", "three", name="pgenum"))
    )


def downgrade():
    op.drop_table("sometable")
"""
            % self.rid,
        )

    def _distinct_enum_script(self):
        write_script(
            self.script,
            self.rid,
            """
revision = '%s'
down_revision = None

from alembic import op
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy import Column


def upgrade():
    enum = ENUM("one", "two", "three", name="pgenum", create_type=False)
    enum.create(op.get_bind(), checkfirst=False)
    op.create_table("sometable",
        Column("data", enum)
    )


def downgrade():
    op.drop_table("sometable")
    ENUM(name="pgenum").drop(op.get_bind(), checkfirst=False)

"""
            % self.rid,
        )

    def test_offline_inline_enum_create(self):
        self._inline_enum_script()
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.rid, sql=True)
        assert (
            "CREATE TYPE pgenum AS "
            "ENUM ('one', 'two', 'three')" in buf.getvalue()
        )
        assert "CREATE TABLE sometable (\n    data pgenum\n)" in buf.getvalue()

    def test_offline_inline_enum_drop(self):
        self._inline_enum_script()
        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, "%s:base" % self.rid, sql=True)
        assert "DROP TABLE sometable" in buf.getvalue()
        # no drop since we didn't emit events
        assert "DROP TYPE pgenum" not in buf.getvalue()

    def test_offline_distinct_enum_create(self):
        self._distinct_enum_script()
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.rid, sql=True)
        assert (
            "CREATE TYPE pgenum AS ENUM "
            "('one', 'two', 'three')" in buf.getvalue()
        )
        assert "CREATE TABLE sometable (\n    data pgenum\n)" in buf.getvalue()

    def test_offline_distinct_enum_drop(self):
        self._distinct_enum_script()
        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, "%s:base" % self.rid, sql=True)
        assert "DROP TABLE sometable" in buf.getvalue()
        assert "DROP TYPE pgenum" in buf.getvalue()


class PostgresqlInlineLiteralTest(TablesTest):
    __only_on__ = "postgresql"
    __backend__ = True

    @classmethod
    def define_tables(cls, metadata):
        Table("tab", metadata, Column("col", String(50)))

    @classmethod
    def insert_data(cls, connection):
        connection.execute(
            text(
                """
                insert into tab (col) values
                    ('old data 1'),
                    ('old data 2.1'),
                    ('old data 3')
            """
            )
        )

    def test_inline_percent(self, connection, ops_context):
        # TODO: here's the issue, you need to escape this.
        tab = table("tab", column("col"))
        ops_context.execute(
            tab.update()
            .where(tab.c.col.like(ops_context.inline_literal("%.%")))
            .values(col=ops_context.inline_literal("new data")),
            execution_options={"no_parameters": True},
        )
        eq_(
            connection.execute(
                text("select count(*) from tab where col='new data'")
            ).scalar(),
            1,
        )


class PostgresqlDefaultCompareTest(TestBase):
    __only_on__ = "postgresql"
    __backend__ = True

    @classmethod
    def setup_class(cls):
        cls.bind = config.db
        staging_env()
        cls.migration_context = MigrationContext.configure(
            connection=cls.bind.connect(),
            opts={"compare_type": True, "compare_server_default": True},
        )

    def setUp(self):
        self.metadata = MetaData()
        self.autogen_context = api.AutogenContext(self.migration_context)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def tearDown(self):
        with config.db.begin() as conn:
            self.metadata.drop_all(conn)

    def _compare_default_roundtrip(
        self, type_, orig_default, alternate=None, diff_expected=None
    ):
        diff_expected = (
            diff_expected
            if diff_expected is not None
            else alternate is not None
        )
        if alternate is None:
            alternate = orig_default

        t1 = Table(
            "test",
            self.metadata,
            Column("somecol", type_, server_default=orig_default),
        )
        t2 = Table(
            "test",
            MetaData(),
            Column("somecol", type_, server_default=alternate),
        )

        t1.create(self.bind)

        insp = inspect(self.bind)
        cols = insp.get_columns(t1.name)
        insp_col = Column(
            "somecol", cols[0]["type"], server_default=text(cols[0]["default"])
        )
        op = ops.AlterColumnOp("test", "somecol")
        _compare_server_default(
            self.autogen_context,
            op,
            None,
            "test",
            "somecol",
            insp_col,
            t2.c.somecol,
        )

        diffs = op.to_diff_tuple()
        eq_(bool(diffs), diff_expected)

    def _compare_default(self, t1, t2, col, rendered):
        t1.create(self.bind, checkfirst=True)
        insp = inspect(self.bind)
        cols = insp.get_columns(t1.name)
        ctx = self.autogen_context.migration_context

        return ctx.impl.compare_server_default(
            None, col, rendered, cols[0]["default"]
        )

    def test_compare_string_blank_default(self):
        self._compare_default_roundtrip(String(8), "")

    def test_compare_string_nonblank_default(self):
        self._compare_default_roundtrip(String(8), "hi")

    def test_compare_interval_str(self):
        # this form shouldn't be used but testing here
        # for compatibility
        self._compare_default_roundtrip(Interval, "14 days")

    @config.requirements.postgresql_uuid_ossp
    def test_compare_uuid_text(self):
        self._compare_default_roundtrip(UUID, text("uuid_generate_v4()"))

    def test_compare_interval_text(self):
        self._compare_default_roundtrip(Interval, text("'14 days'"))

    def test_compare_array_of_integer_text(self):
        self._compare_default_roundtrip(
            ARRAY(Integer), text("(ARRAY[]::integer[])")
        )

    def test_compare_current_timestamp_text(self):
        self._compare_default_roundtrip(
            DateTime(), text("TIMEZONE('utc', CURRENT_TIMESTAMP)")
        )

    def test_compare_current_timestamp_fn_w_binds(self):
        self._compare_default_roundtrip(
            DateTime(), func.timezone("utc", func.current_timestamp())
        )

    def test_compare_integer_str(self):
        self._compare_default_roundtrip(Integer(), "5")

    def test_compare_integer_text(self):
        self._compare_default_roundtrip(Integer(), text("5"))

    def test_compare_integer_text_diff(self):
        self._compare_default_roundtrip(Integer(), text("5"), "7")

    def test_compare_float_str(self):
        self._compare_default_roundtrip(Float(), "5.2")

    def test_compare_float_text(self):
        self._compare_default_roundtrip(Float(), text("5.2"))

    def test_compare_float_no_diff1(self):
        self._compare_default_roundtrip(
            Float(), text("5.2"), "5.2", diff_expected=False
        )

    def test_compare_float_no_diff2(self):
        self._compare_default_roundtrip(
            Float(), "5.2", text("5.2"), diff_expected=False
        )

    def test_compare_float_no_diff3(self):
        self._compare_default_roundtrip(
            Float(), text("5"), text("5.0"), diff_expected=False
        )

    def test_compare_float_no_diff4(self):
        self._compare_default_roundtrip(
            Float(), "5", "5.0", diff_expected=False
        )

    def test_compare_float_no_diff5(self):
        self._compare_default_roundtrip(
            Float(), text("5"), "5.0", diff_expected=False
        )

    def test_compare_float_no_diff6(self):
        self._compare_default_roundtrip(
            Float(), "5", text("5.0"), diff_expected=False
        )

    def test_compare_numeric_no_diff(self):
        self._compare_default_roundtrip(
            Numeric(), text("5"), "5.0", diff_expected=False
        )

    def test_compare_unicode_literal(self):
        self._compare_default_roundtrip(String(), "im a default")

    # TODO: will need to actually eval() the repr() and
    # spend more effort figuring out exactly the kind of expression
    # to use
    def _TODO_test_compare_character_str_w_singlequote(self):
        self._compare_default_roundtrip(String(), "hel''lo")

    def test_compare_character_str(self):
        self._compare_default_roundtrip(String(), "hello")

    def test_compare_character_text(self):
        self._compare_default_roundtrip(String(), text("'hello'"))

    def test_compare_character_str_diff(self):
        self._compare_default_roundtrip(String(), "hello", "there")

    def test_compare_character_text_diff(self):
        self._compare_default_roundtrip(
            String(), text("'hello'"), text("'there'")
        )

    def test_primary_key_skip(self):
        """Test that SERIAL cols are just skipped"""
        t1 = Table(
            "sometable", self.metadata, Column("id", Integer, primary_key=True)
        )
        t2 = Table(
            "sometable", MetaData(), Column("id", Integer, primary_key=True)
        )
        assert not self._compare_default(t1, t2, t2.c.id, "")


class PostgresqlDetectSerialTest(TestBase):
    __only_on__ = "postgresql"
    __backend__ = True

    @classmethod
    def setup_class(cls):
        cls.bind = config.db
        staging_env()

    def setUp(self):
        self.conn = self.bind.connect()
        self.migration_context = MigrationContext.configure(
            connection=self.conn,
            opts={"compare_type": True, "compare_server_default": True},
        )
        self.autogen_context = api.AutogenContext(self.migration_context)

    def tearDown(self):
        self.conn.close()

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    @provide_metadata
    def _expect_default(self, c_expected, col, schema=None, seq=None):
        Table("t", self.metadata, col, schema=schema)

        self.autogen_context.metadata = self.metadata

        if seq:
            seq._set_metadata(self.metadata)
        self.metadata.create_all(config.db)

        insp = inspect(config.db)

        uo = ops.UpgradeOps(ops=[])
        _compare_tables({(schema, "t")}, set(), insp, uo, self.autogen_context)
        diffs = uo.as_diffs()
        tab = diffs[0][1]

        eq_(
            _render_server_default_for_compare(
                tab.c.x.server_default, self.autogen_context
            ),
            c_expected,
        )

        insp = inspect(config.db)
        uo = ops.UpgradeOps(ops=[])
        m2 = MetaData(schema=schema)
        Table("t", m2, Column("x", BigInteger()))
        self.autogen_context.metadata = m2
        _compare_tables(
            {(schema, "t")},
            {(schema, "t")},
            insp,
            uo,
            self.autogen_context,
        )
        diffs = uo.as_diffs()
        server_default = diffs[0][0][4]["existing_server_default"]
        eq_(
            _render_server_default_for_compare(
                server_default, self.autogen_context
            ),
            c_expected,
        )

    @testing.combinations((None,), ("test_schema",))
    def test_serial(self, schema):
        self._expect_default(
            None, Column("x", Integer, primary_key=True), schema
        )

    @testing.combinations((None,), ("test_schema",))
    def test_separate_seq(self, schema):
        seq = Sequence("x_id_seq", schema=schema)
        seq_name = seq.name if schema is None else f"{schema}.{seq.name}"
        self._expect_default(
            f"nextval('{seq_name}'::regclass)",
            Column(
                "x", Integer, server_default=seq.next_value(), primary_key=True
            ),
            schema,
            seq,
        )

    @testing.combinations((None,), ("test_schema",))
    def test_numeric(self, schema):
        seq = Sequence("x_id_seq", schema=schema)
        seq_name = seq.name if schema is None else f"{schema}.{seq.name}"
        self._expect_default(
            f"nextval('{seq_name}'::regclass)",
            Column(
                "x",
                Numeric(8, 2),
                server_default=seq.next_value(),
                primary_key=True,
            ),
            schema,
            seq,
        )

    @testing.combinations((None,), ("test_schema",))
    def test_no_default(self, schema):
        self._expect_default(
            None,
            Column("x", Integer, autoincrement=False, primary_key=True),
            schema,
        )


class PostgresqlAutogenRenderTest(TestBase):
    def setUp(self):
        ctx_opts = {
            "sqlalchemy_module_prefix": "sa.",
            "alembic_module_prefix": "op.",
            "target_metadata": MetaData(),
        }
        context = MigrationContext.configure(
            dialect_name="postgresql", opts=ctx_opts
        )

        self.autogen_context = api.AutogenContext(context)

    def test_render_add_index_pg_where(self):
        autogen_context = self.autogen_context

        m = MetaData()
        t = Table("t", m, Column("x", String), Column("y", String))

        idx = Index(
            "foo_idx", t.c.x, t.c.y, postgresql_where=(t.c.y == "something")
        )

        op_obj = ops.CreateIndexOp.from_index(idx)

        eq_ignore_whitespace(
            autogenerate.render_op_text(autogen_context, op_obj),
            """op.create_index('foo_idx', 't', \
['x', 'y'], unique=False, """
            """postgresql_where=sa.text("y = 'something'"))""",
        )

    def test_render_server_default_native_boolean(self):
        c = Column(
            "updated_at", Boolean(), server_default=false(), nullable=False
        )
        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_ignore_whitespace(
            result,
            "sa.Column('updated_at', sa.Boolean(), "
            "server_default=sa.text('false'), "
            "nullable=False)",
        )

    def test_postgresql_array_type(self):
        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                ARRAY(Integer), self.autogen_context
            ),
            "postgresql.ARRAY(sa.Integer())",
        )

        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                ARRAY(DateTime(timezone=True)), self.autogen_context
            ),
            "postgresql.ARRAY(sa.DateTime(timezone=True))",
        )

        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                ARRAY(BYTEA, as_tuple=True, dimensions=2), self.autogen_context
            ),
            "postgresql.ARRAY(postgresql.BYTEA(), "
            "as_tuple=True, dimensions=2)",
        )

        assert (
            "from sqlalchemy.dialects import postgresql"
            in self.autogen_context.imports
        )

    def test_postgresql_hstore_subtypes(self):
        eq_ignore_whitespace(
            autogenerate.render._repr_type(HSTORE(), self.autogen_context),
            "postgresql.HSTORE(text_type=sa.Text())",
        )

        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                HSTORE(text_type=String()), self.autogen_context
            ),
            "postgresql.HSTORE(text_type=sa.String())",
        )

        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                HSTORE(text_type=BYTEA()), self.autogen_context
            ),
            "postgresql.HSTORE(text_type=postgresql.BYTEA())",
        )

        assert (
            "from sqlalchemy.dialects import postgresql"
            in self.autogen_context.imports
        )

    def test_generic_array_type(self):
        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                types.ARRAY(Integer), self.autogen_context
            ),
            "sa.ARRAY(sa.Integer())",
        )

        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                types.ARRAY(DateTime(timezone=True)), self.autogen_context
            ),
            "sa.ARRAY(sa.DateTime(timezone=True))",
        )

        assert (
            "from sqlalchemy.dialects import postgresql"
            not in self.autogen_context.imports
        )

        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                types.ARRAY(BYTEA, as_tuple=True, dimensions=2),
                self.autogen_context,
            ),
            "sa.ARRAY(postgresql.BYTEA(), as_tuple=True, dimensions=2)",
        )

        assert (
            "from sqlalchemy.dialects import postgresql"
            in self.autogen_context.imports
        )

    def test_array_type_user_defined_inner(self):
        def repr_type(typestring, object_, autogen_context):
            if typestring == "type" and isinstance(object_, String):
                return "foobar.MYVARCHAR"
            else:
                return False

        self.autogen_context.opts.update(render_item=repr_type)

        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                ARRAY(String), self.autogen_context
            ),
            "postgresql.ARRAY(foobar.MYVARCHAR)",
        )

    def test_add_exclude_constraint(self):
        autogen_context = self.autogen_context

        m = MetaData()
        t = Table("t", m, Column("x", String), Column("y", String))

        op_obj = ops.AddConstraintOp.from_constraint(
            ExcludeConstraint(
                (t.c.x, ">"), where=t.c.x != 2, using="gist", name="t_excl_x"
            )
        )

        eq_ignore_whitespace(
            autogenerate.render_op_text(autogen_context, op_obj),
            "op.create_exclude_constraint('t_excl_x', "
            "'t', (sa.column('x'), '>'), "
            "where=sa.text('x != 2'), using='gist')",
        )

    def test_add_exclude_constraint_case_sensitive(self):
        autogen_context = self.autogen_context

        m = MetaData()
        t = Table(
            "TTAble", m, Column("XColumn", String), Column("YColumn", String)
        )

        op_obj = ops.AddConstraintOp.from_constraint(
            ExcludeConstraint(
                (t.c.XColumn, ">"),
                where=t.c.XColumn != 2,
                using="gist",
                name="t_excl_x",
            )
        )

        eq_ignore_whitespace(
            autogenerate.render_op_text(autogen_context, op_obj),
            "op.create_exclude_constraint('t_excl_x', 'TTAble', "
            "(sa.column('XColumn'), '>'), "
            "where=sa.text('\"XColumn\" != 2'), using='gist')",
        )

    def test_inline_exclude_constraint(self):
        autogen_context = self.autogen_context

        m = MetaData()
        t = Table(
            "t",
            m,
            Column("x", String),
            Column("y", String),
            ExcludeConstraint(
                (column("x"), ">"),
                using="gist",
                where="x != 2",
                name="t_excl_x",
            ),
        )

        op_obj = ops.CreateTableOp.from_table(t)

        eq_ignore_whitespace(
            autogenerate.render_op_text(autogen_context, op_obj),
            "op.create_table('t',sa.Column('x', sa.String(), nullable=True),"
            "sa.Column('y', sa.String(), nullable=True),"
            "postgresql.ExcludeConstraint((sa.column('x'), '>'), "
            "where=sa.text('x != 2'), using='gist', name='t_excl_x')"
            ")",
        )

    def test_inline_exclude_constraint_case_sensitive(self):
        autogen_context = self.autogen_context

        m = MetaData()
        t = Table(
            "TTable", m, Column("XColumn", String), Column("YColumn", String)
        )
        ExcludeConstraint(
            (t.c.XColumn, ">"),
            using="gist",
            where='"XColumn" != 2',
            name="TExclX",
        )

        op_obj = ops.CreateTableOp.from_table(t)

        eq_ignore_whitespace(
            autogenerate.render_op_text(autogen_context, op_obj),
            "op.create_table('TTable',sa.Column('XColumn', sa.String(), "
            "nullable=True),"
            "sa.Column('YColumn', sa.String(), nullable=True),"
            "postgresql.ExcludeConstraint((sa.column('XColumn'), '>'), "
            "where=sa.text('\"XColumn\" != 2'), using='gist', "
            "name='TExclX'))",
        )

    def test_inline_exclude_constraint_literal_column(self):
        """test for #1184"""

        autogen_context = self.autogen_context

        m = MetaData()
        t = Table(
            "TTable",
            m,
            Column("id", String()),
            ExcludeConstraint(
                (literal_column("id + 2"), "="), name="TExclID", using="gist"
            ),
        )

        op_obj = ops.CreateTableOp.from_table(t)

        eq_ignore_whitespace(
            autogenerate.render_op_text(autogen_context, op_obj),
            "op.create_table('TTable',sa.Column('id', sa.String(), "
            "nullable=True),"
            "postgresql.ExcludeConstraint((sa.literal_column('id + 2'), '='), "
            "using='gist', "
            "name='TExclID'))",
        )

    @config.requirements.sqlalchemy_2
    def test_inline_exclude_constraint_fn(self):
        """test for #1230"""

        autogen_context = self.autogen_context

        effective_time = Column("effective_time", DateTime(timezone=True))
        expiry_time = Column("expiry_time", DateTime(timezone=True))

        m = MetaData()
        t = Table(
            "TTable",
            m,
            effective_time,
            expiry_time,
            ExcludeConstraint(
                (func.tstzrange(effective_time, expiry_time), "&&"),
                using="gist",
            ),
        )

        op_obj = ops.CreateTableOp.from_table(t)

        eq_ignore_whitespace(
            autogenerate.render_op_text(autogen_context, op_obj),
            "op.create_table('TTable',sa.Column('effective_time', "
            "sa.DateTime(timezone=True), nullable=True),"
            "sa.Column('expiry_time', sa.DateTime(timezone=True), "
            "nullable=True),postgresql.ExcludeConstraint("
            "(sa.text('tstzrange(effective_time, expiry_time)'), "
            "'&&'), using='gist'))",
        )

    @config.requirements.sqlalchemy_2
    def test_inline_exclude_constraint_text(self):
        """test for #1184.

        Requires SQLAlchemy 2.0.5 due to issue
        https://github.com/sqlalchemy/sqlalchemy/issues/9401

        """

        autogen_context = self.autogen_context

        m = MetaData()
        t = Table(
            "TTable",
            m,
            Column("id", String()),
            ExcludeConstraint(
                (text("id + 2"), "="), name="TExclID", using="gist"
            ),
        )

        op_obj = ops.CreateTableOp.from_table(t)

        eq_ignore_whitespace(
            autogenerate.render_op_text(autogen_context, op_obj),
            "op.create_table('TTable',sa.Column('id', sa.String(), "
            "nullable=True),"
            "postgresql.ExcludeConstraint((sa.text('id + 2'), '='), "
            "using='gist', "
            "name='TExclID'))",
        )

    def test_drop_exclude_constraint(self):
        """test for #1300"""

        autogen_context = self.autogen_context

        m = MetaData()
        t = Table(
            "TTable", m, Column("XColumn", String), Column("YColumn", String)
        )

        op_obj = ops.DropConstraintOp.from_constraint(
            ExcludeConstraint(
                (t.c.XColumn, ">"),
                where=t.c.XColumn != 2,
                using="gist",
                name="t_excl_x",
            )
        )

        eq_ignore_whitespace(
            autogenerate.render_op_text(autogen_context, op_obj),
            "op.drop_constraint('t_excl_x', 'TTable')",
        )

    def test_json_type(self):
        eq_ignore_whitespace(
            autogenerate.render._repr_type(JSON(), self.autogen_context),
            "postgresql.JSON(astext_type=sa.Text())",
        )

    def test_jsonb_type(self):
        eq_ignore_whitespace(
            autogenerate.render._repr_type(JSONB(), self.autogen_context),
            "postgresql.JSONB(astext_type=sa.Text())",
        )

    def test_jsonb_expression_in_index(self):
        """test #1322"""

        m = MetaData()
        t = Table("tbl", m, Column("c", JSONB()))
        idx = Index("my_idx", t.c.c["foo"].astext)

        eq_ignore_whitespace(
            autogenerate.render.render_op_text(
                self.autogen_context,
                ops.CreateIndexOp.from_index(idx),
            ),
            "op.create_index('my_idx', 'tbl', "
            "[sa.literal_column(\"(c ->> 'foo')\")], unique=False)",
        )

    @config.requirements.nulls_not_distinct_sa
    def test_render_unique_nulls_not_distinct_constraint(self):
        m = MetaData()
        t = Table("tbl", m, Column("c", Integer))
        uc = UniqueConstraint(
            t.c.c,
            name="uq_1",
            deferrable="XYZ",
            postgresql_nulls_not_distinct=True,
        )
        eq_ignore_whitespace(
            autogenerate.render.render_op_text(
                self.autogen_context,
                ops.AddConstraintOp.from_constraint(uc),
            ),
            "op.create_unique_constraint('uq_1', 'tbl', ['c'], "
            "deferrable='XYZ', postgresql_nulls_not_distinct=True)",
        )
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(
                uc, self.autogen_context, None
            ),
            "sa.UniqueConstraint('c', deferrable='XYZ', name='uq_1', "
            "postgresql_nulls_not_distinct=True)",
        )

    @config.requirements.nulls_not_distinct_sa
    def test_render_index_nulls_not_distinct_constraint(self):
        m = MetaData()
        t = Table("tbl", m, Column("c", Integer))
        idx = Index("ix_42", t.c.c, postgresql_nulls_not_distinct=False)
        eq_ignore_whitespace(
            autogenerate.render.render_op_text(
                self.autogen_context, ops.CreateIndexOp.from_index(idx)
            ),
            "op.create_index('ix_42', 'tbl', ['c'], unique=False, "
            "postgresql_nulls_not_distinct=False)",
        )


class PGUniqueIndexAutogenerateTest(AutogenFixtureTest, TestBase):
    __only_on__ = "postgresql"
    __backend__ = True

    def test_idx_added_schema(self):
        m1 = MetaData()
        m2 = MetaData()
        Table("add_ix", m1, Column("x", String(50)), schema="test_schema")
        Table(
            "add_ix",
            m2,
            Column("x", String(50)),
            Index("ix_1", "x"),
            schema="test_schema",
        )

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs[0][0], "add_index")
        eq_(diffs[0][1].name, "ix_1")

    def test_idx_unchanged_schema(self):
        m1 = MetaData()
        m2 = MetaData()
        Table(
            "add_ix",
            m1,
            Column("x", String(50)),
            Index("ix_1", "x"),
            schema="test_schema",
        )
        Table(
            "add_ix",
            m2,
            Column("x", String(50)),
            Index("ix_1", "x"),
            schema="test_schema",
        )

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs, [])

    def test_uq_added_schema(self):
        m1 = MetaData()
        m2 = MetaData()
        Table("add_uq", m1, Column("x", String(50)), schema="test_schema")
        Table(
            "add_uq",
            m2,
            Column("x", String(50)),
            UniqueConstraint("x", name="ix_1"),
            schema="test_schema",
        )

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "ix_1")

    def test_uq_unchanged_schema(self):
        m1 = MetaData()
        m2 = MetaData()
        Table(
            "add_uq",
            m1,
            Column("x", String(50)),
            UniqueConstraint("x", name="ix_1"),
            schema="test_schema",
        )
        Table(
            "add_uq",
            m2,
            Column("x", String(50)),
            UniqueConstraint("x", name="ix_1"),
            schema="test_schema",
        )

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs, [])

    @config.requirements.btree_gist
    def test_exclude_const_unchanged(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "add_excl",
            m1,
            Column("id", Integer, primary_key=True),
            Column("period", TSRANGE),
            ExcludeConstraint(("period", "&&"), name="quarters_period_excl"),
        )

        Table(
            "add_excl",
            m2,
            Column("id", Integer, primary_key=True),
            Column("period", TSRANGE),
            ExcludeConstraint(("period", "&&"), name="quarters_period_excl"),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_same_tname_two_schemas(self):
        m1 = MetaData()
        m2 = MetaData()

        Table("add_ix", m1, Column("x", String(50)), Index("ix_1", "x"))

        Table("add_ix", m2, Column("x", String(50)), Index("ix_1", "x"))
        Table("add_ix", m2, Column("x", String(50)), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 1)

    def test_uq_dropped(self):
        m1 = MetaData()
        m2 = MetaData()
        Table(
            "add_uq",
            m1,
            Column("id", Integer, primary_key=True),
            Column("name", String),
            UniqueConstraint("name", name="uq_name"),
        )
        Table(
            "add_uq",
            m2,
            Column("id", Integer, primary_key=True),
            Column("name", String),
        )
        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs[0][0], "remove_constraint")
        eq_(diffs[0][1].name, "uq_name")
        eq_(len(diffs), 1)


def _lots_of_indexes(flatten: bool = False):
    diff_pairs = [
        (
            lambda t: Index("idx", t.c.jb["foo"]),
            lambda t: Index("idx", t.c.jb["bar"]),
        ),
        (
            lambda t: Index("idx", t.c.jb["foo"]),
            lambda t: Index("idx", t.c.jb["not_jsonb_path_ops"]),
        ),
        (
            lambda t: Index("idx", t.c.jb["not_jsonb_path_ops"]),
            lambda t: Index("idx", t.c.jb["bar"]),
        ),
        (
            lambda t: Index("idx", t.c.aa),
            lambda t: Index("idx", t.c.not_jsonb_path_ops),
        ),
        (
            lambda t: Index("idx", t.c.not_jsonb_path_ops),
            lambda t: Index("idx", t.c.aa),
        ),
        (
            lambda t: Index(
                "idx",
                t.c.jb["foo"].label("x"),
                postgresql_using="gin",
                postgresql_ops={"x": "jsonb_path_ops"},
            ),
            lambda t: Index(
                "idx",
                t.c.jb["bar"].label("x"),
                postgresql_using="gin",
                postgresql_ops={"x": "jsonb_path_ops"},
            ),
        ),
        (
            lambda t: Index("idx", t.c.jb["foo"].astext),
            lambda t: Index("idx", t.c.jb["bar"].astext),
        ),
        (
            lambda t: Index("idx", t.c.jb["foo"].as_integer()),
            lambda t: Index("idx", t.c.jb["bar"].as_integer()),
        ),
        (
            lambda t: Index("idx", text("(jb->'x')"), _table=t),
            lambda t: Index("idx", text("(jb->'y')"), _table=t),
        ),
    ]
    if flatten:
        return list(itertools.chain.from_iterable(diff_pairs))
    else:
        return diff_pairs


def _equal_indexes():
    the_indexes = [(fn, fn) for fn in _lots_of_indexes(True)]
    the_indexes += [
        (
            lambda t: Index("idx", text("(jb->'x')"), _table=t),
            lambda t: Index("idx", text("(jb -> 'x')"), _table=t),
        ),
        (
            lambda t: Index("idx", text("cast(jb->'x' as integer)"), _table=t),
            lambda t: Index("idx", text("(jb -> 'x')::integer"), _table=t),
        ),
    ]
    return the_indexes


def _index_op_clause():
    def make_idx(t, *expr):
        return Index(
            "idx",
            *(text(e) if isinstance(e, str) else e for e in expr),
            postgresql_using="gin",
            _table=t,
        )

    return [
        (
            False,
            lambda t: make_idx(t, "(jb->'x')jsonb_path_ops"),
            lambda t: make_idx(t, "(jb->'x')jsonb_path_ops"),
        ),
        (
            False,
            lambda t: make_idx(t, "aa array_ops"),
            lambda t: make_idx(t, "aa array_ops"),
        ),
        (
            False,
            lambda t: make_idx(t, "(jb->'x')jsonb_path_ops"),
            lambda t: make_idx(t, "(jb->'y')jsonb_path_ops"),
        ),
        (
            False,
            lambda t: make_idx(t, "aa array_ops"),
            lambda t: make_idx(t, "jb array_ops"),
        ),
        (
            False,
            lambda t: make_idx(t, "aa array_ops", "(jb->'y')jsonb_path_ops"),
            lambda t: make_idx(t, "(jb->'y')jsonb_path_ops", "aa array_ops"),
        ),
        (
            True,
            lambda t: make_idx(t, "aa array_ops", text("(jb->'x')")),
            lambda t: make_idx(t, "aa array_ops", text("(jb->'y')")),
        ),
        (
            True,
            lambda t: make_idx(t, text("(jb->'x')"), "aa array_ops"),
            lambda t: make_idx(t, text("(jb->'y')"), "aa array_ops"),
        ),
        (
            True,
            lambda t: make_idx(t, "aa array_ops", text("(jb->'x')")),
            lambda t: make_idx(t, "jb array_ops", text("(jb->'y')")),
        ),
        (
            True,
            lambda t: make_idx(t, text("(jb->'x')"), "aa array_ops"),
            lambda t: make_idx(t, text("(jb->'y')"), "jb array_ops"),
        ),
    ]


class PGIndexAutogenerateTest(AutogenFixtureTest, TestBase):
    __backend__ = True
    __only_on__ = "postgresql"
    __requires__ = ("reflect_indexes_with_expressions",)

    @testing.fixture
    def index_tables(self):
        m1 = MetaData()
        m2 = MetaData()

        t_old = Table(
            "exp_index",
            m1,
            Column("id", Integer, primary_key=True),
            Column("aa", ARRAY(Integer)),
            Column("jb", JSONB),
            Column("not_jsonb_path_ops", Integer),
        )

        t_new = Table(
            "exp_index",
            m2,
            Column("id", Integer, primary_key=True),
            Column("aa", ARRAY(Integer)),
            Column("jb", JSONB),
            Column("not_jsonb_path_ops", Integer),
        )

        return m1, m2, t_old, t_new

    @combinations(*_lots_of_indexes(), argnames="old_fn, new_fn")
    def test_expression_indexes_changed(self, index_tables, old_fn, new_fn):
        m1, m2, old_table, new_table = index_tables

        old = resolve_lambda(old_fn, t=old_table)
        new = resolve_lambda(new_fn, t=new_table)

        diffs = self._fixture(m1, m2)
        eq_(
            diffs,
            [
                ("remove_index", schemacompare.CompareIndex(old, True)),
                ("add_index", schemacompare.CompareIndex(new)),
            ],
        )

    @combinations(*_equal_indexes(), argnames="fn1, fn2")
    def test_expression_indexes_no_change(self, index_tables, fn1, fn2):
        m1, m2, old_table, new_table = index_tables

        resolve_lambda(fn1, t=old_table)
        resolve_lambda(fn2, t=new_table)

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    @combinations(*_index_op_clause(), argnames="changed, old_fn, new_fn")
    def test_expression_indexes_warn_operator(
        self, index_tables, changed, old_fn, new_fn
    ):
        m1, m2, old_table, new_table = index_tables

        old = old_fn(t=old_table)
        new = new_fn(t=new_table)

        with expect_warnings(
            r"Expression #\d .+ in index 'idx' detected to include "
            "an operator clause. Expression compare cannot proceed. "
            "Please move the operator clause to the "
        ):
            diffs = self._fixture(m1, m2)
        if changed:
            eq_(
                diffs,
                [
                    ("remove_index", schemacompare.CompareIndex(old, True)),
                    ("add_index", schemacompare.CompareIndex(new)),
                ],
            )
        else:
            eq_(diffs, [])


case = combinations(
    ("nulls_not_distinct=False", False),
    ("nulls_not_distinct=True", True),
    ("nulls_not_distinct=None", None),
    argnames="case",
    id_="ia",
)
name_type = combinations(
    (
        "index",
        lambda value: Index(
            "nnd_obj", "name", unique=True, postgresql_nulls_not_distinct=value
        ),
    ),
    (
        "constraint",
        lambda value: UniqueConstraint(
            "id", "name", name="nnd_obj", postgresql_nulls_not_distinct=value
        ),
    ),
    argnames="name,type_",
    id_="sa",
)


class PGNullsNotDistinctAutogenerateTest(AutogenFixtureTest, TestBase):
    __requires__ = ("nulls_not_distinct_db",)
    __only_on__ = "postgresql"
    __backend__ = True

    @case
    @name_type
    def test_add(self, case, name, type_):
        m1 = MetaData()
        m2 = MetaData()
        Table(
            "tbl",
            m1,
            Column("id", Integer, primary_key=True),
            Column("name", String),
        )
        Table(
            "tbl",
            m2,
            Column("id", Integer, primary_key=True),
            Column("name", String),
            type_(case),
        )
        diffs = self._fixture(m1, m2)
        eq_(len(diffs), 1)
        eq_(diffs[0][0], f"add_{name}")
        added = diffs[0][1]
        eq_(added.name, "nnd_obj")
        eq_(added.dialect_kwargs["postgresql_nulls_not_distinct"], case)

    @case
    @name_type
    def test_remove(self, case, name, type_):
        m1 = MetaData()
        m2 = MetaData()
        Table(
            "tbl",
            m1,
            Column("id", Integer, primary_key=True),
            Column("name", String),
            type_(case),
        )
        Table(
            "tbl",
            m2,
            Column("id", Integer, primary_key=True),
            Column("name", String),
        )
        diffs = self._fixture(m1, m2)
        eq_(len(diffs), 1)
        eq_(diffs[0][0], f"remove_{name}")
        eq_(diffs[0][1].name, "nnd_obj")

    @case
    @name_type
    def test_toggle_not_distinct(self, case, name, type_):
        m1 = MetaData()
        m2 = MetaData()
        to = not case
        Table(
            "tbl",
            m1,
            Column("id", Integer, primary_key=True),
            Column("name", String),
            type_(case),
        )
        Table(
            "tbl",
            m2,
            Column("id", Integer, primary_key=True),
            Column("name", String),
            type_(to),
        )
        diffs = self._fixture(m1, m2)
        eq_(len(diffs), 2)
        eq_(diffs[0][0], f"remove_{name}")
        eq_(diffs[1][0], f"add_{name}")
        eq_(diffs[1][1].name, "nnd_obj")
        eq_(diffs[1][1].dialect_kwargs["postgresql_nulls_not_distinct"], to)

    @case
    @name_type
    def test_no_change(self, case, name, type_):
        m1 = MetaData()
        m2 = MetaData()
        Table(
            "tbl",
            m1,
            Column("id", Integer, primary_key=True),
            Column("name", String),
            type_(case),
        )
        Table(
            "tbl",
            m2,
            Column("id", Integer, primary_key=True),
            Column("name", String),
            type_(case),
        )
        diffs = self._fixture(m1, m2)
        eq_(len(diffs), 0, str(diffs))
