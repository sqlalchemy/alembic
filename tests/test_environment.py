#!coding: utf-8
import os
import sys

from alembic import command
from alembic import testing
from alembic import util
from alembic.environment import EnvironmentContext
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.testing import assert_raises
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import is_
from alembic.testing import is_false
from alembic.testing import is_true
from alembic.testing import mock
from alembic.testing.assertions import expect_raises_message
from alembic.testing.env import _get_staging_directory
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import _sqlite_file_db
from alembic.testing.env import _sqlite_testing_config
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.env import write_script
from alembic.testing.fixtures import capture_context_buffer
from alembic.testing.fixtures import TestBase
from alembic.util import compat


class EnvironmentTest(TestBase):
    def setUp(self):
        staging_env()
        self.cfg = _no_sql_testing_config()

    def tearDown(self):
        clear_staging_env()

    def _fixture(self, **kw):
        script = ScriptDirectory.from_config(self.cfg)
        env = EnvironmentContext(self.cfg, script, **kw)
        return env

    def test_x_arg(self):
        env = self._fixture()
        self.cfg.cmd_opts = mock.Mock(x="y=5")
        eq_(env.get_x_argument(), "y=5")

    def test_x_arg_asdict(self):
        env = self._fixture()
        self.cfg.cmd_opts = mock.Mock(x=["y=5"])
        eq_(env.get_x_argument(as_dictionary=True), {"y": "5"})

    def test_x_arg_no_opts(self):
        env = self._fixture()
        eq_(env.get_x_argument(), [])

    def test_x_arg_no_opts_asdict(self):
        env = self._fixture()
        eq_(env.get_x_argument(as_dictionary=True), {})

    def test_tag_arg(self):
        env = self._fixture(tag="x")
        eq_(env.get_tag_argument(), "x")

    def test_migration_context_has_config(self):
        env = self._fixture()
        env.configure(url="sqlite://")
        ctx = env._migration_context
        is_(ctx.config, self.cfg)

        ctx = MigrationContext(ctx.dialect, None, {})
        is_(ctx.config, None)

    def test_sql_mode_parameters(self):
        env = self._fixture()

        a_rev = "arev"
        env.script.generate_revision(a_rev, "revision a", refresh=True)
        write_script(
            env.script,
            a_rev,
            """\
"Rev A"
revision = '{}'
down_revision = None

from alembic import op

def upgrade():
    op.execute('''
        do some SQL thing with a % percent sign %
    ''')

""".format(
                a_rev
            ),
        )
        with capture_context_buffer(transactional_ddl=True) as buf:
            command.upgrade(self.cfg, "arev", sql=True)
        assert "do some SQL thing with a % percent sign %" in buf.getvalue()

    @config.requirements.legacy_engine
    @testing.uses_deprecated(
        r"The Engine.execute\(\) function/method is considered legacy"
    )
    def test_error_on_passing_engine(self):
        env = self._fixture()

        engine = _sqlite_file_db()

        a_rev = "arev"
        env.script.generate_revision(a_rev, "revision a", refresh=True)
        write_script(
            env.script,
            a_rev,
            """\
"Rev A"
revision = '%s'
down_revision = None

from alembic import op


def upgrade():
    pass


def downgrade():
    pass

"""
            % a_rev,
        )
        migration_fn = mock.MagicMock()

        def upgrade(rev, context):
            migration_fn(rev, context)
            return env.script._upgrade_revs(a_rev, rev)

        with expect_raises_message(
            util.CommandError,
            r"'connection' argument to configure\(\) is "
            r"expected to be a sqlalchemy.engine.Connection ",
        ):
            env.configure(
                connection=engine, fn=upgrade, transactional_ddl=False
            )


class CWDTest(TestBase):
    def setUp(self):
        self.env = staging_env()
        self.cfg = _sqlite_testing_config()

    def tearDown(self):
        clear_staging_env()

    @testing.combinations(
        (
            ".",
            ["."],
        ),
        ("/tmp/foo:/tmp/bar", ["/tmp/foo", "/tmp/bar"]),
        ("/tmp/foo /tmp/bar", ["/tmp/foo", "/tmp/bar"]),
        ("/tmp/foo,/tmp/bar", ["/tmp/foo", "/tmp/bar"]),
        (". /tmp/foo", [".", "/tmp/foo"]),
    )
    def test_sys_path_prepend(self, config_value, expected):
        self.cfg.set_main_option("prepend_sys_path", config_value)

        script = ScriptDirectory.from_config(self.cfg)
        env = EnvironmentContext(self.cfg, script)

        target = os.path.abspath(_get_staging_directory())

        def assert_(heads, context):
            eq_(
                [os.path.abspath(p) for p in sys.path[0 : len(expected)]],
                [os.path.abspath(p) for p in expected],
            )
            return []

        p = [p for p in sys.path if os.path.abspath(p) != target]
        with mock.patch.object(sys, "path", p):
            env.configure(url="sqlite://", fn=assert_)
            with env:
                script.run_env()


class MigrationTransactionTest(TestBase):
    __backend__ = True

    conn = None

    def _fixture(self, opts):
        self.conn = conn = config.db.connect()

        if opts.get("as_sql", False):
            self.context = MigrationContext.configure(
                dialect=conn.dialect, opts=opts
            )
            self.context.output_buffer = (
                self.context.impl.output_buffer
            ) = compat.StringIO()
        else:
            self.context = MigrationContext.configure(
                connection=conn, opts=opts
            )
        return self.context

    def teardown(self):
        if self.conn:
            self.conn.close()

    def test_proxy_transaction_rollback(self):
        context = self._fixture(
            {"transaction_per_migration": True, "transactional_ddl": True}
        )

        is_false(self.conn.in_transaction())
        proxy = context.begin_transaction(_per_migration=True)
        is_true(self.conn.in_transaction())
        proxy.rollback()
        is_false(self.conn.in_transaction())

    def test_proxy_transaction_commit(self):
        context = self._fixture(
            {"transaction_per_migration": True, "transactional_ddl": True}
        )
        proxy = context.begin_transaction(_per_migration=True)
        is_true(self.conn.in_transaction())
        proxy.commit()
        is_false(self.conn.in_transaction())

    def test_proxy_transaction_contextmanager_commit(self):
        context = self._fixture(
            {"transaction_per_migration": True, "transactional_ddl": True}
        )
        proxy = context.begin_transaction(_per_migration=True)
        is_true(self.conn.in_transaction())
        with proxy:
            pass
        is_false(self.conn.in_transaction())

    def test_proxy_transaction_contextmanager_rollback(self):
        context = self._fixture(
            {"transaction_per_migration": True, "transactional_ddl": True}
        )
        proxy = context.begin_transaction(_per_migration=True)
        is_true(self.conn.in_transaction())

        def go():
            with proxy:
                raise Exception("hi")

        assert_raises(Exception, go)
        is_false(self.conn.in_transaction())

    def test_transaction_per_migration_transactional_ddl(self):
        context = self._fixture(
            {"transaction_per_migration": True, "transactional_ddl": True}
        )

        is_false(self.conn.in_transaction())

        with context.begin_transaction():
            is_false(self.conn.in_transaction())
            with context.begin_transaction(_per_migration=True):
                is_true(self.conn.in_transaction())

            is_false(self.conn.in_transaction())
        is_false(self.conn.in_transaction())

    def test_transaction_per_migration_non_transactional_ddl(self):
        context = self._fixture(
            {"transaction_per_migration": True, "transactional_ddl": False}
        )

        is_false(self.conn.in_transaction())

        with context.begin_transaction():
            is_false(self.conn.in_transaction())
            with context.begin_transaction(_per_migration=True):
                is_true(self.conn.in_transaction())

            is_false(self.conn.in_transaction())
        is_false(self.conn.in_transaction())

    def test_transaction_per_all_transactional_ddl(self):
        context = self._fixture({"transactional_ddl": True})

        is_false(self.conn.in_transaction())

        with context.begin_transaction():
            is_true(self.conn.in_transaction())
            with context.begin_transaction(_per_migration=True):
                is_true(self.conn.in_transaction())

            is_true(self.conn.in_transaction())
        is_false(self.conn.in_transaction())

    def test_transaction_per_all_non_transactional_ddl(self):
        context = self._fixture({"transactional_ddl": False})

        is_false(self.conn.in_transaction())

        with context.begin_transaction():
            is_false(self.conn.in_transaction())
            with context.begin_transaction(_per_migration=True):
                is_true(self.conn.in_transaction())

            is_false(self.conn.in_transaction())
        is_false(self.conn.in_transaction())

    def test_transaction_per_all_sqlmode(self):
        context = self._fixture({"as_sql": True})

        context.execute("step 1")
        with context.begin_transaction():
            context.execute("step 2")
            with context.begin_transaction(_per_migration=True):
                context.execute("step 3")

            context.execute("step 4")
        context.execute("step 5")

        if context.impl.transactional_ddl:
            self._assert_impl_steps(
                "step 1",
                "BEGIN",
                "step 2",
                "step 3",
                "step 4",
                "COMMIT",
                "step 5",
            )
        else:
            self._assert_impl_steps(
                "step 1", "step 2", "step 3", "step 4", "step 5"
            )

    def test_transaction_per_migration_sqlmode(self):
        context = self._fixture(
            {"as_sql": True, "transaction_per_migration": True}
        )

        context.execute("step 1")
        with context.begin_transaction():
            context.execute("step 2")
            with context.begin_transaction(_per_migration=True):
                context.execute("step 3")

            context.execute("step 4")
        context.execute("step 5")

        if context.impl.transactional_ddl:
            self._assert_impl_steps(
                "step 1",
                "step 2",
                "BEGIN",
                "step 3",
                "COMMIT",
                "step 4",
                "step 5",
            )
        else:
            self._assert_impl_steps(
                "step 1", "step 2", "step 3", "step 4", "step 5"
            )

    @config.requirements.autocommit_isolation
    def test_autocommit_block(self):
        context = self._fixture({"transaction_per_migration": True})

        is_false(self.conn.in_transaction())

        with context.begin_transaction():
            is_false(self.conn.in_transaction())
            with context.begin_transaction(_per_migration=True):
                is_true(self.conn.in_transaction())

                with context.autocommit_block():
                    is_false(self.conn.in_transaction())

                is_true(self.conn.in_transaction())

            is_false(self.conn.in_transaction())
        is_false(self.conn.in_transaction())

    @config.requirements.autocommit_isolation
    def test_autocommit_block_no_transaction(self):
        context = self._fixture({"transaction_per_migration": True})

        is_false(self.conn.in_transaction())

        with context.autocommit_block():
            is_false(self.conn.in_transaction())
        is_false(self.conn.in_transaction())

    def test_autocommit_block_transactional_ddl_sqlmode(self):
        context = self._fixture(
            {
                "transaction_per_migration": True,
                "transactional_ddl": True,
                "as_sql": True,
            }
        )

        with context.begin_transaction():
            context.execute("step 1")
            with context.begin_transaction(_per_migration=True):
                context.execute("step 2")

                with context.autocommit_block():
                    context.execute("step 3")

                context.execute("step 4")

            context.execute("step 5")

        self._assert_impl_steps(
            "step 1",
            "BEGIN",
            "step 2",
            "COMMIT",
            "step 3",
            "BEGIN",
            "step 4",
            "COMMIT",
            "step 5",
        )

    def test_autocommit_block_nontransactional_ddl_sqlmode(self):
        context = self._fixture(
            {
                "transaction_per_migration": True,
                "transactional_ddl": False,
                "as_sql": True,
            }
        )

        with context.begin_transaction():
            context.execute("step 1")
            with context.begin_transaction(_per_migration=True):
                context.execute("step 2")

                with context.autocommit_block():
                    context.execute("step 3")

                context.execute("step 4")

            context.execute("step 5")

        self._assert_impl_steps(
            "step 1", "step 2", "step 3", "step 4", "step 5"
        )

    def _assert_impl_steps(self, *steps):
        to_check = self.context.output_buffer.getvalue()

        self.context.impl.output_buffer = buf = compat.StringIO()
        for step in steps:
            if step == "BEGIN":
                self.context.impl.emit_begin()
            elif step == "COMMIT":
                self.context.impl.emit_commit()
            else:
                self.context.impl._exec(step)

        eq_(to_check, buf.getvalue())
