#!coding: utf-8

from alembic.script import ScriptDirectory
from alembic.environment import EnvironmentContext
from alembic.migration import MigrationContext
import unittest
from . import Mock, call, _no_sql_testing_config, staging_env, \
    clear_staging_env

from . import eq_, is_


class EnvironmentTest(unittest.TestCase):

    def setUp(self):
        staging_env()
        self.cfg = _no_sql_testing_config()

    def tearDown(self):
        clear_staging_env()

    def _fixture(self, **kw):
        script = ScriptDirectory.from_config(self.cfg)
        env = EnvironmentContext(
            self.cfg,
            script,
            **kw
        )
        return env

    def test_x_arg(self):
        env = self._fixture()
        self.cfg.cmd_opts = Mock(x="y=5")
        eq_(
            env.get_x_argument(),
            "y=5"
        )

    def test_x_arg_asdict(self):
        env = self._fixture()
        self.cfg.cmd_opts = Mock(x=["y=5"])
        eq_(
            env.get_x_argument(as_dictionary=True),
            {"y": "5"}
        )

    def test_x_arg_no_opts(self):
        env = self._fixture()
        eq_(
            env.get_x_argument(),
            []
        )

    def test_x_arg_no_opts_asdict(self):
        env = self._fixture()
        eq_(
            env.get_x_argument(as_dictionary=True),
            {}
        )

    def test_tag_arg(self):
        env = self._fixture(tag="x")
        eq_(
            env.get_tag_argument(),
            "x"
        )

    def test_migration_context_has_config(self):
        env = self._fixture()
        env.configure(url="sqlite://")
        ctx = env._migration_context
        is_(ctx.config, self.cfg)

        ctx = MigrationContext(ctx.dialect, None, {})
        is_(ctx.config, None)
