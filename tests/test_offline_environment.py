from tests import clear_staging_env, staging_env, \
    _no_sql_testing_config, sqlite_db, eq_, ne_, \
    capture_context_buffer, three_rev_fixture, _env_file_fixture
from alembic import command, util

def setup():
    global cfg, env
    env = staging_env()
    cfg = _no_sql_testing_config()

    global a, b, c
    a, b, c = three_rev_fixture(cfg)

def teardown():
    clear_staging_env()

def test_not_requires_connection():
    _env_file_fixture("""
assert not context.requires_connection()
""")
    command.upgrade(cfg, a, sql=True)
    command.downgrade(cfg, a, sql=True)

def test_requires_connection():
    _env_file_fixture("""
assert context.requires_connection()
""")
    command.upgrade(cfg, a)
    command.downgrade(cfg, a)


def test_starting_rev():
    _env_file_fixture("""
context.configure(dialect_name='sqlite', starting_rev='x')
assert context.get_starting_revision_argument() == 'x'
""")
    command.upgrade(cfg, a, sql=True)
    command.downgrade(cfg, a, sql=True)


def test_destination_rev():
    _env_file_fixture("""
context.configure(dialect_name='sqlite')
assert context.get_revision_argument() == '%s'
""" % b)
    command.upgrade(cfg, b, sql=True)
    command.downgrade(cfg, b, sql=True)


def test_head_rev():
    _env_file_fixture("""
context.configure(dialect_name='sqlite')
assert context.get_head_revision() == '%s'
""" % c)
    command.upgrade(cfg, b, sql=True)
    command.downgrade(cfg, b, sql=True)

def test_tag_cmd_arg():
    _env_file_fixture("""
context.configure(dialect_name='sqlite')
assert context.get_tag_argument() == 'hi'
""")
    command.upgrade(cfg, b, sql=True, tag='hi')
    command.downgrade(cfg, b, sql=True, tag='hi')

def test_tag_cfg_arg():
    _env_file_fixture("""
context.configure(dialect_name='sqlite', tag='there')
assert context.get_tag_argument() == 'there'
""")
    command.upgrade(cfg, b, sql=True, tag='hi')
    command.downgrade(cfg, b, sql=True, tag='hi')
