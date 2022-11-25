import os
import sys

from alembic import command
from alembic import testing
from alembic import util
from alembic.environment import EnvironmentContext
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import is_
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
