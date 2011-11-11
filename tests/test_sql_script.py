from tests import clear_staging_env, staging_env, _no_sql_testing_config, sqlite_db, eq_, ne_, capture_context_buffer
from alembic import command, util
from alembic.script import ScriptDirectory

def setup():
    global cfg, env
    env = staging_env()
    cfg = _no_sql_testing_config()

    global a, b, c
    a = util.rev_id()
    b = util.rev_id()
    c = util.rev_id()

    script = ScriptDirectory.from_config(cfg)
    script.generate_rev(a, None)
    script.write(a, """
down_revision = None

from alembic.op import *

def upgrade():
    execute("CREATE STEP 1")

def downgrade():
    execute("DROP STEP 1")

""")

    script.generate_rev(b, None)
    script.write(b, """
down_revision = '%s'

from alembic.op import *

def upgrade():
    execute("CREATE STEP 2")

def downgrade():
    execute("DROP STEP 2")

""" % a)

    script.generate_rev(c, None)
    script.write(c, """
down_revision = '%s'

from alembic.op import *

def upgrade():
    execute("CREATE STEP 3")

def downgrade():
    execute("DROP STEP 3")

""" % b)

def teardown():
    clear_staging_env()

def test_version_from_none_insert():
    with capture_context_buffer() as buf:
        command.upgrade(cfg, a, sql=True)
    assert "CREATE TABLE alembic_version" in buf.getvalue()
    assert "INSERT INTO alembic_version" in buf.getvalue()
    assert "CREATE STEP 1" in buf.getvalue()
    assert "CREATE STEP 2" not in buf.getvalue()
    assert "CREATE STEP 3" not in buf.getvalue()

def test_version_from_middle_update():
    with capture_context_buffer() as buf:
        command.upgrade(cfg, "%s:%s" % (b, c), sql=True)
    assert "CREATE TABLE alembic_version" not in buf.getvalue()
    assert "UPDATE alembic_version" in buf.getvalue()
    assert "CREATE STEP 1" not in buf.getvalue()
    assert "CREATE STEP 2" not in buf.getvalue()
    assert "CREATE STEP 3" in buf.getvalue()

def test_version_to_none():
    with capture_context_buffer() as buf:
        command.downgrade(cfg, "%s:base" % c, sql=True)
    assert "CREATE TABLE alembic_version" not in buf.getvalue()
    assert "INSERT INTO alembic_version" not in buf.getvalue()
    assert "DROP TABLE alembic_version" in buf.getvalue()
    assert "DROP STEP 3" in buf.getvalue()
    assert "DROP STEP 2" in buf.getvalue()
    assert "DROP STEP 1" in buf.getvalue()

def test_version_to_middle():
    with capture_context_buffer() as buf:
        command.downgrade(cfg, "%s:%s" % (c, a), sql=True)
    assert "CREATE TABLE alembic_version" not in buf.getvalue()
    assert "INSERT INTO alembic_version" not in buf.getvalue()
    assert "DROP TABLE alembic_version" not in buf.getvalue()
    assert "DROP STEP 3" in buf.getvalue()
    assert "DROP STEP 2" in buf.getvalue()
    assert "DROP STEP 1" not in buf.getvalue()


def test_stamp():
    with capture_context_buffer() as buf:
        command.stamp(cfg, "head", sql=True)
    assert "UPDATE alembic_version SET version_num='%s';" % c in buf.getvalue()
