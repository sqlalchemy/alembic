# coding: utf-8

from __future__ import with_statement, unicode_literals

from tests import clear_staging_env, staging_env, \
    _no_sql_testing_config, capture_context_buffer, \
    three_rev_fixture, write_script
from alembic import command, util
from alembic.script import ScriptDirectory
import unittest

cfg = None
a, b, c = None, None, None

class ThreeRevTest(unittest.TestCase):

    def setUp(self):
        global cfg, env
        env = staging_env()
        cfg = _no_sql_testing_config()
        cfg.set_main_option('dialect_name', 'sqlite')
        cfg.remove_main_option('url')
        global a, b, c
        a, b, c = three_rev_fixture(cfg)

    def tearDown(self):
        clear_staging_env()

    def test_begin_comit(self):
        with capture_context_buffer(transactional_ddl=True) as buf:
            command.upgrade(cfg, a, sql=True)
        assert "BEGIN;" in buf.getvalue()
        assert "COMMIT;" in buf.getvalue()

        with capture_context_buffer(transactional_ddl=False) as buf:
            command.upgrade(cfg, a, sql=True)
        assert "BEGIN;" not in buf.getvalue()
        assert "COMMIT;" not in buf.getvalue()

    def test_version_from_none_insert(self):
        with capture_context_buffer() as buf:
            command.upgrade(cfg, a, sql=True)
        assert "CREATE TABLE alembic_version" in buf.getvalue()
        assert "INSERT INTO alembic_version" in buf.getvalue()
        assert "CREATE STEP 1" in buf.getvalue()
        assert "CREATE STEP 2" not in buf.getvalue()
        assert "CREATE STEP 3" not in buf.getvalue()

    def test_version_from_middle_update(self):
        with capture_context_buffer() as buf:
            command.upgrade(cfg, "%s:%s" % (b, c), sql=True)
        assert "CREATE TABLE alembic_version" not in buf.getvalue()
        assert "UPDATE alembic_version" in buf.getvalue()
        assert "CREATE STEP 1" not in buf.getvalue()
        assert "CREATE STEP 2" not in buf.getvalue()
        assert "CREATE STEP 3" in buf.getvalue()

    def test_version_to_none(self):
        with capture_context_buffer() as buf:
            command.downgrade(cfg, "%s:base" % c, sql=True)
        assert "CREATE TABLE alembic_version" not in buf.getvalue()
        assert "INSERT INTO alembic_version" not in buf.getvalue()
        assert "DROP TABLE alembic_version" in buf.getvalue()
        assert "DROP STEP 3" in buf.getvalue()
        assert "DROP STEP 2" in buf.getvalue()
        assert "DROP STEP 1" in buf.getvalue()

    def test_version_to_middle(self):
        with capture_context_buffer() as buf:
            command.downgrade(cfg, "%s:%s" % (c, a), sql=True)
        assert "CREATE TABLE alembic_version" not in buf.getvalue()
        assert "INSERT INTO alembic_version" not in buf.getvalue()
        assert "DROP TABLE alembic_version" not in buf.getvalue()
        assert "DROP STEP 3" in buf.getvalue()
        assert "DROP STEP 2" in buf.getvalue()
        assert "DROP STEP 1" not in buf.getvalue()

    def test_stamp(self):
        with capture_context_buffer() as buf:
            command.stamp(cfg, "head", sql=True)
        assert "UPDATE alembic_version SET version_num='%s';" % c in buf.getvalue()


class EncodingTest(unittest.TestCase):
    def setUp(self):
        global cfg, env, a
        env = staging_env()
        cfg = _no_sql_testing_config()
        cfg.set_main_option('dialect_name', 'sqlite')
        cfg.remove_main_option('url')
        a = util.rev_id()
        script = ScriptDirectory.from_config(cfg)
        script.generate_revision(a, "revision a", refresh=True)
        write_script(script, a, """# coding: utf-8
from __future__ import unicode_literals
revision = '%s'
down_revision = None

from alembic import op

def upgrade():
    op.execute("« S’il vous plaît…")

def downgrade():
    op.execute("drôle de petite voix m’a réveillé")

""".encode('utf-8') % a)

    def tearDown(self):
        clear_staging_env()

    def test_encode(self):
        with capture_context_buffer(output_encoding='utf-8') as buf:
            command.upgrade(cfg, a, sql=True)
        assert "« S’il vous plaît…".encode("utf-8") in buf.getvalue()
