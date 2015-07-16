from alembic import command
from io import TextIOWrapper, BytesIO
from alembic.script import ScriptDirectory
from alembic.testing.fixtures import TestBase, capture_context_buffer
from alembic.testing.env import staging_env, _sqlite_testing_config, \
    three_rev_fixture, clear_staging_env, _no_sql_testing_config, \
    _sqlite_file_db, write_script, env_file_fixture
from alembic.testing import eq_, assert_raises_message
from alembic import util

try:
    from mock import patch
except ImportError:
    from unittest.mock import patch


class HistoryTest(TestBase):

    @classmethod
    def setup_class(cls):
        cls.env = staging_env()
        cls.cfg = _sqlite_testing_config()
        cls.a, cls.b, cls.c = three_rev_fixture(cls.cfg)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def _eq_cmd_output(self, buf, expected):
        script = ScriptDirectory.from_config(self.cfg)

        # test default encode/decode behavior as well,
        # rev B has a non-ascii char in it + a coding header.
        eq_(
            buf.getvalue().decode("ascii", 'replace').strip(),
            "\n".join([
                script.get_revision(rev).log_entry
                for rev in expected
            ]).encode("ascii", "replace").decode("ascii").strip()
        )

    def _buf_fixture(self):
        # try to simulate how sys.stdout looks - we send it u''
        # but then it's trying to encode to something.
        buf = BytesIO()
        wrapper = TextIOWrapper(buf, encoding='ascii', line_buffering=True)
        wrapper.getvalue = buf.getvalue
        return wrapper

    def test_history_full(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b, self.a])

    def test_history_num_range(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "%s:%s" % (self.a, self.b), verbose=True)
        self._eq_cmd_output(buf, [self.b, self.a])

    def test_history_base_to_num(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, ":%s" % (self.b), verbose=True)
        self._eq_cmd_output(buf, [self.b, self.a])

    def test_history_num_to_head(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "%s:" % (self.a), verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b, self.a])

    def test_history_num_plus_relative(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "%s:+2" % (self.a), verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b, self.a])

    def test_history_relative_to_num(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "-2:%s" % (self.c), verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b, self.a])

    def test_history_too_large_relative_to_num(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "-5:%s" % (self.c), verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b, self.a])

    def test_history_current_to_head_as_b(self):
        command.stamp(self.cfg, self.b)
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "current:", verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b])

    def test_history_current_to_head_as_base(self):
        command.stamp(self.cfg, "base")
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "current:", verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b, self.a])


class RevisionTest(TestBase):
    def setUp(self):
        self.env = staging_env()
        self.cfg = _sqlite_testing_config()

    def tearDown(self):
        clear_staging_env()

    def _env_fixture(self):
        env_file_fixture("""

from sqlalchemy import MetaData, engine_from_config
target_metadata = MetaData()

engine = engine_from_config(
    config.get_section(config.config_ini_section),
    prefix='sqlalchemy.')

connection = engine.connect()

context.configure(connection=connection, target_metadata=target_metadata)

try:
    with context.begin_transaction():
        context.run_migrations()
finally:
    connection.close()

""")

    def test_create_rev_plain_db_not_up_to_date(self):
        self._env_fixture()
        command.revision(self.cfg)
        command.revision(self.cfg)  # no problem

    def test_create_rev_autogen(self):
        self._env_fixture()
        command.revision(self.cfg, autogenerate=True)

    def test_create_rev_autogen_db_not_up_to_date(self):
        self._env_fixture()
        command.revision(self.cfg)
        assert_raises_message(
            util.CommandError,
            "Target database is not up to date.",
            command.revision, self.cfg, autogenerate=True
        )

    def test_create_rev_autogen_db_not_up_to_date_multi_heads(self):
        self._env_fixture()
        command.revision(self.cfg)
        rev2 = command.revision(self.cfg)
        rev3a = command.revision(self.cfg)
        command.revision(self.cfg, head=rev2.revision, splice=True)
        command.upgrade(self.cfg, "heads")
        command.revision(self.cfg, head=rev3a.revision)

        assert_raises_message(
            util.CommandError,
            "Target database is not up to date.",
            command.revision, self.cfg, autogenerate=True
        )

    def test_create_rev_plain_db_not_up_to_date_multi_heads(self):
        self._env_fixture()
        command.revision(self.cfg)
        rev2 = command.revision(self.cfg)
        rev3a = command.revision(self.cfg)
        command.revision(self.cfg, head=rev2.revision, splice=True)
        command.upgrade(self.cfg, "heads")
        command.revision(self.cfg, head=rev3a.revision)

        assert_raises_message(
            util.CommandError,
            "Multiple heads are present; please specify the head revision "
            "on which the new revision should be based, or perform a merge.",
            command.revision, self.cfg
        )

    def test_create_rev_autogen_need_to_select_head(self):
        self._env_fixture()
        command.revision(self.cfg)
        rev2 = command.revision(self.cfg)
        command.revision(self.cfg)
        command.revision(self.cfg, head=rev2.revision, splice=True)
        command.upgrade(self.cfg, "heads")
        # there's multiple heads present
        assert_raises_message(
            util.CommandError,
            "Multiple heads are present; please specify the head revision "
            "on which the new revision should be based, or perform a merge.",
            command.revision, self.cfg, autogenerate=True
        )

    def test_create_rev_plain_need_to_select_head(self):
        self._env_fixture()
        command.revision(self.cfg)
        rev2 = command.revision(self.cfg)
        command.revision(self.cfg)
        command.revision(self.cfg, head=rev2.revision, splice=True)
        command.upgrade(self.cfg, "heads")
        # there's multiple heads present
        assert_raises_message(
            util.CommandError,
            "Multiple heads are present; please specify the head revision "
            "on which the new revision should be based, or perform a merge.",
            command.revision, self.cfg
        )

    def test_create_rev_plain_post_merge(self):
        self._env_fixture()
        command.revision(self.cfg)
        rev2 = command.revision(self.cfg)
        command.revision(self.cfg)
        command.revision(self.cfg, head=rev2.revision, splice=True)
        command.merge(self.cfg, "heads")
        command.revision(self.cfg)

    def test_create_rev_autogenerate_post_merge(self):
        self._env_fixture()
        command.revision(self.cfg)
        rev2 = command.revision(self.cfg)
        command.revision(self.cfg)
        command.revision(self.cfg, head=rev2.revision, splice=True)
        command.merge(self.cfg, "heads")
        command.upgrade(self.cfg, "heads")
        command.revision(self.cfg, autogenerate=True)

    def test_create_rev_autogenerate_db_not_up_to_date_post_merge(self):
        self._env_fixture()
        command.revision(self.cfg)
        rev2 = command.revision(self.cfg)
        command.revision(self.cfg)
        command.revision(self.cfg, head=rev2.revision, splice=True)
        command.upgrade(self.cfg, "heads")
        command.merge(self.cfg, "heads")
        assert_raises_message(
            util.CommandError,
            "Target database is not up to date.",
            command.revision, self.cfg, autogenerate=True
        )

    def test_nonsensical_sql_mode_autogen(self):
        self._env_fixture()
        assert_raises_message(
            util.CommandError,
            "Using --sql with --autogenerate does not make any sense",
            command.revision, self.cfg, autogenerate=True, sql=True
        )

    def test_nonsensical_sql_no_env(self):
        self._env_fixture()
        assert_raises_message(
            util.CommandError,
            "Using --sql with the revision command when revision_environment "
            "is not configured does not make any sense",
            command.revision, self.cfg, sql=True
        )

    def test_sensical_sql_w_env(self):
        self._env_fixture()
        self.cfg.set_main_option("revision_environment", "true")
        command.revision(self.cfg, sql=True)


class UpgradeDowngradeStampTest(TestBase):

    def setUp(self):
        self.env = staging_env()
        self.cfg = cfg = _no_sql_testing_config()
        cfg.set_main_option('dialect_name', 'sqlite')
        cfg.remove_main_option('url')

        self.a, self.b, self.c = three_rev_fixture(cfg)

    def tearDown(self):
        clear_staging_env()

    def test_version_from_none_insert(self):
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "CREATE TABLE alembic_version" in buf.getvalue()
        assert "INSERT INTO alembic_version" in buf.getvalue()
        assert "CREATE STEP 1" in buf.getvalue()
        assert "CREATE STEP 2" not in buf.getvalue()
        assert "CREATE STEP 3" not in buf.getvalue()

    def test_version_from_middle_update(self):
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, "%s:%s" % (self.b, self.c), sql=True)
        assert "CREATE TABLE alembic_version" not in buf.getvalue()
        assert "UPDATE alembic_version" in buf.getvalue()
        assert "CREATE STEP 1" not in buf.getvalue()
        assert "CREATE STEP 2" not in buf.getvalue()
        assert "CREATE STEP 3" in buf.getvalue()

    def test_version_to_none(self):
        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, "%s:base" % self.c, sql=True)
        assert "CREATE TABLE alembic_version" not in buf.getvalue()
        assert "INSERT INTO alembic_version" not in buf.getvalue()
        assert "DROP TABLE alembic_version" in buf.getvalue()
        assert "DROP STEP 3" in buf.getvalue()
        assert "DROP STEP 2" in buf.getvalue()
        assert "DROP STEP 1" in buf.getvalue()

    def test_version_to_middle(self):
        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, "%s:%s" % (self.c, self.a), sql=True)
        assert "CREATE TABLE alembic_version" not in buf.getvalue()
        assert "INSERT INTO alembic_version" not in buf.getvalue()
        assert "DROP TABLE alembic_version" not in buf.getvalue()
        assert "DROP STEP 3" in buf.getvalue()
        assert "DROP STEP 2" in buf.getvalue()
        assert "DROP STEP 1" not in buf.getvalue()

    def test_sql_stamp_from_rev(self):
        with capture_context_buffer() as buf:
            command.stamp(self.cfg, "%s:head" % self.a, sql=True)
        assert (
            "UPDATE alembic_version "
            "SET version_num='%s' "
            "WHERE alembic_version.version_num = '%s';" % (self.c, self.a)
        ) in buf.getvalue()

    def test_sql_stamp_from_partial_rev(self):
        with capture_context_buffer() as buf:
            command.stamp(self.cfg, "%s:head" % self.a[0:7], sql=True)
        assert (
            "UPDATE alembic_version "
            "SET version_num='%s' "
            "WHERE alembic_version.version_num = '%s';" % (self.c, self.a)
        ) in buf.getvalue()


class LiveStampTest(TestBase):
    __only_on__ = 'sqlite'

    def setUp(self):
        self.bind = _sqlite_file_db()
        self.env = staging_env()
        self.cfg = _sqlite_testing_config()
        self.a = a = util.rev_id()
        self.b = b = util.rev_id()
        script = ScriptDirectory.from_config(self.cfg)
        script.generate_revision(a, None, refresh=True)
        write_script(script, a, """
revision = '%s'
down_revision = None
""" % a)
        script.generate_revision(b, None, refresh=True)
        write_script(script, b, """
revision = '%s'
down_revision = '%s'
""" % (b, a))

    def tearDown(self):
        clear_staging_env()

    def test_stamp_creates_table(self):
        command.stamp(self.cfg, "head")
        eq_(
            self.bind.scalar("select version_num from alembic_version"),
            self.b
        )

    def test_stamp_existing_upgrade(self):
        command.stamp(self.cfg, self.a)
        command.stamp(self.cfg, self.b)
        eq_(
            self.bind.scalar("select version_num from alembic_version"),
            self.b
        )

    def test_stamp_existing_downgrade(self):
        command.stamp(self.cfg, self.b)
        command.stamp(self.cfg, self.a)
        eq_(
            self.bind.scalar("select version_num from alembic_version"),
            self.a
        )


class EditTest(TestBase):

    @classmethod
    def setup_class(cls):
        cls.env = staging_env()
        cls.cfg = _sqlite_testing_config()
        cls.a, cls.b, cls.c = three_rev_fixture(cls.cfg)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_edit_latest(self):
        expected_call_arg = '%s/scripts/versions/%s_revision_c.py' % (
            EditTest.cfg.config_args['here'],
            EditTest.c
        )

        with patch('alembic.command.editor.edit') as edit:
            command.edit(self.cfg)
            edit.assert_called_with(expected_call_arg)

    def test_edit_with_missing_editor(self):
        with patch('alembic.command.editor.edit') as edit:
            edit.side_effect = OSError('file not found')
            assert_raises_message(
                util.CommandError,
                'file not found',
                command.edit,
                self.cfg)
