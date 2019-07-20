#!coding: utf-8
from alembic import command
from alembic.environment import EnvironmentContext
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import is_
from alembic.testing.assertions import expect_warnings
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import _sqlite_file_db
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.env import write_script
from alembic.testing.fixtures import capture_context_buffer
from alembic.testing.fixtures import TestBase
from alembic.testing.mock import call
from alembic.testing.mock import MagicMock
from alembic.testing.mock import Mock


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
        self.cfg.cmd_opts = Mock(x="y=5")
        eq_(env.get_x_argument(), "y=5")

    def test_x_arg_asdict(self):
        env = self._fixture()
        self.cfg.cmd_opts = Mock(x=["y=5"])
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

    @config.requirements.sqlalchemy_issue_3740
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

    def test_warning_on_passing_engine(self):
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
        migration_fn = MagicMock()

        def upgrade(rev, context):
            migration_fn(rev, context)
            return env.script._upgrade_revs(a_rev, rev)

        with expect_warnings(
            r"'connection' argument to configure\(\) is "
            r"expected to be a sqlalchemy.engine.Connection "
        ):
            env.configure(
                connection=engine, fn=upgrade, transactional_ddl=False
            )

        env.run_migrations()

        eq_(migration_fn.mock_calls, [call((), env._migration_context)])
