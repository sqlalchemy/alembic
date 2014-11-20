#!coding: utf-8

import os
import tempfile

from alembic import config, util, compat
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from alembic.testing.fixtures import TestBase
from alembic.testing.mock import Mock, call

from alembic.testing import eq_, assert_raises_message
from alembic.testing.fixtures import capture_db
from alembic.testing.env import _no_sql_testing_config, clear_staging_env,\
    staging_env


class ConfigTest(TestBase):
    def test_config_args(self):
        config_file = tempfile.mktemp()
        with open(config_file, "w") as fp:
            fp.write("""
[alembic]
migrations = %(base_path)s/db/migrations
""")
        cfg = config.Config(config_file, config_args=dict(base_path = "/home/alembic"))
        eq_(cfg.get_section_option("alembic", "migrations"), "/home/alembic/db/migrations")
        print config_file
        os.unlink(config_file)

    def test_config_no_file_main_option(self):
        cfg = config.Config()
        cfg.set_main_option("url", "postgresql://foo/bar")

        eq_(cfg.get_main_option("url"), "postgresql://foo/bar")

    def test_config_no_file_section_option(self):
        cfg = config.Config()
        cfg.set_section_option("foo", "url", "postgresql://foo/bar")

        eq_(cfg.get_section_option("foo", "url"), "postgresql://foo/bar")

        cfg.set_section_option("foo", "echo", "True")
        eq_(cfg.get_section_option("foo", "echo"), "True")

    def test_standalone_op(self):
        eng, buf = capture_db()

        env = MigrationContext.configure(eng)
        op = Operations(env)

        op.alter_column("t", "c", nullable=True)
        eq_(buf, ['ALTER TABLE t ALTER COLUMN c DROP NOT NULL'])

    def test_no_script_error(self):
        cfg = config.Config()
        assert_raises_message(
            util.CommandError,
            "No 'script_location' key found in configuration.",
            ScriptDirectory.from_config, cfg
        )


class StdoutOutputEncodingTest(TestBase):

    def test_plain(self):
        stdout = Mock(encoding='latin-1')
        cfg = config.Config(stdout=stdout)
        cfg.print_stdout("test %s %s", "x", "y")
        eq_(
            stdout.mock_calls,
            [call.write('test x y'), call.write('\n')]
        )

    def test_utf8_unicode(self):
        stdout = Mock(encoding='latin-1')
        cfg = config.Config(stdout=stdout)
        cfg.print_stdout(compat.u("méil %s %s"), "x", "y")
        eq_(
            stdout.mock_calls,
            [call.write(compat.u('méil x y')), call.write('\n')]
        )

    def test_ascii_unicode(self):
        stdout = Mock(encoding=None)
        cfg = config.Config(stdout=stdout)
        cfg.print_stdout(compat.u("méil %s %s"), "x", "y")
        eq_(
            stdout.mock_calls,
            [call.write('m?il x y'), call.write('\n')]
        )


class TemplateOutputEncodingTest(TestBase):
    def setUp(self):
        staging_env()
        self.cfg = _no_sql_testing_config()

    def tearDown(self):
        clear_staging_env()

    def test_default(self):
        script = ScriptDirectory.from_config(self.cfg)
        eq_(script.output_encoding, 'utf-8')

    def test_setting(self):
        self.cfg.set_main_option('output_encoding', 'latin-1')
        script = ScriptDirectory.from_config(self.cfg)
        eq_(script.output_encoding, 'latin-1')
