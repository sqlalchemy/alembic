
from tests import op_fixture, db_for_dialect, eq_, staging_env, clear_staging_env
from unittest import TestCase
from sqlalchemy import DateTime, MetaData, Table, Column, text, Integer, String
from sqlalchemy.engine.reflection import Inspector
from alembic import context

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
#        t.create(self.bind)
#        insp = Inspector.from_engine(self.bind)
#        cols = insp.get_columns("test")
#        ctx = context.get_context()
#        assert ctx.impl.compare_server_default(
#           cols[0],
#            t2.c.somecol, 
#           alternate) is expected

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