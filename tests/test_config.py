#!coding: utf-8


from alembic import config
from alembic import util
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from alembic.testing import assert_raises_message
from alembic.testing import eq_
from alembic.testing import mock
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import _write_config_file
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.fixtures import capture_db
from alembic.testing.fixtures import TestBase
from alembic.util import compat


class FileConfigTest(TestBase):
    def test_config_args(self):
        cfg = _write_config_file(
            """
[alembic]
migrations = %(base_path)s/db/migrations
"""
        )
        test_cfg = config.Config(
            cfg.config_file_name, config_args=dict(base_path="/home/alembic")
        )
        eq_(
            test_cfg.get_section_option("alembic", "migrations"),
            "/home/alembic/db/migrations",
        )

    def tearDown(self):
        clear_staging_env()


class ConfigTest(TestBase):
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

    def test_config_set_main_option_percent(self):
        cfg = config.Config()
        cfg.set_main_option("foob", "a %% percent")

        eq_(cfg.get_main_option("foob"), "a % percent")

    def test_config_set_section_option_percent(self):
        cfg = config.Config()
        cfg.set_section_option("some_section", "foob", "a %% percent")

        eq_(cfg.get_section_option("some_section", "foob"), "a % percent")

    def test_config_set_section_option_interpolation(self):
        cfg = config.Config()
        cfg.set_section_option("some_section", "foob", "foob_value")

        cfg.set_section_option("some_section", "bar", "bar with %(foob)s")

        eq_(
            cfg.get_section_option("some_section", "bar"),
            "bar with foob_value",
        )

    def test_standalone_op(self):
        eng, buf = capture_db()

        env = MigrationContext.configure(eng)
        op = Operations(env)

        op.alter_column("t", "c", nullable=True)
        eq_(buf, ["ALTER TABLE t ALTER COLUMN c DROP NOT NULL"])

    def test_no_script_error(self):
        cfg = config.Config()
        assert_raises_message(
            util.CommandError,
            "No 'script_location' key found in configuration.",
            ScriptDirectory.from_config,
            cfg,
        )

    def test_attributes_attr(self):
        m1 = mock.Mock()
        cfg = config.Config()
        cfg.attributes["connection"] = m1
        eq_(cfg.attributes["connection"], m1)

    def test_attributes_construtor(self):
        m1 = mock.Mock()
        m2 = mock.Mock()
        cfg = config.Config(attributes={"m1": m1})
        cfg.attributes["connection"] = m2
        eq_(cfg.attributes, {"m1": m1, "connection": m2})


class StdoutOutputEncodingTest(TestBase):
    def test_plain(self):
        stdout = mock.Mock(encoding="latin-1")
        cfg = config.Config(stdout=stdout)
        cfg.print_stdout("test %s %s", "x", "y")
        eq_(
            stdout.mock_calls,
            [mock.call.write("test x y"), mock.call.write("\n")],
        )

    def test_utf8_unicode(self):
        stdout = mock.Mock(encoding="latin-1")
        cfg = config.Config(stdout=stdout)
        cfg.print_stdout(compat.u("méil %s %s"), "x", "y")
        eq_(
            stdout.mock_calls,
            [mock.call.write(compat.u("méil x y")), mock.call.write("\n")],
        )

    def test_ascii_unicode(self):
        stdout = mock.Mock(encoding=None)
        cfg = config.Config(stdout=stdout)
        cfg.print_stdout(compat.u("méil %s %s"), "x", "y")
        eq_(
            stdout.mock_calls,
            [mock.call.write("m?il x y"), mock.call.write("\n")],
        )

    def test_only_formats_output_with_args(self):
        stdout = mock.Mock(encoding=None)
        cfg = config.Config(stdout=stdout)
        cfg.print_stdout(compat.u("test 3%"))
        eq_(
            stdout.mock_calls,
            [mock.call.write("test 3%"), mock.call.write("\n")],
        )


class TemplateOutputEncodingTest(TestBase):
    def setUp(self):
        staging_env()
        self.cfg = _no_sql_testing_config()

    def tearDown(self):
        clear_staging_env()

    def test_default(self):
        script = ScriptDirectory.from_config(self.cfg)
        eq_(script.output_encoding, "utf-8")

    def test_setting(self):
        self.cfg.set_main_option("output_encoding", "latin-1")
        script = ScriptDirectory.from_config(self.cfg)
        eq_(script.output_encoding, "latin-1")
