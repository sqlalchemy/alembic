from pathlib import Path
import subprocess
import sys

import alembic
from alembic.testing import eq_
from alembic.testing import TestBase

_home = Path(__file__).parent.parent


def run_command(file):
    res = subprocess.run(
        [
            sys.executable,
            str((_home / "tools" / "write_pyi.py").relative_to(_home)),
            "--stdout",
            "--file",
            file,
        ],
        stdout=subprocess.PIPE,
        cwd=_home,
        encoding="utf-8",
    )
    return res


class TestStubFiles(TestBase):
    __requires__ = ("stubs_test",)

    def test_op_pyi(self):
        res = run_command("op")
        generated = res.stdout
        expected = Path(alembic.__file__).parent / "op.pyi"
        eq_(generated, expected.read_text())

    def test_context_pyi(self):
        res = run_command("context")
        generated = res.stdout
        expected = Path(alembic.__file__).parent / "context.pyi"
        eq_(generated, expected.read_text())
