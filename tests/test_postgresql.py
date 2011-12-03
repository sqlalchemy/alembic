
from tests import op_fixture, db_for_dialect, eq_, staging_env, \
            clear_staging_env, _no_sql_testing_config,\
            capture_context_buffer, requires_07
from unittest import TestCase
from sqlalchemy import DateTime, MetaData, Table, Column, text, Integer, String
from sqlalchemy.engine.reflection import Inspector
from alembic import context, command, util
from alembic.script import ScriptDirectory

class PGOfflineEnumTest(TestCase):
    @requires_07
    def setUp(self):
        env = staging_env()
        self.cfg = cfg = _no_sql_testing_config()

        self.rid = rid = util.rev_id()

        self.script = script = ScriptDirectory.from_config(cfg)
        script.generate_rev(rid, None, refresh=True)

    def tearDown(self):
        clear_staging_env()


    def _inline_enum_script(self):
        self.script.write(self.rid, """
down_revision = None

from alembic.op import *
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy import Column

def upgrade():
    create_table("sometable", 
        Column("data", ENUM("one", "two", "three", name="pgenum"))
    )

def downgrade():
    drop_table("sometable")
""")

    def _distinct_enum_script(self):
        self.script.write(self.rid, """
down_revision = None

from alembic.op import *
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy import Column

def upgrade():
    enum = ENUM("one", "two", "three", name="pgenum", create_type=False)
    enum.create(get_bind(), checkfirst=False)
    create_table("sometable", 
        Column("data", enum)
    )

def downgrade():
    drop_table("sometable")
    ENUM(name="pgenum").drop(get_bind(), checkfirst=False)
    
""")

    def test_offline_inline_enum_create(self):
        self._inline_enum_script()
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.rid, sql=True)
        assert "CREATE TYPE pgenum AS ENUM ('one','two','three')" in buf.getvalue()
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
        assert "CREATE TYPE pgenum AS ENUM ('one','two','three')" in buf.getvalue()
        assert "CREATE TABLE sometable (\n    data pgenum\n)" in buf.getvalue()

    def test_offline_distinct_enum_drop(self):
        self._distinct_enum_script()
        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, "%s:base" % self.rid, sql=True)
        assert "DROP TABLE sometable" in buf.getvalue()
        assert "DROP TYPE pgenum" in buf.getvalue()



class PostgresqlDefaultCompareTest(TestCase):
    @classmethod
    def setup_class(cls):
        cls.bind = db_for_dialect("postgresql")
        staging_env()
        context.configure(
            connection = cls.bind.connect(),
            compare_type = True,
            compare_server_default = True,
        )
        connection = context.get_bind()
        cls.autogen_context = {
            'imports':set(),
            'connection':connection,
            'dialect':connection.dialect,
            'context':context.get_context()
            }

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def setUp(self):
        self.metadata = MetaData(self.bind)

    def tearDown(self):
        self.metadata.drop_all()

    def _compare_default_roundtrip(
        self, type_, txt, alternate=None):
        if alternate:
            expected = True
        else:
            alternate = txt
            expected = False
        t = Table("test", self.metadata,
            Column("somecol", type_, server_default=text(txt))
        )
        t2 = Table("test", MetaData(),
            Column("somecol", type_, server_default=text(alternate))
        )
        assert self._compare_default(
            t, t2, t2.c.somecol, alternate
        ) is expected

    def _compare_default(
        self,
        t1, t2, col,
        rendered
    ):
        t1.create(self.bind)
        insp = Inspector.from_engine(self.bind)
        cols = insp.get_columns(t1.name)
        ctx = context.get_context()
        return ctx.impl.compare_server_default(
            cols[0],
            col, 
            rendered)

    def test_compare_current_timestamp(self):
        self._compare_default_roundtrip(
            DateTime(),
            "TIMEZONE('utc', CURRENT_TIMESTAMP)",
        )

    def test_compare_current_timestamp(self):
        self._compare_default_roundtrip(
            DateTime(),
            "TIMEZONE('utc', CURRENT_TIMESTAMP)",
        )

    def test_compare_integer(self):
        self._compare_default_roundtrip(
            Integer(),
            "5",
        )

    def test_compare_integer_diff(self):
        self._compare_default_roundtrip(
            Integer(),
            "5", "7"
        )

    def test_compare_character_diff(self):
        self._compare_default_roundtrip(
            String(),
            "'hello'",
            "'there'"
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