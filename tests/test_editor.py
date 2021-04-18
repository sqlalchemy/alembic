import os
from os.path import join
from unittest.mock import patch

from alembic import util
from alembic.testing import combinations
from alembic.testing import expect_raises_message
from alembic.testing.fixtures import TestBase


class TestHelpers(TestBase):
    def common(self, cb, is_posix=True):
        with patch("alembic.util.editor.check_call") as check_call, patch(
            "alembic.util.editor.exists"
        ) as exists, patch(
            "alembic.util.editor.is_posix",
            new=is_posix,
        ), patch(
            "os.pathsep", new=":" if is_posix else ";"
        ):
            cb(check_call, exists)

    @combinations((True,), (False,))
    def test_edit_with_user_editor(self, posix):
        def go(check_call, exists):
            test_environ = {"EDITOR": "myvim", "PATH": "/usr/bin"}
            executable = join("/usr/bin", "myvim")
            if not posix:
                executable += ".exe"

            exists.side_effect = lambda fname: fname == executable
            util.open_in_editor("myfile", test_environ)
            check_call.assert_called_with([executable, "myfile"])

        self.common(go, posix)

    @combinations(("EDITOR",), ("VISUAL",))
    def test_edit_with_user_editor_exists(self, key):
        def go(check_call, exists):
            test_environ = {key: "myvim", "PATH": "/usr/bin"}
            exists.side_effect = lambda fname: fname == "myvim"
            util.open_in_editor("myfile", test_environ)
            check_call.assert_called_with(["myvim", "myfile"])

        self.common(go)

    @combinations((True,), (False,))
    def test_edit_with_user_editor_precedence(self, with_path):
        def go(check_call, exists):
            test_environ = {
                "EDITOR": "myvim",
                "VISUAL": "myvisual",
                "PATH": "/usr/bin",
            }
            exes = ["myvim", "myvisual"]
            if with_path:
                exes = [join("/usr/bin", n) for n in exes]
            exists.side_effect = lambda fname: fname in exes
            util.open_in_editor("myfile", test_environ)
            check_call.assert_called_with([exes[0], "myfile"])

        self.common(go)

    def test_edit_with_user_editor_abs(self):
        def go(check_call, exists):
            test_environ = {"EDITOR": "/foo/myvim", "PATH": "/usr/bin"}
            exists.side_effect = lambda fname: fname == "/usr/bin/foo/myvim"
            with expect_raises_message(util.CommandError, "EDITOR"):
                util.open_in_editor("myfile", test_environ)

        self.common(go)

    def test_edit_with_default_editor(self):
        def go(check_call, exists):
            test_environ = {"PATH": os.pathsep.join(["/usr/bin", "/bin"])}
            executable = join("/bin", "vim")

            exists.side_effect = lambda fname: fname == executable
            util.open_in_editor("myfile", test_environ)
            check_call.assert_called_with([executable, "myfile"])

        self.common(go)

    def test_edit_with_default_editor_windows(self):
        def go(check_call, exists):
            test_environ = {
                "PATH": os.pathsep.join(
                    [r"C:\Windows\System32", r"C:\Users\user\bin"]
                )
            }
            executable = join(r"C:\Users\user\bin", "notepad.exe")

            exists.side_effect = lambda fname: fname == executable
            util.open_in_editor("myfile", test_environ)
            check_call.assert_called_with([executable, "myfile"])

        self.common(go, False)

    def test_edit_with_missing_editor(self):
        def go(check_call, exists):
            test_environ = {}
            exists.return_value = False
            with expect_raises_message(util.CommandError, "EDITOR"):
                util.open_in_editor("myfile", test_environ)

        self.common(go)
