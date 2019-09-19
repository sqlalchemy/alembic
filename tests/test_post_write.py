import sys

from alembic import command
from alembic import util
from alembic.script import write_hooks
from alembic.testing import assert_raises_message
from alembic.testing import eq_
from alembic.testing import mock
from alembic.testing import TestBase
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env


class HookTest(TestBase):
    def test_register(self):
        @write_hooks.register("my_writer")
        def my_writer(path, config):
            return path

        assert "my_writer" in write_hooks._registry

    def test_invoke(self):
        my_formatter = mock.Mock()
        write_hooks.register("my_writer")(my_formatter)

        write_hooks._invoke("my_writer", "/some/path", {"option": 1})

        my_formatter.assert_called_once_with("/some/path", {"option": 1})


class RunHookTest(TestBase):
    def setUp(self):
        self.env = staging_env()

    def tearDown(self):
        clear_staging_env()

    def test_generic(self):
        hook1 = mock.Mock()
        hook2 = mock.Mock()

        write_hooks.register("hook1")(hook1)
        write_hooks.register("hook2")(hook2)

        self.cfg = _no_sql_testing_config(
            directives=(
                "\n[post_write_hooks]\n"
                "hooks=hook1,hook2\n"
                "hook1.type=hook1\n"
                "hook1.arg1=foo\n"
                "hook2.type=hook2\n"
                "hook2.arg1=bar\n"
            )
        )

        rev = command.revision(self.cfg, message="x")

        eq_(
            hook1.mock_calls,
            [
                mock.call(
                    rev.path,
                    {"type": "hook1", "arg1": "foo", "_hook_name": "hook1"},
                )
            ],
        )
        eq_(
            hook2.mock_calls,
            [
                mock.call(
                    rev.path,
                    {"type": "hook2", "arg1": "bar", "_hook_name": "hook2"},
                )
            ],
        )

    def test_empty_section(self):
        self.cfg = _no_sql_testing_config(
            directives=("\n[post_write_hooks]\n")
        )

        command.revision(self.cfg, message="x")

    def test_no_section(self):
        self.cfg = _no_sql_testing_config(directives="")

        command.revision(self.cfg, message="x")

    def test_empty_hooks(self):
        self.cfg = _no_sql_testing_config(
            directives=("\n[post_write_hooks]\n" "hooks=\n")
        )

        command.revision(self.cfg, message="x")

    def test_no_type(self):
        self.cfg = _no_sql_testing_config(
            directives=(
                "\n[post_write_hooks]\n" "hooks=foo\n" "foo.bar=somebar\n"
            )
        )

        assert_raises_message(
            util.CommandError,
            "Key foo.type is required for post write hook 'foo'",
            command.revision,
            self.cfg,
            message="x",
        )

    def test_console_scripts_entrypoint_missing(self):
        self.cfg = _no_sql_testing_config(
            directives=(
                "\n[post_write_hooks]\n"
                "hooks=black\n"
                "black.type=console_scripts\n"
            )
        )
        assert_raises_message(
            util.CommandError,
            "Key black.entrypoint is required for post write hook 'black'",
            command.revision,
            self.cfg,
            message="x",
        )

    def test_console_scripts(self):
        self.cfg = _no_sql_testing_config(
            directives=(
                "\n[post_write_hooks]\n"
                "hooks=black\n"
                "black.type=console_scripts\n"
                "black.entrypoint=black\n"
                "black.options=-l 79\n"
            )
        )

        impl = mock.Mock(attrs=("foo", "bar"), module_name="black_module")
        entrypoints = mock.Mock(return_value=iter([impl]))
        with mock.patch(
            "pkg_resources.iter_entry_points", entrypoints
        ), mock.patch(
            "alembic.script.write_hooks.subprocess"
        ) as mock_subprocess:

            rev = command.revision(self.cfg, message="x")

        eq_(entrypoints.mock_calls, [mock.call("console_scripts", "black")])
        eq_(
            mock_subprocess.mock_calls,
            [
                mock.call.run(
                    [
                        sys.executable,
                        "-c",
                        "import black_module; black_module.foo.bar()",
                        rev.path,
                        "-l",
                        "79",
                    ]
                )
            ],
        )
