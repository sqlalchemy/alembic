from contextlib import contextmanager
import inspect
from io import BytesIO
from io import StringIO
from io import TextIOWrapper
import os
import re
from typing import cast

from sqlalchemy import exc as sqla_exc
from sqlalchemy import text
from sqlalchemy import VARCHAR
from sqlalchemy.engine import Engine
from sqlalchemy.sql.schema import Column

from alembic import __version__
from alembic import command
from alembic import config
from alembic import util
from alembic.script import ScriptDirectory
from alembic.testing import assert_raises
from alembic.testing import assert_raises_message
from alembic.testing import eq_
from alembic.testing import is_false
from alembic.testing import is_true
from alembic.testing import mock
from alembic.testing.env import _get_staging_directory
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import _sqlite_file_db
from alembic.testing.env import _sqlite_testing_config
from alembic.testing.env import clear_staging_env
from alembic.testing.env import env_file_fixture
from alembic.testing.env import multi_heads_fixture
from alembic.testing.env import staging_env
from alembic.testing.env import three_rev_fixture
from alembic.testing.env import write_script
from alembic.testing.fixtures import capture_context_buffer
from alembic.testing.fixtures import capture_engine_context_buffer
from alembic.testing.fixtures import TestBase
from alembic.util.sqla_compat import _connectable_has_table


class _BufMixin:
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
    engine.dispose()
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

        actual = (
            buf.getvalue()
            .decode("ascii", "replace")
            .replace(os.linesep, "\n")
            .strip()
        )
        eq_(
            actual,
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
        cls.bind = _sqlite_file_db(scope="class")
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

        lines = {
            re.match(r"(^.\w)", elem).group(1)
            for elem in re.split(
                "\n", buf.getvalue().decode("ascii", "replace").strip()
            )
            if elem
        }

        eq_(lines, set(revs))

    def test_doesnt_create_alembic_version(self):
        command.current(self.cfg)
        engine = self.bind
        with engine.connect() as conn:
            is_false(_connectable_has_table(conn, "alembic_version", None))

    def test_no_current(self):
        command.stamp(self.cfg, ())
        with self._assert_lines([]):
            command.current(self.cfg)

    def test_plain_current(self):
        command.stamp(self.cfg, ())
        command.stamp(self.cfg, self.a3.revision)
        with self._assert_lines(["a3"]):
            command.current(self.cfg)

    def test_current_obfuscate_password(self):
        eq_(
            util.obfuscate_url_pw("postgresql://scott:tiger@localhost/test"),
            "postgresql://scott:***@localhost/test",
        )

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
    engine.dispose()

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
        with db.connect() as conn:
            assert_raises(
                sqla_exc.IntegrityError,
                conn.execute,
                text(
                    "insert into alembic_version values ('%s')" % r2.revision
                ),
            )

    def test_err_correctly_raised_on_dupe_rows_no_pk(self):
        self._env_fixture(version_table_pk=False)
        command.revision(self.cfg)
        r2 = command.revision(self.cfg)
        db = _sqlite_file_db()
        command.upgrade(self.cfg, "head")
        with db.begin() as conn:
            conn.execute(
                text("insert into alembic_version values ('%s')" % r2.revision)
            )
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


class CheckTest(TestBase):
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
    engine.dispose()

"""
            % (version_table_pk,)
        )

    def test_check_no_changes(self):
        self._env_fixture()
        command.check(self.cfg)  # no problem

    def test_check_changes_detected(self):
        self._env_fixture()
        with mock.patch(
            "alembic.operations.ops.UpgradeOps.as_diffs",
            return_value=[
                ("remove_column", None, "foo", Column("old_data", VARCHAR()))
            ],
        ):
            assert_raises_message(
                util.AutogenerateDiffsDetected,
                r"New upgrade operations detected: \[\('remove_column'",
                command.check,
                self.cfg,
            )


class _StampTest:
    def _assert_sql(self, emitted_sql, origin, destinations):
        ins_expr = (
            r"INSERT INTO alembic_version \(version_num\) "
            r"VALUES \('(.+)'\)"
        )
        expected = [ins_expr for elem in destinations]
        if origin:
            expected[0] = (
                "UPDATE alembic_version SET version_num='(.+)' WHERE "
                "alembic_version.version_num = '%s'" % (origin,)
            )
        for line in emitted_sql.split("\n"):
            if not expected:
                assert not re.match(
                    ins_expr, line
                ), "additional inserts were emitted"
            else:
                m = re.match(expected[0], line)
                if m:
                    destinations.remove(m.group(1))
                    expected.pop(0)

        assert not expected, "lines remain"


class StampMultipleRootsTest(TestBase, _StampTest):
    def setUp(self):
        self.env = staging_env()
        # self.cfg = cfg = _no_sql_testing_config()
        self.cfg = cfg = _sqlite_testing_config()
        # cfg.set_main_option("dialect_name", "sqlite")
        # cfg.remove_main_option("url")

        self.a1, self.b1, self.c1 = three_rev_fixture(cfg)
        self.a2, self.b2, self.c2 = three_rev_fixture(cfg)

    def tearDown(self):
        clear_staging_env()

    def test_sql_stamp_heads(self):
        with capture_context_buffer() as buf:
            command.stamp(self.cfg, ["heads"], sql=True)

        self._assert_sql(buf.getvalue(), None, {self.c1, self.c2})

    def test_sql_stamp_single_head(self):
        with capture_context_buffer() as buf:
            command.stamp(self.cfg, ["%s@head" % self.c1], sql=True)

        self._assert_sql(buf.getvalue(), None, {self.c1})


class StampMultipleHeadsTest(TestBase, _StampTest):
    def setUp(self):
        self.env = staging_env()
        # self.cfg = cfg = _no_sql_testing_config()
        self.cfg = cfg = _sqlite_testing_config()
        # cfg.set_main_option("dialect_name", "sqlite")
        # cfg.remove_main_option("url")

        self.a, self.b, self.c = three_rev_fixture(cfg)
        self.d, self.e, self.f = multi_heads_fixture(
            cfg, self.a, self.b, self.c
        )

    def tearDown(self):
        clear_staging_env()

    def test_sql_stamp_heads(self):
        with capture_context_buffer() as buf:
            command.stamp(self.cfg, ["heads"], sql=True)

        self._assert_sql(buf.getvalue(), None, {self.c, self.e, self.f})

    def test_sql_stamp_multi_rev_nonsensical(self):
        with capture_context_buffer() as buf:
            command.stamp(self.cfg, [self.a, self.e, self.f], sql=True)
        # TODO: this shouldn't be possible, because e/f require b as a
        # dependency
        self._assert_sql(buf.getvalue(), None, {self.a, self.e, self.f})

    def test_sql_stamp_multi_rev_from_multi_base_nonsensical(self):
        with capture_context_buffer() as buf:
            command.stamp(
                self.cfg,
                ["base:%s" % self.a, "base:%s" % self.e, "base:%s" % self.f],
                sql=True,
            )

        # TODO: this shouldn't be possible, because e/f require b as a
        # dependency
        self._assert_sql(buf.getvalue(), None, {self.a, self.e, self.f})

    def test_online_stamp_multi_rev_nonsensical(self):
        with capture_engine_context_buffer() as buf:
            command.stamp(self.cfg, [self.a, self.e, self.f])

        # TODO: this shouldn't be possible, because e/f require b as a
        # dependency
        self._assert_sql(buf.getvalue(), None, {self.a, self.e, self.f})

    def test_online_stamp_multi_rev_from_real_ancestor(self):
        command.stamp(self.cfg, [self.a])
        with capture_engine_context_buffer() as buf:
            command.stamp(self.cfg, [self.e, self.f])

        self._assert_sql(buf.getvalue(), self.a, {self.e, self.f})

    def test_online_stamp_version_already_there(self):
        command.stamp(self.cfg, [self.c, self.e])
        with capture_engine_context_buffer() as buf:
            command.stamp(self.cfg, [self.c, self.e])
        self._assert_sql(buf.getvalue(), None, {})

    def test_sql_stamp_multi_rev_from_multi_start(self):
        with capture_context_buffer() as buf:
            command.stamp(
                self.cfg,
                [
                    "%s:%s" % (self.b, self.c),
                    "%s:%s" % (self.b, self.e),
                    "%s:%s" % (self.b, self.f),
                ],
                sql=True,
            )

        self._assert_sql(buf.getvalue(), self.b, {self.c, self.e, self.f})

    def test_sql_stamp_heads_symbolic(self):
        with capture_context_buffer() as buf:
            command.stamp(self.cfg, ["%s:heads" % self.b], sql=True)

        self._assert_sql(buf.getvalue(), self.b, {self.c, self.e, self.f})

    def test_sql_stamp_different_multi_start(self):
        assert_raises_message(
            util.CommandError,
            "Stamp operation with --sql only supports a single "
            "starting revision at a time",
            command.stamp,
            self.cfg,
            ["%s:%s" % (self.b, self.c), "%s:%s" % (self.a, self.e)],
            sql=True,
        )

    def test_stamp_purge(self):
        command.stamp(self.cfg, [self.a])

        eng = _sqlite_file_db()
        with eng.begin() as conn:
            result = conn.execute(
                text("update alembic_version set version_num='fake'")
            )
            eq_(result.rowcount, 1)

        with capture_engine_context_buffer() as buf:
            command.stamp(self.cfg, [self.a, self.e, self.f], purge=True)

        self._assert_sql(buf.getvalue(), None, {self.a, self.e, self.f})

    def test_stamp_purge_no_sql(self):
        assert_raises_message(
            util.CommandError,
            "Can't use --purge with --sql mode",
            command.stamp,
            self.cfg,
            [self.c],
            sql=True,
            purge=True,
        )


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

    def test_sql_stamp_revision_as_kw(self):
        with capture_context_buffer() as buf:
            command.stamp(self.cfg, revision="head", sql=True)
        assert (
            "INSERT INTO alembic_version (version_num) VALUES ('%s')" % self.c
            in buf.getvalue()
        )

    def test_stamp_argparser_single_rev(self):
        cmd = config.CommandLine()
        options = cmd.parser.parse_args(["stamp", self.c, "--sql"])
        with capture_context_buffer() as buf:
            cmd.run_cmd(self.cfg, options)
        assert (
            "INSERT INTO alembic_version (version_num) VALUES ('%s')" % self.c
            in buf.getvalue()
        )

    def test_stamp_argparser_multiple_rev(self):
        cmd = config.CommandLine()
        options = cmd.parser.parse_args(["stamp", self.b, self.c, "--sql"])
        with capture_context_buffer() as buf:
            cmd.run_cmd(self.cfg, options)
        # TODO: this is still wrong, as this stamp command is putting
        # conflicting heads into the table.   The test here is only to test
        # that the revisions are passed as a list.
        assert (
            "INSERT INTO alembic_version (version_num) VALUES ('%s')" % self.b
            in buf.getvalue()
        )
        assert (
            "INSERT INTO alembic_version (version_num) VALUES ('%s')" % self.c
            in buf.getvalue()
        )


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
        with self.bind.connect() as conn:
            eq_(
                conn.scalar(text("select version_num from alembic_version")),
                self.b,
            )

    def test_stamp_existing_upgrade(self):
        command.stamp(self.cfg, self.a)
        command.stamp(self.cfg, self.b)
        with self.bind.connect() as conn:
            eq_(
                conn.scalar(text("select version_num from alembic_version")),
                self.b,
            )

    def test_stamp_existing_downgrade(self):
        command.stamp(self.cfg, self.b)
        command.stamp(self.cfg, self.a)
        with self.bind.connect() as conn:
            eq_(
                conn.scalar(text("select version_num from alembic_version")),
                self.a,
            )

    def test_stamp_version_already_there(self):
        command.stamp(self.cfg, self.b)
        command.stamp(self.cfg, self.b)

        with self.bind.connect() as conn:
            eq_(
                conn.scalar(text("select version_num from alembic_version")),
                self.b,
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
        expected_call_arg = os.path.normpath(
            "%s/scripts/versions/%s_revision_c.py"
            % (EditTest.cfg.config_args["here"], EditTest.c)
        )

        with mock.patch("alembic.util.open_in_editor") as edit:
            command.edit(self.cfg, "head")
            edit.assert_called_with(expected_call_arg)

    def test_edit_b(self):
        expected_call_arg = os.path.normpath(
            "%s/scripts/versions/%s_revision_b.py"
            % (EditTest.cfg.config_args["here"], EditTest.b)
        )

        with mock.patch("alembic.util.open_in_editor") as edit:
            command.edit(self.cfg, self.b[0:3])
            edit.assert_called_with(expected_call_arg)

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
        expected_call_arg = os.path.normpath(
            "%s/scripts/versions/%s_revision_b.py"
            % (EditTest.cfg.config_args["here"], EditTest.b)
        )

        command.stamp(self.cfg, self.b)
        with mock.patch("alembic.util.open_in_editor") as edit:
            command.edit(self.cfg, "current")
            edit.assert_called_with(expected_call_arg)


class CommandLineTest(TestBase):
    @classmethod
    def setup_class(cls):
        cls.env = staging_env()
        cls.cfg = _sqlite_testing_config()
        cls.a, cls.b, cls.c = three_rev_fixture(cls.cfg)

    def teardown(self):
        os.environ.pop("ALEMBIC_CONFIG", None)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

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

    def test_help_text(self):
        commands = {
            fn.__name__
            for fn in [getattr(command, n) for n in dir(command)]
            if inspect.isfunction(fn)
            and fn.__name__[0] != "_"
            and fn.__module__ == "alembic.command"
        }
        # make sure we found them
        assert commands.intersection(
            {"upgrade", "downgrade", "merge", "revision"}
        )

        # catch help text coming intersection
        with mock.patch("alembic.config.ArgumentParser") as argparse:
            config.CommandLine()
            for kall in argparse().add_subparsers().mock_calls:
                for sub_kall in kall.call_list():
                    if sub_kall[0] == "add_parser":
                        cmdname = sub_kall[1][0]
                        help_text = sub_kall[2]["help"]
                        if help_text:
                            commands.remove(cmdname)
                            # more than two spaces
                            assert not re.search(r"   ", help_text)

                            # no markup stuff
                            assert ":" not in help_text

                            # no newlines
                            assert "\n" not in help_text

                            # ends with a period
                            assert help_text.endswith(".")

                            # not too long
                            assert len(help_text) < 80
        assert not commands, "Commands without help text: %s" % commands

    def test_init_file_exists_and_is_not_empty(self):
        with mock.patch(
            "alembic.command.os.listdir", return_value=["file1", "file2"]
        ), mock.patch("alembic.command.os.access", return_value=True):
            directory = "alembic"
            assert_raises_message(
                util.CommandError,
                "Directory %s already exists and is not empty" % directory,
                command.init,
                self.cfg,
                directory=directory,
            )

    def test_config_file_default(self):
        cl = config.CommandLine()
        with mock.patch.object(cl, "run_cmd") as run_cmd:
            cl.main(argv=["list_templates"])

        cfg = run_cmd.mock_calls[0][1][0]
        eq_(cfg.config_file_name, "alembic.ini")

    def test_config_file_c_override(self):
        cl = config.CommandLine()
        with mock.patch.object(cl, "run_cmd") as run_cmd:
            cl.main(argv=["-c", "myconf.ini", "list_templates"])

        cfg = run_cmd.mock_calls[0][1][0]
        eq_(cfg.config_file_name, "myconf.ini")

    def test_config_file_env_variable(self):
        os.environ["ALEMBIC_CONFIG"] = "/foo/bar/bat.conf"
        cl = config.CommandLine()
        with mock.patch.object(cl, "run_cmd") as run_cmd:
            cl.main(argv=["list_templates"])

        cfg = run_cmd.mock_calls[0][1][0]
        eq_(cfg.config_file_name, "/foo/bar/bat.conf")

    def test_config_file_env_variable_c_override(self):
        os.environ["ALEMBIC_CONFIG"] = "/foo/bar/bat.conf"
        cl = config.CommandLine()
        with mock.patch.object(cl, "run_cmd") as run_cmd:
            cl.main(argv=["-c", "myconf.conf", "list_templates"])

        cfg = run_cmd.mock_calls[0][1][0]
        eq_(cfg.config_file_name, "myconf.conf")

    def test_init_file_exists_and_is_empty(self):
        def access_(path, mode):
            if "generic" in path or path == "foobar":
                return True
            else:
                return False

        def listdir_(path):
            if path == "foobar":
                return []
            else:
                return ["file1", "file2", "alembic.ini.mako"]

        with mock.patch(
            "alembic.command.os.access", side_effect=access_
        ), mock.patch("alembic.command.os.makedirs") as makedirs, mock.patch(
            "alembic.command.os.listdir", side_effect=listdir_
        ), mock.patch(
            "alembic.command.ScriptDirectory"
        ):
            command.init(self.cfg, directory="foobar")
            eq_(
                makedirs.mock_calls,
                [mock.call(os.path.normpath("foobar/versions"))],
            )

    def test_init_file_doesnt_exist(self):
        def access_(path, mode):
            if "generic" in path:
                return True
            else:
                return False

        with mock.patch(
            "alembic.command.os.access", side_effect=access_
        ), mock.patch("alembic.command.os.makedirs") as makedirs, mock.patch(
            "alembic.command.ScriptDirectory"
        ):
            command.init(self.cfg, directory="foobar")
            eq_(
                makedirs.mock_calls,
                [
                    mock.call("foobar"),
                    mock.call(os.path.normpath("foobar/versions")),
                ],
            )

    def test_init_w_package(self):

        path = os.path.join(_get_staging_directory(), "foobar")

        with mock.patch("alembic.command.open") as open_:
            command.init(self.cfg, directory=path, package=True)
            eq_(
                open_.mock_calls,
                [
                    mock.call(
                        os.path.abspath(os.path.join(path, "__init__.py")), "w"
                    ),
                    mock.call().close(),
                    mock.call(
                        os.path.abspath(
                            os.path.join(path, "versions", "__init__.py")
                        ),
                        "w",
                    ),
                    mock.call().close(),
                ],
            )

    def test_version_text(self):
        buf = StringIO()
        to_mock = "sys.stdout"

        with mock.patch(to_mock, buf):
            try:
                config.CommandLine(prog="test_prog").main(argv=["--version"])
                assert False
            except SystemExit:
                pass

        is_true("test_prog" in str(buf.getvalue()))
        is_true(__version__ in str(buf.getvalue()))


class EnureVersionTest(TestBase):
    @classmethod
    def setup_class(cls):
        cls.bind = _sqlite_file_db(scope="class")
        cls.env = staging_env()
        cls.cfg = _sqlite_testing_config()

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_ensure_version(self):
        command.ensure_version(self.cfg)

        engine = cast(Engine, self.bind)
        with engine.connect() as conn:
            is_true(_connectable_has_table(conn, "alembic_version", None))

    def test_ensure_version_called_twice(self):
        command.ensure_version(self.cfg)
        command.ensure_version(self.cfg)

        engine = cast(Engine, self.bind)
        with engine.connect() as conn:
            is_true(_connectable_has_table(conn, "alembic_version", None))

    def test_sql_ensure_version(self):
        with capture_context_buffer() as buf:
            command.ensure_version(self.cfg, sql=True)

        is_true(buf.getvalue().startswith("CREATE TABLE alembic_version"))
