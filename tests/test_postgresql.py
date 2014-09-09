from unittest import TestCase

from sqlalchemy import DateTime, MetaData, Table, Column, text, Integer, \
    String, Interval
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.schema import DefaultClause
from sqlalchemy.engine.reflection import Inspector
from alembic.operations import Operations
from sqlalchemy.sql import table, column
from alembic.autogenerate.compare import _compare_server_default

from alembic import command, util
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from . import db_for_dialect, eq_, staging_env, \
    clear_staging_env, _no_sql_testing_config,\
    capture_context_buffer, requires_09, write_script


class PGOfflineEnumTest(TestCase):

    def setUp(self):
        staging_env()
        self.cfg = cfg = _no_sql_testing_config()

        self.rid = rid = util.rev_id()

        self.script = script = ScriptDirectory.from_config(cfg)
        script.generate_revision(rid, None, refresh=True)

    def tearDown(self):
        clear_staging_env()

    def _inline_enum_script(self):
        write_script(self.script, self.rid, """
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
""" % self.rid)

    def _distinct_enum_script(self):
        write_script(self.script, self.rid, """
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

""" % self.rid)

    @requires_09
    def test_offline_inline_enum_create(self):
        self._inline_enum_script()
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.rid, sql=True)
        assert "CREATE TYPE pgenum AS "\
            "ENUM ('one', 'two', 'three')" in buf.getvalue()
        assert "CREATE TABLE sometable (\n    data pgenum\n)" in buf.getvalue()

    def test_offline_inline_enum_drop(self):
        self._inline_enum_script()
        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, "%s:base" % self.rid, sql=True)
        assert "DROP TABLE sometable" in buf.getvalue()
        # no drop since we didn't emit events
        assert "DROP TYPE pgenum" not in buf.getvalue()

    @requires_09
    def test_offline_distinct_enum_create(self):
        self._distinct_enum_script()
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.rid, sql=True)
        assert "CREATE TYPE pgenum AS ENUM "\
            "('one', 'two', 'three')" in buf.getvalue()
        assert "CREATE TABLE sometable (\n    data pgenum\n)" in buf.getvalue()

    def test_offline_distinct_enum_drop(self):
        self._distinct_enum_script()
        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, "%s:base" % self.rid, sql=True)
        assert "DROP TABLE sometable" in buf.getvalue()
        assert "DROP TYPE pgenum" in buf.getvalue()


class PostgresqlInlineLiteralTest(TestCase):

    @classmethod
    def setup_class(cls):
        cls.bind = db_for_dialect("postgresql")
        cls.bind.execute("""
            create table tab (
                col varchar(50)
            )
        """)
        cls.bind.execute("""
            insert into tab (col) values
                ('old data 1'),
                ('old data 2.1'),
                ('old data 3')
        """)

    @classmethod
    def teardown_class(cls):
        cls.bind.execute("drop table tab")

    def setUp(self):
        self.conn = self.bind.connect()
        ctx = MigrationContext.configure(self.conn)
        self.op = Operations(ctx)

    def tearDown(self):
        self.conn.close()

    def test_inline_percent(self):
        # TODO: here's the issue, you need to escape this.
        tab = table('tab', column('col'))
        self.op.execute(
            tab.update().where(
                tab.c.col.like(self.op.inline_literal('%.%'))
            ).values(col=self.op.inline_literal('new data')),
            execution_options={'no_parameters': True}
        )
        eq_(
            self.conn.execute(
                "select count(*) from tab where col='new data'").scalar(),
            1,
        )


class PostgresqlDefaultCompareTest(TestCase):

    @classmethod
    def setup_class(cls):
        cls.bind = db_for_dialect("postgresql")
        staging_env()
        context = MigrationContext.configure(
            connection=cls.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True
            }
        )
        connection = context.bind
        cls.autogen_context = {
            'imports': set(),
            'connection': connection,
            'dialect': connection.dialect,
            'context': context
        }

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def setUp(self):
        self.metadata = MetaData(self.bind)

    def tearDown(self):
        self.metadata.drop_all()

    def _compare_default_roundtrip(self, type_, orig_default, alternate=None):
        diff_expected = alternate is not None
        if alternate is None:
            alternate = orig_default

        t1 = Table("test", self.metadata,
                   Column("somecol", type_, server_default=orig_default))
        t2 = Table("test", MetaData(),
                   Column("somecol", type_, server_default=alternate))

        t1.create(self.bind)

        insp = Inspector.from_engine(self.bind)
        cols = insp.get_columns(t1.name)
        insp_col = Column("somecol", cols[0]['type'],
                          server_default=text(cols[0]['default']))
        diffs = []
        _compare_server_default(None, "test", "somecol", insp_col,
                                t2.c.somecol, diffs, self.autogen_context)
        eq_(bool(diffs), diff_expected)

    def _compare_default(
        self,
        t1, t2, col,
        rendered
    ):
        t1.create(self.bind, checkfirst=True)
        insp = Inspector.from_engine(self.bind)
        cols = insp.get_columns(t1.name)
        ctx = self.autogen_context['context']

        return ctx.impl.compare_server_default(
            None,
            col,
            rendered,
            cols[0]['default'])

    def test_compare_interval_str(self):
        # this form shouldn't be used but testing here
        # for compatibility
        self._compare_default_roundtrip(
            Interval,
            "14 days"
        )

    def test_compare_interval_text(self):
        self._compare_default_roundtrip(
            Interval,
            text("'14 days'")
        )

    def test_compare_array_of_integer_text(self):
        self._compare_default_roundtrip(
            ARRAY(Integer),
            text("(ARRAY[]::integer[])")
        )

    def test_compare_current_timestamp_text(self):
        self._compare_default_roundtrip(
            DateTime(),
            text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
        )

    def test_compare_integer_str(self):
        self._compare_default_roundtrip(
            Integer(),
            "5",
        )

    def test_compare_integer_text(self):
        self._compare_default_roundtrip(
            Integer(),
            text("5"),
        )

    def test_compare_integer_text_diff(self):
        self._compare_default_roundtrip(
            Integer(),
            text("5"), "7"
        )

    def test_compare_character_str(self):
        self._compare_default_roundtrip(
            String(),
            "hello",
        )

    def test_compare_character_text(self):
        self._compare_default_roundtrip(
            String(),
            text("'hello'"),
        )

    def test_compare_character_str_diff(self):
        self._compare_default_roundtrip(
            String(),
            "hello",
            "there"
        )

    def test_compare_character_text_diff(self):
        self._compare_default_roundtrip(
            String(),
            text("'hello'"),
            text("'there'")
        )

    def test_primary_key_skip(self):
        """Test that SERIAL cols are just skipped"""
        t1 = Table("sometable", self.metadata,
                   Column("id", Integer, primary_key=True)
                   )
        t2 = Table("sometable", MetaData(),
                   Column("id", Integer, primary_key=True)
                   )
        assert not self._compare_default(
            t1, t2, t2.c.id, ""
        )
