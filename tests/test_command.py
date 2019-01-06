from contextlib import contextmanager
from io import BytesIO
from io import TextIOWrapper
import re

from sqlalchemy import exc as sqla_exc

from alembic import command
from alembic import config
from alembic import util
from alembic.script import ScriptDirectory
from alembic.testing import assert_raises
from alembic.testing import assert_raises_message
from alembic.testing import eq_
from alembic.testing import mock
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import _sqlite_file_db
from alembic.testing.env import _sqlite_testing_config
from alembic.testing.env import clear_staging_env
from alembic.testing.env import env_file_fixture
from alembic.testing.env import staging_env
from alembic.testing.env import three_rev_fixture
from alembic.testing.env import write_script
from alembic.testing.fixtures import capture_context_buffer
from alembic.testing.fixtures import TestBase


class _BufMixin(object):
    def _buf_fixture(self):
        # try to simulate how sys.stdout looks - we send it u''
        # but then it's trying to encode to something.
        buf = BytesIO()
        wrapper = TextIOWrapper(buf, encoding="ascii", line_buffering=True)
        wrapper.getvalue = buf.getvalue
        return wrapper


class HistoryTest(_BufMixin, TestBase):
    @classmethod
    def setup_class(cls):
        cls.env = staging_env()
        cls.cfg = _sqlite_testing_config()
        cls.a, cls.b, cls.c = three_rev_fixture(cls.cfg)
        cls._setup_env_file()

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def teardown(self):
        self.cfg.set_main_option("revision_environment", "false")

    @classmethod
    def _setup_env_file(self):
        env_file_fixture(
            r"""

from sqlalchemy import MetaData, engine_from_config
target_metadata = MetaData()

engine = engine_from_config(
    config.get_section(config.config_ini_section),
    prefix='sqlalchemy.')

connection = engine.connect()

context.configure(
    connection=connection, target_metadata=target_metadata
)

try:
    with context.begin_transaction():
        config.stdout.write(u"environment included OK\n")
        context.run_migrations()
finally:
    connection.close()

"""
        )

    def _eq_cmd_output(self, buf, expected, env_token=False, currents=()):
        script = ScriptDirectory.from_config(self.cfg)

        # test default encode/decode behavior as well,
        # rev B has a non-ascii char in it + a coding header.

        assert_lines = []
        for _id in expected:
            rev = script.get_revision(_id)
            if _id in currents:
                rev._db_current_indicator = True
            assert_lines.append(rev.log_entry)

        if env_token:
            assert_lines.insert(0, "environment included OK")

        eq_(
            buf.getvalue().decode("ascii", "replace").strip(),
            "\n".join(assert_lines)
            .encode("ascii", "replace")
            .decode("ascii")
            .strip(),
        )

    def test_history_full(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b, self.a])

    def test_history_full_environment(self):
        self.cfg.stdout = buf = self._buf_fixture()
        self.cfg.set_main_option("revision_environment", "true")
        command.history(self.cfg, verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b, self.a], env_token=True)

    def test_history_num_range(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "%s:%s" % (self.a, self.b), verbose=True)
        self._eq_cmd_output(buf, [self.b, self.a])

    def test_history_num_range_environment(self):
        self.cfg.stdout = buf = self._buf_fixture()
        self.cfg.set_main_option("revision_environment", "true")
        command.history(self.cfg, "%s:%s" % (self.a, self.b), verbose=True)
        self._eq_cmd_output(buf, [self.b, self.a], env_token=True)

    def test_history_base_to_num(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, ":%s" % (self.b), verbose=True)
        self._eq_cmd_output(buf, [self.b, self.a])

    def test_history_num_to_head(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "%s:" % (self.a), verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b, self.a])

    def test_history_num_to_head_environment(self):
        self.cfg.stdout = buf = self._buf_fixture()
        self.cfg.set_main_option("revision_environment", "true")
        command.history(self.cfg, "%s:" % (self.a), verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b, self.a], env_token=True)

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
        self._eq_cmd_output(buf, [self.c, self.b], env_token=True)

    def test_history_current_to_head_as_base(self):
        command.stamp(self.cfg, "base")
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "current:", verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b, self.a], env_token=True)

    def test_history_include_env(self):
        self.cfg.stdout = buf = self._buf_fixture()
        self.cfg.set_main_option("revision_environment", "true")
        command.history(self.cfg, verbose=True)
        self._eq_cmd_output(buf, [self.c, self.b, self.a], env_token=True)

    def test_history_indicate_current(self):
        command.stamp(self.cfg, (self.b,))
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, indicate_current=True, verbose=True)
        self._eq_cmd_output(
            buf, [self.c, self.b, self.a], currents=(self.b,), env_token=True
        )


class CurrentTest(_BufMixin, TestBase):
    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.cfg = _sqlite_testing_config()
        cls.a1 = env.generate_revision("a1", "a1")
        cls.a2 = env.generate_revision("a2", "a2")
        cls.a3 = env.generate_revision("a3", "a3")
        cls.b1 = env.generate_revision("b1", "b1", head="base")
        cls.b2 = env.generate_revision("b2", "b2", head="b1", depends_on="a2")
        cls.b3 = env.generate_revision("b3", "b3", head="b2")

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    @contextmanager
    def _assert_lines(self, revs):
        self.cfg.stdout = buf = self._buf_fixture()

        yield

        lines = set(
            [
                re.match(r"(^.\w)", elem).group(1)
                for elem in re.split(
                    "\n", buf.getvalue().decode("ascii", "replace").strip()
                )
                if elem
            ]
        )

        eq_(lines, set(revs))

    def test_no_current(self):
        command.stamp(self.cfg, ())
        with self._assert_lines([]):
            command.current(self.cfg)

    def test_plain_current(self):
        command.stamp(self.cfg, ())
        command.stamp(self.cfg, self.a3.revision)
        with self._assert_lines(["a3"]):
            command.current(self.cfg)

    def test_two_heads(self):
        command.stamp(self.cfg, ())
        command.stamp(self.cfg, (self.a1.revision, self.b1.revision))
        with self._assert_lines(["a1", "b1"]):
            command.current(self.cfg)

    def test_heads_one_is_dependent(self):
        command.stamp(self.cfg, ())
        command.stamp(self.cfg, (self.b2.revision,))
        with self._assert_lines(["a2", "b2"]):
            command.current(self.cfg)

    def test_heads_upg(self):
        command.stamp(self.cfg, (self.b2.revision,))
        command.upgrade(self.cfg, (self.b3.revision))
        with self._assert_lines(["a2", "b3"]):
            command.current(self.cfg)


class RevisionTest(TestBase):
    def setUp(self):
        self.env = staging_env()
        self.cfg = _sqlite_testing_config()

    def tearDown(self):
        clear_staging_env()

    def _env_fixture(self, version_table_pk=True):
        env_file_fixture(
            """

from sqlalchemy import MetaData, engine_from_config
target_metadata = MetaData()

engine = engine_from_config(
    config.get_section(config.config_ini_section),
    prefix='sqlalchemy.')

connection = engine.connect()

context.configure(
    connection=connection, target_metadata=target_metadata,
    version_table_pk=%r
)

try:
    with context.begin_transaction():
        context.run_migrations()
finally:
    connection.close()

"""
            % (version_table_pk,)
        )

    def test_create_rev_plain_db_not_up_to_date(self):
        self._env_fixture()
        command.revision(self.cfg)
        command.revision(self.cfg)  # no problem

    def test_create_rev_autogen(self):
        self._env_fixture()
        command.revision(self.cfg, autogenerate=True)

    def test_create_rev_autogen_db_not_up_to_date(self):
        self._env_fixture()
        assert command.revision(self.cfg)
        assert_raises_message(
            util.CommandError,
            "Target database is not up to date.",
            command.revision,
            self.cfg,
            autogenerate=True,
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
            command.revision,
            self.cfg,
            autogenerate=True,
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
            command.revision,
            self.cfg,
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
            command.revision,
            self.cfg,
            autogenerate=True,
        )

    def test_pk_constraint_normally_prevents_dupe_rows(self):
        self._env_fixture()
        command.revision(self.cfg)
        r2 = command.revision(self.cfg)
        db = _sqlite_file_db()
        command.upgrade(self.cfg, "head")
        assert_raises(
            sqla_exc.IntegrityError,
            db.execute,
            "insert into alembic_version values ('%s')" % r2.revision,
        )

    def test_err_correctly_raised_on_dupe_rows_no_pk(self):
        self._env_fixture(version_table_pk=False)
        command.revision(self.cfg)
        r2 = command.revision(self.cfg)
        db = _sqlite_file_db()
        command.upgrade(self.cfg, "head")
        db.execute("insert into alembic_version values ('%s')" % r2.revision)
        assert_raises_message(
            util.CommandError,
            "Online migration expected to match one row when "
            "updating .* in 'alembic_version'; 2 found",
            command.downgrade,
            self.cfg,
            "-1",
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
            command.revision,
            self.cfg,
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

    def test_create_rev_depends_on(self):
        self._env_fixture()
        command.revision(self.cfg)
        rev2 = command.revision(self.cfg)
        rev3 = command.revision(self.cfg, depends_on=rev2.revision)
        eq_(rev3._resolved_dependencies, (rev2.revision,))

        rev4 = command.revision(
            self.cfg, depends_on=[rev2.revision, rev3.revision]
        )
        eq_(rev4._resolved_dependencies, (rev2.revision, rev3.revision))

    def test_create_rev_depends_on_branch_label(self):
        self._env_fixture()
        command.revision(self.cfg)
        rev2 = command.revision(self.cfg, branch_label="foobar")
        rev3 = command.revision(self.cfg, depends_on="foobar")
        eq_(rev3.dependencies, "foobar")
        eq_(rev3._resolved_dependencies, (rev2.revision,))

    def test_create_rev_depends_on_partial_revid(self):
        self._env_fixture()
        command.revision(self.cfg)
        rev2 = command.revision(self.cfg)
        assert len(rev2.revision) > 7
        rev3 = command.revision(self.cfg, depends_on=rev2.revision[0:4])
        eq_(rev3.dependencies, rev2.revision)
        eq_(rev3._resolved_dependencies, (rev2.revision,))

    def test_create_rev_invalid_depends_on(self):
        self._env_fixture()
        command.revision(self.cfg)
        assert_raises_message(
            util.CommandError,
            "Can't locate revision identified by 'invalid'",
            command.revision,
            self.cfg,
            depends_on="invalid",
        )

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
            command.revision,
            self.cfg,
            autogenerate=True,
        )

    def test_nonsensical_sql_mode_autogen(self):
        self._env_fixture()
        assert_raises_message(
            util.CommandError,
            "Using --sql with --autogenerate does not make any sense",
            command.revision,
            self.cfg,
            autogenerate=True,
            sql=True,
        )

    def test_nonsensical_sql_no_env(self):
        self._env_fixture()
        assert_raises_message(
            util.CommandError,
            "Using --sql with the revision command when revision_environment "
            "is not configured does not make any sense",
            command.revision,
            self.cfg,
            sql=True,
        )

    def test_sensical_sql_w_env(self):
        self._env_fixture()
        self.cfg.set_main_option("revision_environment", "true")
        command.revision(self.cfg, sql=True)


class UpgradeDowngradeStampTest(TestBase):
    def setUp(self):
        self.env = staging_env()
        self.cfg = cfg = _no_sql_testing_config()
        cfg.set_main_option("dialect_name", "sqlite")
        cfg.remove_main_option("url")

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

    def test_none_to_head_sql(self):
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, "head", sql=True)
        assert "CREATE TABLE alembic_version" in buf.getvalue()
        assert "UPDATE alembic_version" in buf.getvalue()
        assert "CREATE STEP 1" in buf.getvalue()
        assert "CREATE STEP 2" in buf.getvalue()
        assert "CREATE STEP 3" in buf.getvalue()

    def test_base_to_head_sql(self):
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, "base:head", sql=True)
        assert "CREATE TABLE alembic_version" in buf.getvalue()
        assert "UPDATE alembic_version" in buf.getvalue()
        assert "CREATE STEP 1" in buf.getvalue()
        assert "CREATE STEP 2" in buf.getvalue()
        assert "CREATE STEP 3" in buf.getvalue()

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
    __only_on__ = "sqlite"

    def setUp(self):
        self.bind = _sqlite_file_db()
        self.env = staging_env()
        self.cfg = _sqlite_testing_config()
        self.a = a = util.rev_id()
        self.b = b = util.rev_id()
        script = ScriptDirectory.from_config(self.cfg)
        script.generate_revision(a, None, refresh=True)
        write_script(
            script,
            a,
            """
revision = '%s'
down_revision = None
"""
            % a,
        )
        script.generate_revision(b, None, refresh=True)
        write_script(
            script,
            b,
            """
revision = '%s'
down_revision = '%s'
"""
            % (b, a),
        )

    def tearDown(self):
        clear_staging_env()

    def test_stamp_creates_table(self):
        command.stamp(self.cfg, "head")
        eq_(
            self.bind.scalar("select version_num from alembic_version"), self.b
        )

    def test_stamp_existing_upgrade(self):
        command.stamp(self.cfg, self.a)
        command.stamp(self.cfg, self.b)
        eq_(
            self.bind.scalar("select version_num from alembic_version"), self.b
        )

    def test_stamp_existing_downgrade(self):
        command.stamp(self.cfg, self.b)
        command.stamp(self.cfg, self.a)
        eq_(
            self.bind.scalar("select version_num from alembic_version"), self.a
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

    def setUp(self):
        command.stamp(self.cfg, "base")

    def test_edit_head(self):
        expected_call_arg = "%s/scripts/versions/%s_revision_c.py" % (
            EditTest.cfg.config_args["here"],
            EditTest.c,
        )

        with mock.patch("alembic.util.edit") as edit:
            command.edit(self.cfg, "head")
            edit.assert_called_with(expected_call_arg)

    def test_edit_b(self):
        expected_call_arg = "%s/scripts/versions/%s_revision_b.py" % (
            EditTest.cfg.config_args["here"],
            EditTest.b,
        )

        with mock.patch("alembic.util.edit") as edit:
            command.edit(self.cfg, self.b[0:3])
            edit.assert_called_with(expected_call_arg)

    def test_edit_with_missing_editor(self):
        with mock.patch("editor.edit") as edit_mock:
            edit_mock.side_effect = OSError("file not found")
            assert_raises_message(
                util.CommandError,
                "file not found",
                util.edit,
                "/not/a/file.txt",
            )

    def test_edit_no_revs(self):
        assert_raises_message(
            util.CommandError,
            "No revision files indicated by symbol 'base'",
            command.edit,
            self.cfg,
            "base",
        )

    def test_edit_no_current(self):
        assert_raises_message(
            util.CommandError,
            "No current revisions",
            command.edit,
            self.cfg,
            "current",
        )

    def test_edit_current(self):
        expected_call_arg = "%s/scripts/versions/%s_revision_b.py" % (
            EditTest.cfg.config_args["here"],
            EditTest.b,
        )

        command.stamp(self.cfg, self.b)
        with mock.patch("alembic.util.edit") as edit:
            command.edit(self.cfg, "current")
            edit.assert_called_with(expected_call_arg)


class CommandLineTest(TestBase):
    @classmethod
    def setup_class(cls):
        cls.env = staging_env()
        cls.cfg = _sqlite_testing_config()
        cls.a, cls.b, cls.c = three_rev_fixture(cls.cfg)

    def test_run_cmd_args_missing(self):
        canary = mock.Mock()

        orig_revision = command.revision

        # the command function has "process_revision_directives"
        # however the ArgumentParser does not.  ensure things work
        def revision(
            config,
            message=None,
            autogenerate=False,
            sql=False,
            head="head",
            splice=False,
            branch_label=None,
            version_path=None,
            rev_id=None,
            depends_on=None,
            process_revision_directives=None,
        ):
            canary(config, message=message)

        revision.__module__ = "alembic.command"

        # CommandLine() pulls the function into the ArgumentParser
        # and needs the full signature, so we can't patch the "revision"
        # command normally as ArgumentParser gives us no way to get to it.
        config.command.revision = revision
        try:
            commandline = config.CommandLine()
            options = commandline.parser.parse_args(["revision", "-m", "foo"])
            commandline.run_cmd(self.cfg, options)
        finally:
            config.command.revision = orig_revision
        eq_(canary.mock_calls, [mock.call(self.cfg, message="foo")])
