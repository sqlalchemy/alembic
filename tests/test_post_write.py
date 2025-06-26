import importlib.util
from pathlib import Path
import sys

from alembic import command
from alembic import testing
from alembic import util
from alembic.script import write_hooks
from alembic.testing import assert_raises_message
from alembic.testing import combinations
from alembic.testing import eq_
from alembic.testing import mock
from alembic.testing import TestBase
from alembic.testing.env import _get_staging_directory
from alembic.testing.env import _no_sql_pyproject_config
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.util import compat


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

    @testing.variation("config", ["ini", "toml"])
    def test_generic(self, config):
        hook1 = mock.Mock()
        hook2 = mock.Mock()

        write_hooks.register("hook1")(hook1)
        write_hooks.register("hook2")(hook2)

        if config.ini:
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
        else:
            self.cfg = _no_sql_pyproject_config(
                directives="""

                [[tool.alembic.post_write_hooks]]
                name="hook1"
                type="hook1"
                arg1="foo"

                [[tool.alembic.post_write_hooks]]
                name="hook2"
                type="hook2"
                arg1="bar"
                """
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

    @testing.variation("config", ["ini", "toml"])
    def test_no_section(self, config):
        if config.ini:
            self.cfg = _no_sql_testing_config(directives="")
        else:
            self.cfg = _no_sql_pyproject_config(
                directives="""

                """
            )

        command.revision(self.cfg, message="x")

    def test_empty_hooks(self):
        self.cfg = _no_sql_testing_config(
            directives=("\n[post_write_hooks]\n" "hooks=\n")
        )

        command.revision(self.cfg, message="x")

    @testing.variation("config", ["ini", "toml"])
    def test_no_type(self, config):
        if config.ini:
            self.cfg = _no_sql_testing_config(
                directives=(
                    "\n[post_write_hooks]\n" "hooks=foo\n" "foo.bar=somebar\n"
                )
            )
        else:
            self.cfg = _no_sql_pyproject_config(
                directives="""

                [[tool.alembic.post_write_hooks]]
                name="foo"
                bar="somebar"
                """
            )

        assert_raises_message(
            util.CommandError,
            r"Key 'foo.type' \(or 'type' in toml\) is required "
            "for post write hook 'foo'",
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

    def _run_black_with_config(
        self,
        input_config,
        expected_additional_arguments_fn,
        cwd=None,
        use_toml=False,
    ):
        if use_toml:
            self.cfg = _no_sql_pyproject_config(directives=input_config)
        else:
            self.cfg = _no_sql_testing_config(directives=input_config)

        retVal = [
            compat.EntryPoint(
                name="black",
                value="black.foo:patched_main",
                group="console_scripts",
            ),
            compat.EntryPoint(
                name="alembic",
                value="alembic.config:main",
                group="console_scripts",
            ),
        ]

        importlib_metadata_get = mock.Mock(return_value=retVal)
        with (
            mock.patch(
                "alembic.util.compat.importlib_metadata_get",
                importlib_metadata_get,
            ),
            mock.patch(
                "alembic.script.write_hooks.subprocess"
            ) as mock_subprocess,
        ):
            rev = command.revision(self.cfg, message="x")

        eq_(importlib_metadata_get.mock_calls, [mock.call("console_scripts")])
        eq_(
            mock_subprocess.mock_calls,
            [
                mock.call.run(
                    [
                        sys.executable,
                        "-c",
                        "import black.foo; black.foo.patched_main()",
                    ]
                    + expected_additional_arguments_fn(rev.path),
                    cwd=cwd,
                )
            ],
        )

    @testing.variation("config", ["ini", "toml"])
    def test_console_scripts(self, config):
        if config.ini:
            input_config = """
[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 79
            """
        else:
            input_config = """
    [[tool.alembic.post_write_hooks]]
    name = "black"
    type = "console_scripts"
    entrypoint = "black"
    options = "-l 79"
    """

        def expected_additional_arguments_fn(rev_path):
            return [rev_path, "-l", "79"]

        self._run_black_with_config(
            input_config,
            expected_additional_arguments_fn,
            use_toml=config.toml,
        )

    @combinations(True, False, argnames="posix")
    @testing.variation("config", ["ini", "toml"])
    def test_filename_interpolation(self, posix, config):
        if config.ini:
            input_config = """
[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = arg1 REVISION_SCRIPT_FILENAME 'multi-word arg' \
    --flag1='REVISION_SCRIPT_FILENAME'
        """
        else:
            input_config = """
[[tool.alembic.post_write_hooks]]
name = "black"
type = "console_scripts"
entrypoint = "black"
options = "arg1 REVISION_SCRIPT_FILENAME 'multi-word arg' --flag1='REVISION_SCRIPT_FILENAME'"
"""  # noqa: E501

        def expected_additional_arguments_fn(rev_path):
            if compat.is_posix:
                return [
                    "arg1",
                    rev_path,
                    "multi-word arg",
                    "--flag1=" + rev_path,
                ]
            else:
                return [
                    "arg1",
                    rev_path,
                    "'multi-word arg'",
                    "--flag1='%s'" % rev_path,
                ]

        with mock.patch("alembic.util.compat.is_posix", posix):
            self._run_black_with_config(
                input_config,
                expected_additional_arguments_fn,
                use_toml=config.toml,
            )

    def test_path_in_config(self):
        input_config = """
[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = arg1 REVISION_SCRIPT_FILENAME --config %(here)s/pyproject.toml
        """

        def expected_additional_arguments_fn(rev_path):
            return [
                "arg1",
                rev_path,
                "--config",
                Path(_get_staging_directory(), "pyproject.toml")
                .absolute()
                .as_posix(),
            ]

        self._run_black_with_config(
            input_config, expected_additional_arguments_fn
        )

    def test_black_with_cwd(self):
        input_config = """
[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.cwd = /path/to/cwd
        """

        def expected_additional_arguments_fn(rev_path):
            return [rev_path]

        self._run_black_with_config(
            input_config, expected_additional_arguments_fn, cwd="/path/to/cwd"
        )

    def test_exec_executable_missing(self):
        self.cfg = _no_sql_testing_config(
            directives=(
                "\n[post_write_hooks]\n" "hooks=ruff\n" "ruff.type=exec\n"
            )
        )
        assert_raises_message(
            util.CommandError,
            "Key ruff.executable is required for post write hook 'ruff'",
            command.revision,
            self.cfg,
            message="x",
        )

    def _run_ruff_with_config(
        self,
        input_config,
        expected_additional_arguments_fn,
        executable="ruff",
        cwd=None,
    ):
        self.cfg = _no_sql_testing_config(directives=input_config)

        with mock.patch(
            "alembic.script.write_hooks.subprocess"
        ) as mock_subprocess:
            rev = command.revision(self.cfg, message="x")

        eq_(
            mock_subprocess.mock_calls,
            [
                mock.call.run(
                    [
                        executable,
                    ]
                    + expected_additional_arguments_fn(rev.path),
                    cwd=cwd,
                )
            ],
        )

    def test_exec_with_path_search(self):
        input_config = """
[post_write_hooks]
hooks = ruff
ruff.type = exec
ruff.executable = ruff
ruff.options = check --fix
        """

        def expected_additional_arguments_fn(rev_path):
            return [rev_path, "check", "--fix"]

        self._run_ruff_with_config(
            input_config, expected_additional_arguments_fn
        )

    def test_exec_with_full_pathname(self):
        input_config = """
[post_write_hooks]
hooks = ruff
ruff.type = exec
ruff.executable = %(here)s/.venv/bin/ruff
ruff.options = check --fix
        """

        def expected_additional_arguments_fn(rev_path):
            return [rev_path, "check", "--fix"]

        self._run_ruff_with_config(
            input_config,
            expected_additional_arguments_fn,
            executable=Path(_get_staging_directory(), ".venv/bin/ruff")
            .absolute()
            .as_posix(),
        )

    @combinations(True, False)
    def test_exec_with_filename_interpolation(self, posix):
        input_config = """
[post_write_hooks]
hooks = ruff
ruff.type = exec
ruff.executable = ruff
ruff.options = arg1 REVISION_SCRIPT_FILENAME 'multi-word arg' \
    --flag1='REVISION_SCRIPT_FILENAME'
        """

        def expected_additional_arguments_fn(rev_path):
            if compat.is_posix:
                return [
                    "arg1",
                    rev_path,
                    "multi-word arg",
                    "--flag1=" + rev_path,
                ]
            else:
                return [
                    "arg1",
                    rev_path,
                    "'multi-word arg'",
                    "--flag1='%s'" % rev_path,
                ]

        with mock.patch("alembic.util.compat.is_posix", posix):
            self._run_ruff_with_config(
                input_config, expected_additional_arguments_fn
            )

    def test_exec_with_path_in_config(self):
        input_config = """
[post_write_hooks]
hooks = ruff
ruff.type = exec
ruff.executable = ruff
ruff.options = arg1 REVISION_SCRIPT_FILENAME --config %(here)s/pyproject.toml
        """

        def expected_additional_arguments_fn(rev_path):
            return [
                "arg1",
                rev_path,
                "--config",
                Path(_get_staging_directory(), "pyproject.toml")
                .absolute()
                .as_posix(),
            ]

        self._run_ruff_with_config(
            input_config, expected_additional_arguments_fn
        )

    def test_exec_with_cwd(self):
        input_config = """
[post_write_hooks]
hooks = ruff
ruff.type = exec
ruff.executable = ruff
ruff.cwd = /path/to/cwd
        """

        def expected_additional_arguments_fn(rev_path):
            return [rev_path]

        self._run_ruff_with_config(
            input_config, expected_additional_arguments_fn, cwd="/path/to/cwd"
        )

    def test_module_config_missing(self):
        self.cfg = _no_sql_testing_config(
            directives=(
                """
[post_write_hooks]
hooks = ruff
ruff.type = module
                """
            )
        )
        assert_raises_message(
            util.CommandError,
            "Key ruff.module is required for post write hook 'ruff'",
            command.revision,
            self.cfg,
            message="x",
        )

    def test_module_not_found(self):
        self.cfg = _no_sql_testing_config(
            directives=(
                """
[post_write_hooks]
hooks = ruff
ruff.type = module
ruff.module = ruff_not_found
                """
            )
        )
        assert_raises_message(
            util.CommandError,
            "Could not find module ruff_not_found",
            command.revision,
            self.cfg,
            message="x",
        )

    def _run_black_module_with_config(
        self,
        input_config,
        expected_additional_arguments_fn,
        cwd=None,
        use_toml=False,
    ):
        if use_toml:
            self.cfg = _no_sql_pyproject_config(directives=input_config)
        else:
            self.cfg = _no_sql_testing_config(directives=input_config)

        black_module_spec = importlib.util.find_spec("black")

        importlib_util_find_spec = mock.Mock(return_value=black_module_spec)
        with (
            mock.patch(
                "importlib.util.find_spec",
                importlib_util_find_spec,
            ),
            mock.patch(
                "alembic.script.write_hooks.subprocess"
            ) as mock_subprocess,
        ):
            rev = command.revision(self.cfg, message="x")

        eq_(importlib_util_find_spec.mock_calls, [mock.call("black")])
        eq_(
            mock_subprocess.mock_calls,
            [
                mock.call.run(
                    [
                        sys.executable,
                        "-m",
                        "black",
                    ]
                    + expected_additional_arguments_fn(rev.path),
                    cwd=cwd,
                )
            ],
        )

    @testing.variation("config", ["ini", "toml"])
    def test_module(self, config):
        if config.ini:
            input_config = """
[post_write_hooks]
hooks = black
black.type = module
black.module = black
black.options = -l 79
            """
        else:
            input_config = """
    [[tool.alembic.post_write_hooks]]
    name = "black"
    type = "module"
    module = "black"
    options = "-l 79"
    """

        def expected_additional_arguments_fn(rev_path):
            return [rev_path, "-l", "79"]

        self._run_black_module_with_config(
            input_config,
            expected_additional_arguments_fn,
            use_toml=config.toml,
        )

    @combinations(True, False, argnames="posix")
    @testing.variation("config", ["ini", "toml"])
    def test_module_filename_interpolation(self, posix, config):
        if config.ini:
            input_config = """
[post_write_hooks]
hooks = black
black.type = module
black.module = black
black.options = arg1 REVISION_SCRIPT_FILENAME 'multi-word arg' \
    --flag1='REVISION_SCRIPT_FILENAME'
        """
        else:
            input_config = """
[[tool.alembic.post_write_hooks]]
name = "black"
type = "module"
module = "black"
options = "arg1 REVISION_SCRIPT_FILENAME 'multi-word arg' --flag1='REVISION_SCRIPT_FILENAME'"
"""  # noqa: E501

        def expected_additional_arguments_fn(rev_path):
            if compat.is_posix:
                return [
                    "arg1",
                    rev_path,
                    "multi-word arg",
                    "--flag1=" + rev_path,
                ]
            else:
                return [
                    "arg1",
                    rev_path,
                    "'multi-word arg'",
                    "--flag1='%s'" % rev_path,
                ]

        with mock.patch("alembic.util.compat.is_posix", posix):
            self._run_black_module_with_config(
                input_config,
                expected_additional_arguments_fn,
                use_toml=config.toml,
            )

    def test_module_path_in_config(self):
        input_config = """
[post_write_hooks]
hooks = black
black.type = module
black.module = black
black.options = arg1 REVISION_SCRIPT_FILENAME --config %(here)s/pyproject.toml
        """

        def expected_additional_arguments_fn(rev_path):
            return [
                "arg1",
                rev_path,
                "--config",
                Path(_get_staging_directory(), "pyproject.toml")
                .absolute()
                .as_posix(),
            ]

        self._run_black_module_with_config(
            input_config, expected_additional_arguments_fn
        )

    def test_module_black_with_cwd(self):
        input_config = """
[post_write_hooks]
hooks = black
black.type = module
black.module = black
black.cwd = /path/to/cwd
        """

        def expected_additional_arguments_fn(rev_path):
            return [rev_path]

        self._run_black_module_with_config(
            input_config, expected_additional_arguments_fn, cwd="/path/to/cwd"
        )
