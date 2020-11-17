from sqlalchemy import Column
from sqlalchemy import exc
from sqlalchemy import Integer

from alembic import command
from alembic import op
from alembic.testing import assert_raises_message
from alembic.testing import combinations
from alembic.testing import config
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
        cls.cfg = cfg = _no_sql_testing_config("oracle")

        cls.a, cls.b, cls.c = three_rev_fixture(cfg)

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


class OpTest(TestBase):
    def test_add_column(self):
        context = op_fixture("oracle")
        op.add_column("t1", Column("c1", Integer, nullable=False))
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL")

    def test_add_column_with_default(self):
        context = op_fixture("oracle")
        op.add_column(
            "t1", Column("c1", Integer, nullable=False, server_default="12")
        )
        context.assert_("ALTER TABLE t1 ADD c1 INTEGER DEFAULT '12' NOT NULL")

    @config.requirements.comments
    def test_add_column_with_comment(self):
        context = op_fixture("oracle")
        op.add_column(
            "t1", Column("c1", Integer, nullable=False, comment="c1 comment")
        )
        context.assert_(
            "ALTER TABLE t1 ADD c1 INTEGER NOT NULL",
            "COMMENT ON COLUMN t1.c1 IS 'c1 comment'",
        )

    @config.requirements.computed_columns
    def test_add_column_computed(self):
        context = op_fixture("oracle")
        op.add_column(
            "t1",
            Column("some_column", Integer, sqla_compat.Computed("foo * 5")),
        )
        context.assert_(
            "ALTER TABLE t1 ADD some_column "
            "INTEGER GENERATED ALWAYS AS (foo * 5)"
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
        op_fixture("oracle")
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

    def test_alter_table_rename_oracle(self):
        context = op_fixture("oracle")
        op.rename_table("s", "t")
        context.assert_("ALTER TABLE s RENAME TO t")

    def test_alter_table_rename_schema_oracle(self):
        context = op_fixture("oracle")
        op.rename_table("s", "t", schema="myowner")
        context.assert_("ALTER TABLE myowner.s RENAME TO t")

    def test_alter_column_rename_oracle(self):
        context = op_fixture("oracle")
        op.alter_column("t", "c", new_column_name="x")
        context.assert_("ALTER TABLE t RENAME COLUMN c TO x")

    def test_alter_column_new_type(self):
        context = op_fixture("oracle")
        op.alter_column("t", "c", type_=Integer)
        context.assert_("ALTER TABLE t MODIFY c INTEGER")

    def test_alter_column_add_comment(self):
        context = op_fixture("oracle")
        op.alter_column("t", "c", type_=Integer, comment="c comment")
        context.assert_(
            "ALTER TABLE t MODIFY c INTEGER",
            "COMMENT ON COLUMN t.c IS 'c comment'",
        )

    def test_alter_column_add_comment_quotes(self):
        context = op_fixture("oracle")
        op.alter_column("t", "c", type_=Integer, comment="c 'comment'")
        context.assert_(
            "ALTER TABLE t MODIFY c INTEGER",
            "COMMENT ON COLUMN t.c IS 'c ''comment'''",
        )

    def test_alter_column_drop_comment(self):
        context = op_fixture("oracle")
        op.alter_column("t", "c", type_=Integer, comment=None)
        context.assert_(
            "ALTER TABLE t MODIFY c INTEGER", "COMMENT ON COLUMN t.c IS ''"
        )

    def test_create_table_comment(self):
        # this is handled by SQLAlchemy's compilers
        context = op_fixture("oracle")
        op.create_table_comment("t2", comment="t2 table", schema="foo")
        context.assert_("COMMENT ON TABLE foo.t2 IS 't2 table'")

    def test_drop_table_comment(self):
        # this is handled by SQLAlchemy's compilers
        context = op_fixture("oracle")
        op.drop_table_comment("t2", existing_comment="t2 table", schema="foo")
        context.assert_("COMMENT ON TABLE foo.t2 IS ''")

    def test_drop_index(self):
        context = op_fixture("oracle")
        op.drop_index("my_idx", "my_table")
        context.assert_contains("DROP INDEX my_idx")

    def test_drop_column_w_default(self):
        context = op_fixture("oracle")
        op.drop_column("t1", "c1")
        context.assert_("ALTER TABLE t1 DROP COLUMN c1")

    def test_drop_column_w_check(self):
        context = op_fixture("oracle")
        op.drop_column("t1", "c1")
        context.assert_("ALTER TABLE t1 DROP COLUMN c1")

    def test_alter_column_nullable_w_existing_type(self):
        context = op_fixture("oracle")
        op.alter_column("t", "c", nullable=True, existing_type=Integer)
        context.assert_("ALTER TABLE t MODIFY c NULL")

    def test_alter_column_not_nullable_w_existing_type(self):
        context = op_fixture("oracle")
        op.alter_column("t", "c", nullable=False, existing_type=Integer)
        context.assert_("ALTER TABLE t MODIFY c NOT NULL")

    def test_alter_column_nullable_w_new_type(self):
        context = op_fixture("oracle")
        op.alter_column("t", "c", nullable=True, type_=Integer)
        context.assert_(
            "ALTER TABLE t MODIFY c NULL", "ALTER TABLE t MODIFY c INTEGER"
        )

    def test_alter_column_not_nullable_w_new_type(self):
        context = op_fixture("oracle")
        op.alter_column("t", "c", nullable=False, type_=Integer)
        context.assert_(
            "ALTER TABLE t MODIFY c NOT NULL", "ALTER TABLE t MODIFY c INTEGER"
        )

    def test_alter_add_server_default(self):
        context = op_fixture("oracle")
        op.alter_column("t", "c", server_default="5")
        context.assert_("ALTER TABLE t MODIFY c DEFAULT '5'")

    def test_alter_replace_server_default(self):
        context = op_fixture("oracle")
        op.alter_column(
            "t", "c", server_default="5", existing_server_default="6"
        )
        context.assert_("ALTER TABLE t MODIFY c DEFAULT '5'")

    def test_alter_remove_server_default(self):
        context = op_fixture("oracle")
        op.alter_column("t", "c", server_default=None)
        context.assert_("ALTER TABLE t MODIFY c DEFAULT NULL")

    def test_alter_do_everything(self):
        context = op_fixture("oracle")
        op.alter_column(
            "t",
            "c",
            new_column_name="c2",
            nullable=True,
            type_=Integer,
            server_default="5",
        )
        context.assert_(
            "ALTER TABLE t MODIFY c NULL",
            "ALTER TABLE t MODIFY c DEFAULT '5'",
            "ALTER TABLE t MODIFY c INTEGER",
            "ALTER TABLE t RENAME COLUMN c TO c2",
        )

    @config.requirements.comments
    def test_create_table_with_column_comments(self):
        context = op_fixture("oracle")
        op.create_table(
            "t2", Column("c1", Integer, primary_key=True), comment="t2 comment"
        )
        context.assert_(
            "CREATE TABLE t2 (c1 INTEGER NOT NULL, PRIMARY KEY (c1))",
            "COMMENT ON TABLE t2 IS 't2 comment'",
        )

    # TODO: when we add schema support
    # def test_alter_column_rename_oracle_schema(self):
    #    context = op_fixture('oracle')
    #    op.alter_column("t", "c", name="x", schema="y")
    #    context.assert_(
    #        'ALTER TABLE y.t RENAME COLUMN c TO c2'
    #    )

    def _identity_qualification(self, kw):
        always = kw.get("always", False)
        if always is None:
            return ""
        qualification = "ALWAYS" if always else "BY DEFAULT"
        if kw.get("on_null", False):
            qualification += " ON NULL"
        return qualification

    @config.requirements.identity_columns
    @combinations(
        ({}, None),
        (dict(always=True), None),
        (dict(always=None, order=True), "ORDER"),
        (
            dict(start=3, increment=33, maxvalue=99, cycle=True),
            "INCREMENT BY 33 START WITH 3 MAXVALUE 99 CYCLE",
        ),
        (dict(on_null=True, start=42), "START WITH 42"),
    )
    def test_add_column_identity(self, kw, text):
        context = op_fixture("oracle")
        op.add_column(
            "t1",
            Column("some_column", Integer, sqla_compat.Identity(**kw)),
        )
        qualification = self._identity_qualification(kw)
        options = " (%s)" % text if text else ""
        context.assert_(
            "ALTER TABLE t1 ADD some_column "
            "INTEGER GENERATED %s AS IDENTITY%s" % (qualification, options)
        )

    @config.requirements.identity_columns
    @combinations(
        ({}, None),
        (dict(always=True), None),
        (dict(always=None, cycle=True), "CYCLE"),
        (
            dict(start=3, increment=33, maxvalue=99, cycle=True),
            "INCREMENT BY 33 START WITH 3 MAXVALUE 99 CYCLE",
        ),
        (dict(on_null=True, start=42), "START WITH 42"),
    )
    def test_add_identity_to_column(self, kw, text):
        context = op_fixture("oracle")
        op.alter_column(
            "t1",
            "some_column",
            server_default=sqla_compat.Identity(**kw),
            existing_server_default=None,
        )
        qualification = self._identity_qualification(kw)
        options = " (%s)" % text if text else ""
        context.assert_(
            "ALTER TABLE t1 MODIFY some_column "
            "GENERATED %s AS IDENTITY%s" % (qualification, options)
        )

    @config.requirements.identity_columns
    def test_remove_identity_from_column(self):
        context = op_fixture("oracle")
        op.alter_column(
            "t1",
            "some_column",
            server_default=None,
            existing_server_default=sqla_compat.Identity(),
        )
        context.assert_("ALTER TABLE t1 MODIFY some_column DROP IDENTITY")

    @config.requirements.identity_columns
    @combinations(
        ({}, dict(always=True), None),
        (
            dict(always=True),
            dict(always=False, start=3),
            "START WITH 3",
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
            "INCREMENT BY 1 START WITH 3 MINVALUE -3 MAXVALUE 99 CYCLE",
        ),
        (
            dict(
                always=False,
                start=3,
                maxvalue=9999,
                minvalue=0,
            ),
            dict(always=False, start=3, order=True, on_null=False, cache=2),
            "START WITH 3 CACHE 2 ORDER",
        ),
        (
            dict(always=False),
            dict(always=None, minvalue=0),
            "MINVALUE 0",
        ),
    )
    def test_change_identity_in_column(self, existing, updated, text):
        context = op_fixture("oracle")
        op.alter_column(
            "t1",
            "some_column",
            server_default=sqla_compat.Identity(**updated),
            existing_server_default=sqla_compat.Identity(**existing),
        )

        qualification = self._identity_qualification(updated)
        options = " (%s)" % text if text else ""
        context.assert_(
            "ALTER TABLE t1 MODIFY some_column "
            "GENERATED %s AS IDENTITY%s" % (qualification, options)
        )
