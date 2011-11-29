from tests import clear_staging_env, staging_env, \
    no_sql_testing_config, sqlite_db, eq_, ne_, capture_context_buffer, \
    three_rev_fixture
from alembic import command, util

def setup():
    global cfg, env
    env = staging_env()
    cfg = no_sql_testing_config()

    global a, b, c
    a, b, c = three_rev_fixture(cfg)

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

