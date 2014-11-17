from alembic.testing.fixtures import TestBase

from alembic import command, util

from alembic.testing import assert_raises_message
from alembic.testing.env import staging_env, _no_sql_testing_config, \
    three_rev_fixture, clear_staging_env, env_file_fixture


a = b = c = None


class OfflineEnvironmentTest(TestBase):

    def setUp(self):
        staging_env()
        self.cfg = _no_sql_testing_config()

        global a, b, c
        a, b, c = three_rev_fixture(self.cfg)

    def tearDown(self):
        clear_staging_env()

    def test_not_requires_connection(self):
        env_file_fixture("""
assert not context.requires_connection()
""")
        command.upgrade(self.cfg, a, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)

    def test_requires_connection(self):
        env_file_fixture("""
assert context.requires_connection()
""")
        command.upgrade(self.cfg, a)
        command.downgrade(self.cfg, a)

    def test_starting_rev_post_context(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite', starting_rev='x')
assert context.get_starting_revision_argument() == 'x'
""")
        command.upgrade(self.cfg, a, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)
        command.current(self.cfg)
        command.stamp(self.cfg, a)

    def test_starting_rev_pre_context(self):
        env_file_fixture("""
assert context.get_starting_revision_argument() == 'x'
""")
        command.upgrade(self.cfg, "x:y", sql=True)
        command.downgrade(self.cfg, "x:y", sql=True)

    def test_starting_rev_pre_context_cmd_w_no_startrev(self):
        env_file_fixture("""
assert context.get_starting_revision_argument() == 'x'
""")
        assert_raises_message(
            util.CommandError,
            "No starting revision argument is available.",
            command.current, self.cfg)

    def test_starting_rev_current_pre_context(self):
        env_file_fixture("""
assert context.get_starting_revision_argument() is None
""")
        assert_raises_message(
            util.CommandError,
            "No starting revision argument is available.",
            command.current, self.cfg
        )

    def test_destination_rev_pre_context(self):
        env_file_fixture("""
assert context.get_revision_argument() == '%s'
""" % b)
        command.upgrade(self.cfg, b, sql=True)
        command.stamp(self.cfg, b, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (c, b), sql=True)

    def test_destination_rev_post_context(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite')
assert context.get_revision_argument() == '%s'
""" % b)
        command.upgrade(self.cfg, b, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (c, b), sql=True)
        command.stamp(self.cfg, b, sql=True)

    def test_head_rev_pre_context(self):
        env_file_fixture("""
assert context.get_head_revision() == '%s'
""" % c)
        command.upgrade(self.cfg, b, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)
        command.stamp(self.cfg, b, sql=True)
        command.current(self.cfg)

    def test_head_rev_post_context(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite')
assert context.get_head_revision() == '%s'
""" % c)
        command.upgrade(self.cfg, b, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)
        command.stamp(self.cfg, b, sql=True)
        command.current(self.cfg)

    def test_tag_pre_context(self):
        env_file_fixture("""
assert context.get_tag_argument() == 'hi'
""")
        command.upgrade(self.cfg, b, sql=True, tag='hi')
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True, tag='hi')

    def test_tag_pre_context_None(self):
        env_file_fixture("""
assert context.get_tag_argument() is None
""")
        command.upgrade(self.cfg, b, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)

    def test_tag_cmd_arg(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite')
assert context.get_tag_argument() == 'hi'
""")
        command.upgrade(self.cfg, b, sql=True, tag='hi')
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True, tag='hi')

    def test_tag_cfg_arg(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite', tag='there')
assert context.get_tag_argument() == 'there'
""")
        command.upgrade(self.cfg, b, sql=True, tag='hi')
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True, tag='hi')

    def test_tag_None(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite')
assert context.get_tag_argument() is None
""")
        command.upgrade(self.cfg, b, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)

    def test_downgrade_wo_colon(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite')
""")
        assert_raises_message(
            util.CommandError,
            "downgrade with --sql requires <fromrev>:<torev>",
            command.downgrade,
            self.cfg, b, sql=True
        )

    def test_upgrade_with_output_encoding(self):
        env_file_fixture("""
url = config.get_main_option('sqlalchemy.url')
context.configure(url=url, output_encoding='utf-8')
assert not context.requires_connection()
""")
        command.upgrade(self.cfg, a, sql=True)
        command.downgrade(self.cfg, "%s:%s" % (b, a), sql=True)
