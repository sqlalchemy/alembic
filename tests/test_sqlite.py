from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import func
from sqlalchemy import inspect
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import text
from sqlalchemy.sql import column

from alembic import autogenerate
from alembic import op
from alembic.autogenerate import api
from alembic.autogenerate.compare import _compare_server_default
from alembic.migration import MigrationContext
from alembic.operations import ops
from alembic.testing import assert_raises_message
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import eq_ignore_whitespace
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.fixtures import op_fixture
from alembic.testing.fixtures import TestBase


class SQLiteTest(TestBase):
    def test_add_column(self):
        context = op_fixture("sqlite")
        op.add_column("t1", Column("c1", Integer))
        context.assert_("ALTER TABLE t1 ADD COLUMN c1 INTEGER")

    def test_add_column_implicit_constraint(self):
        context = op_fixture("sqlite")
        op.add_column("t1", Column("c1", Boolean))
        context.assert_("ALTER TABLE t1 ADD COLUMN c1 BOOLEAN")

    def test_add_explicit_constraint(self):
        op_fixture("sqlite")
        assert_raises_message(
            NotImplementedError,
            "No support for ALTER of constraints in SQLite dialect",
            op.create_check_constraint,
            "foo",
            "sometable",
            column("name") > 5,
        )

    def test_drop_explicit_constraint(self):
        op_fixture("sqlite")
        assert_raises_message(
            NotImplementedError,
            "No support for ALTER of constraints in SQLite dialect",
            op.drop_constraint,
            "foo",
            "sometable",
        )

    @config.requirements.comments
    def test_create_table_with_comment_ignored(self):

        context = op_fixture("sqlite")
        op.create_table(
            "t2",
            Column("c1", Integer, primary_key=True),
            Column("c2", Integer),
            comment="This is a table comment",
        )
        context.assert_(
            "CREATE TABLE t2 (c1 INTEGER NOT NULL, "
            "c2 INTEGER, PRIMARY KEY (c1))"
        )

    @config.requirements.comments
    def test_add_column_with_comment_ignored(self):

        context = op_fixture("sqlite")
        op.add_column("t1", Column("c1", Integer, comment="c1 comment"))
        context.assert_("ALTER TABLE t1 ADD COLUMN c1 INTEGER")

    def test_rename_table_w_schema(self):
        context = op_fixture("sqlite")
        op.rename_table("old_name", "new_name", schema="my_schema")
        context.assert_("ALTER TABLE my_schema.old_name RENAME TO new_name")


class SQLiteDefaultCompareTest(TestBase):
    __only_on__ = "sqlite"
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
        self.metadata.drop_all(config.db)

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

    def test_compare_current_timestamp_func(self):
        self._compare_default_roundtrip(
            DateTime(), func.datetime("now", "localtime")
        )

    def test_compare_current_timestamp_func_now(self):
        self._compare_default_roundtrip(DateTime(), func.now())

    def test_compare_current_timestamp_text(self):
        # SQLAlchemy doesn't render the parenthesis for a
        # SQLite server default specified as text(), so users will be doing
        # this; sqlite comparison needs to accommodate for these.
        self._compare_default_roundtrip(
            DateTime(), text("(datetime('now', 'localtime'))")
        )

    def test_compare_integer_str(self):
        self._compare_default_roundtrip(Integer(), "5")

    def test_compare_integer_str_diff(self):
        self._compare_default_roundtrip(Integer(), "5", "7")

    def test_compare_integer_text(self):
        self._compare_default_roundtrip(Integer(), text("5"))

    def test_compare_integer_text_diff(self):
        self._compare_default_roundtrip(Integer(), text("5"), "7")

    def test_compare_float_str(self):
        self._compare_default_roundtrip(Float(), "5.2")

    def test_compare_float_str_diff(self):
        self._compare_default_roundtrip(Float(), "5.2", "5.3")

    def test_compare_float_text(self):
        self._compare_default_roundtrip(Float(), text("5.2"))

    def test_compare_float_text_diff(self):
        self._compare_default_roundtrip(Float(), text("5.2"), "5.3")

    def test_compare_string_literal(self):
        self._compare_default_roundtrip(String(), "im a default")

    def test_compare_string_literal_diff(self):
        self._compare_default_roundtrip(String(), "im a default", "me too")


class SQLiteAutogenRenderTest(TestBase):
    def setUp(self):
        ctx_opts = {
            "sqlalchemy_module_prefix": "sa.",
            "alembic_module_prefix": "op.",
            "target_metadata": MetaData(),
        }
        context = MigrationContext.configure(
            dialect_name="sqlite", opts=ctx_opts
        )

        self.autogen_context = api.AutogenContext(context)

    def test_render_server_default_expr_needs_parens(self):
        c = Column(
            "date_value",
            DateTime(),
            server_default=func.datetime("now", "localtime"),
        )

        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_ignore_whitespace(
            result,
            "sa.Column('date_value', sa.DateTime(), "
            "server_default=sa.text(\"(datetime('now', 'localtime'))\"), "
            "nullable=True)",
        )

    def test_render_server_default_text_expr_needs_parens(self):
        c = Column(
            "date_value",
            DateTime(),
            server_default=text("(datetime('now', 'localtime'))"),
        )

        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_ignore_whitespace(
            result,
            "sa.Column('date_value', sa.DateTime(), "
            "server_default=sa.text(\"(datetime('now', 'localtime'))\"), "
            "nullable=True)",
        )

    def test_render_server_default_const(self):
        c = Column("int_value", Integer, server_default="5")

        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_ignore_whitespace(
            result,
            "sa.Column('int_value', sa.Integer(), server_default='5', "
            "nullable=True)",
        )

    @config.requirements.sqlalchemy_13
    def test_render_add_column_w_on_conflict(self):
        c = Column("int_value", Integer, sqlite_on_conflict_not_null="FAIL")

        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_ignore_whitespace(
            result,
            "sa.Column('int_value', sa.Integer(), "
            "nullable=True, sqlite_on_conflict_not_null='FAIL')",
        )
