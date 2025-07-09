import os
import pathlib
import sys
import tempfile

from alembic import command
from alembic import config
from alembic import testing
from alembic import util
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from alembic.testing import assert_raises_message
from alembic.testing import eq_
from alembic.testing import mock
from alembic.testing.assertions import expect_raises_message
from alembic.testing.env import _get_staging_directory
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import _testing_config
from alembic.testing.env import _write_config_file
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.fixtures import capture_db
from alembic.testing.fixtures import TestBase


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

    def test_attributes_constructor(self):
        m1 = mock.Mock()
        m2 = mock.Mock()
        cfg = config.Config(attributes={"m1": m1})
        cfg.attributes["connection"] = m2
        eq_(cfg.attributes, {"m1": m1, "connection": m2})

    @testing.combinations(
        (
            "legacy raw string 1",
            None,
            "/foo",
            ["/foo"],
        ),
        (
            "legacy raw string 2",
            None,
            "/foo /bar",
            ["/foo", "/bar"],
        ),
        (
            "legacy raw string 3",
            "space",
            "/foo",
            ["/foo"],
        ),
        (
            "legacy raw string 4",
            "space",
            "/foo /bar",
            ["/foo", "/bar"],
        ),
        (
            "multiline string 1",
            "newline",
            " /foo  \n/bar  ",
            ["/foo", "/bar"],
        ),
        (
            "Linux pathsep 1",
            ":",
            "/Project A",
            ["/Project A"],
        ),
        (
            "Linux pathsep 2",
            ":",
            "/Project A:/Project B",
            ["/Project A", "/Project B"],
        ),
        (
            "Windows pathsep 1",
            ";",
            r"C:\Project A",
            [r"C:\Project A"],
        ),
        (
            "Windows pathsep 2",
            ";",
            r"C:\Project A;C:\Project B",
            [r"C:\Project A", r"C:\Project B"],
        ),
        (
            "os pathsep",
            "os",
            r"path_number_one%(sep)spath_number_two%(sep)s"
            % {"sep": os.pathsep},
            [r"path_number_one", r"path_number_two"],
        ),
        (
            "invalid pathsep 2",
            "|",
            "/foo|/bar",
            ValueError(
                "'|' is not a valid value for path_separator; "
                "expected 'space', 'newline', 'os', ':', ';'"
            ),
        ),
        id_="iaaa",
        argnames="separator, string_value, expected_result",
    )
    def test_version_locations(self, separator, string_value, expected_result):
        cfg = config.Config()
        if separator is not None:
            cfg.set_main_option(
                "path_separator",
                separator,
            )
        cfg.set_main_option("script_location", tempfile.gettempdir())
        cfg.set_main_option("version_locations", string_value)

        if isinstance(expected_result, ValueError):
            message = str(expected_result)
            with expect_raises_message(ValueError, message, text_exact=True):
                ScriptDirectory.from_config(cfg)
        else:
            if separator is None:
                with testing.expect_deprecated(
                    "No path_separator found in configuration; "
                    "falling back to legacy splitting on spaces/commas "
                    "for version_locations"
                ):
                    s = ScriptDirectory.from_config(cfg)
            else:
                s = ScriptDirectory.from_config(cfg)

            eq_(s.version_locations, expected_result)

    @testing.combinations(
        (
            "legacy raw string 1",
            None,
            "/foo",
            ["/foo"],
        ),
        (
            "legacy raw string 2",
            None,
            "/foo /bar",
            ["/foo", "/bar"],
        ),
        (
            "legacy raw string 3",
            "space",
            "/foo",
            ["/foo"],
        ),
        (
            "legacy raw string 4",
            "space",
            "/foo /bar",
            ["/foo", "/bar"],
        ),
        (
            "multiline string 1",
            "newline",
            " /foo  \n/bar  ",
            ["/foo", "/bar"],
        ),
        (
            "Linux pathsep 1",
            ":",
            "/Project A",
            ["/Project A"],
        ),
        (
            "Linux pathsep 2",
            ":",
            "/Project A:/Project B",
            ["/Project A", "/Project B"],
        ),
        (
            "Windows pathsep 1",
            ";",
            r"C:\Project A",
            [r"C:\Project A"],
        ),
        (
            "Windows pathsep 2",
            ";",
            r"C:\Project A;C:\Project B",
            [r"C:\Project A", r"C:\Project B"],
        ),
        (
            "os pathsep",
            "os",
            r"path_number_one%(sep)spath_number_two%(sep)s"
            % {"sep": os.pathsep},
            [r"path_number_one", r"path_number_two"],
        ),
        (
            "invalid pathsep 2",
            "|",
            "/foo|/bar",
            ValueError(
                "'|' is not a valid value for path_separator; "
                "expected 'space', 'newline', 'os', ':', ';'"
            ),
        ),
        id_="iaaa",
        argnames="separator, string_value, expected_result",
    )
    def test_prepend_sys_path_locations(
        self, separator, string_value, expected_result
    ):
        cfg = config.Config()
        if separator is not None:
            cfg.set_main_option(
                "path_separator",
                separator,
            )
        cfg.set_main_option("script_location", tempfile.gettempdir())
        cfg.set_main_option("prepend_sys_path", string_value)

        if isinstance(expected_result, ValueError):
            message = str(expected_result)
            with expect_raises_message(ValueError, message, text_exact=True):
                ScriptDirectory.from_config(cfg)
        else:
            restore_path = list(sys.path)
            try:
                sys.path.clear()

                if separator is None:
                    with testing.expect_deprecated(
                        "No path_separator found in configuration; "
                        "falling back to legacy splitting on spaces, commas, "
                        "and colons for prepend_sys_path"
                    ):
                        ScriptDirectory.from_config(cfg)
                else:
                    ScriptDirectory.from_config(cfg)
                eq_(sys.path, expected_result)
            finally:
                sys.path = restore_path

    def test_version_path_separator_deprecation_warning(self):
        cfg = config.Config()
        cfg.set_main_option("script_location", tempfile.gettempdir())
        cfg.set_main_option("version_path_separator", "space")
        cfg.set_main_option(
            "version_locations", "/path/one /path/two /path:/three"
        )
        with testing.expect_deprecated(
            "The version_path_separator configuration parameter is "
            "deprecated; please use path_separator"
        ):
            script = ScriptDirectory.from_config(cfg)
        eq_(
            script.version_locations,
            ["/path/one", "/path/two", "/path:/three"],
        )


class PyprojectConfigTest(TestBase):
    @testing.fixture
    def pyproject_only_env(self):
        cfg = _testing_config()
        path = pathlib.Path(_get_staging_directory(), "scripts")
        command.init(cfg, str(path), template="pyproject")
        cfg._config_file_path.unlink()
        yield cfg
        clear_staging_env()

    def test_revision_command_no_alembicini(self, pyproject_only_env):
        cfg = pyproject_only_env
        path = pathlib.Path(_get_staging_directory(), "scripts")
        pyproject_path = path.parent / "pyproject.toml"
        eq_(pyproject_path, cfg._toml_file_path)
        assert pyproject_path.exists()
        assert not cfg._config_file_path.exists()

        # the cfg contains the path to alembic.ini but the file
        # is not present. the idea here is that all the required config
        # should go to pyproject.toml first before raising.

        ScriptDirectory.from_config(cfg)

        command.revision(cfg, message="x")

        command.history(cfg)

    def test_no_config_at_all_still_raises(self, pyproject_only_env):
        cfg = pyproject_only_env
        cfg._toml_file_path.unlink()
        assert not cfg._toml_file_path.exists()
        assert not cfg._config_file_path.exists()

        with expect_raises_message(
            util.CommandError,
            r"No 'script_location' key found in configuration.",
        ):
            ScriptDirectory.from_config(cfg)

    def test_get_main_option_raises(self, pyproject_only_env):
        cfg = pyproject_only_env

        with expect_raises_message(
            util.CommandError,
            r"No config file '.*test_alembic.ini' found, "
            r"or file has no '\[alembic\]' section",
        ):
            cfg.get_main_option("asdf")

    def test_get_main_ini_added(self, pyproject_only_env):
        cfg = pyproject_only_env

        with cfg._config_file_path.open("w") as file_:
            file_.write("[alembic]\nasdf = back_at_ya")

        eq_(cfg.get_main_option("asdf"), "back_at_ya")

    def test_script_location(self, pyproject_only_env):
        cfg = pyproject_only_env
        with cfg._toml_file_path.open("wb") as file_:
            file_.write(
                rb"""

[tool.alembic]
script_location = "%(here)s/scripts"

"""
            )

        new_cfg = config.Config(
            file_=cfg.config_file_name, toml_file=cfg._toml_file_path
        )
        sd = ScriptDirectory.from_config(new_cfg)
        eq_(
            pathlib.Path(sd.dir),
            pathlib.Path(_get_staging_directory(), "scripts").absolute(),
        )

    def test_version_locations(self, pyproject_only_env):

        cfg = pyproject_only_env
        with cfg._toml_file_path.open("ba") as file_:
            file_.write(
                b"""
version_locations = [
    "%(here)s/foo/bar"
]
"""
            )

        if "toml_alembic_config" in cfg.__dict__:
            cfg.__dict__.pop("toml_alembic_config")

        eq_(
            cfg.get_version_locations_list(),
            [
                pathlib.Path(_get_staging_directory(), "foo/bar")
                .absolute()
                .as_posix()
            ],
        )

    def test_prepend_sys_path(self, pyproject_only_env):

        cfg = pyproject_only_env
        with cfg._toml_file_path.open("wb") as file_:
            file_.write(
                rb"""

[tool.alembic]
script_location = "%(here)s/scripts"

prepend_sys_path = [
    ".",
    "%(here)s/path/to/python",
    "c:\\some\\path"
]
"""
            )

        if "toml_alembic_config" in cfg.__dict__:
            cfg.__dict__.pop("toml_alembic_config")

        eq_(
            cfg.get_prepend_sys_paths_list(),
            [
                ".",
                pathlib.Path(_get_staging_directory(), "path/to/python")
                .absolute()
                .as_posix(),
                r"c:\some\path",
            ],
        )

    def test_write_hooks(self, pyproject_only_env):

        cfg = pyproject_only_env
        with cfg._toml_file_path.open("wb") as file_:
            file_.write(
                rb"""

[tool.alembic]
script_location = "%(here)s/scripts"

[[tool.alembic.post_write_hooks]]
name = "myhook"
type = "exec"
executable = "%(here)s/.venv/bin/ruff"
options = "-l 79 REVISION_SCRIPT_FILENAME"

"""
            )

        if "toml_alembic_config" in cfg.__dict__:
            cfg.__dict__.pop("toml_alembic_config")

        eq_(
            cfg.get_hooks_list(),
            [
                {
                    "type": "exec",
                    "executable": (
                        cfg._toml_file_path.absolute().parent
                        / ".venv/bin/ruff"
                    ).as_posix(),
                    "options": "-l 79 REVISION_SCRIPT_FILENAME",
                    "_hook_name": "myhook",
                }
            ],
        )

    def test_string_list(self, pyproject_only_env):

        cfg = pyproject_only_env
        with cfg._toml_file_path.open("wb") as file_:
            file_.write(
                rb"""

[tool.alembic]
script_location = "%(here)s/scripts"

my_list = [
    "one",
    "two %(here)s three"
]

"""
            )
        if "toml_alembic_config" in cfg.__dict__:
            cfg.__dict__.pop("toml_alembic_config")

        eq_(
            cfg.get_alembic_option("my_list"),
            [
                "one",
                f"two {cfg._toml_file_path.absolute().parent.as_posix()} "
                "three",
            ],
        )

    @testing.combinations(
        "sourceless", "recursive_version_locations", argnames="paramname"
    )
    @testing.variation("argtype", ["true", "false", "omit", "wrongvalue"])
    def test_bool(
        self, pyproject_only_env, argtype: testing.Variation, paramname
    ):

        cfg = pyproject_only_env
        with cfg._toml_file_path.open("w") as file_:

            if argtype.true:
                config_option = f"{paramname} = true"
            elif argtype.false:
                config_option = f"{paramname} = false"
            elif argtype.omit:
                config_option = ""
            elif argtype.wrongvalue:
                config_option = f"{paramname} = 'false'"
            else:
                argtype.fail()

            file_.write(
                rf"""

[tool.alembic]
script_location = "%(here)s/scripts"

{config_option}
"""
            )
        if "toml_alembic_config" in cfg.__dict__:
            cfg.__dict__.pop("toml_alembic_config")

        if argtype.wrongvalue:
            with expect_raises_message(
                util.CommandError,
                f"boolean value expected for TOML parameter '{paramname}'",
            ):
                sd = ScriptDirectory.from_config(cfg)
        else:
            sd = ScriptDirectory.from_config(cfg)
            eq_(getattr(sd, paramname), bool(argtype.true))


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
        cfg.print_stdout("méil %s %s", "x", "y")
        eq_(
            stdout.mock_calls,
            [mock.call.write("méil x y"), mock.call.write("\n")],
        )

    def test_ascii_unicode(self):
        stdout = mock.Mock(encoding=None)
        cfg = config.Config(stdout=stdout)
        cfg.print_stdout("méil %s %s", "x", "y")
        eq_(
            stdout.mock_calls,
            [mock.call.write("m?il x y"), mock.call.write("\n")],
        )

    def test_only_formats_output_with_args(self):
        stdout = mock.Mock(encoding=None)
        cfg = config.Config(stdout=stdout)
        cfg.print_stdout("test 3%")
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


class CommandLineTest(TestBase):
    def test_register_command(self):
        cli = config.CommandLine()

        fake_stdout = []

        def frobnicate(config: config.Config, revision: str) -> None:
            """Frobnicates the revision.

            :param config: a :class:`.Config` instance
            :param revision: the revision to frobnicate
            """

            fake_stdout.append(f"Revision {revision} frobnicated.")

        cli.register_command(frobnicate)

        help_text = cli.parser.format_help()
        assert frobnicate.__name__ in help_text
        assert frobnicate.__doc__.split("\n")[0] in help_text

        cli.main(["frobnicate", "abc42"])

        assert fake_stdout == ["Revision abc42 frobnicated."]
