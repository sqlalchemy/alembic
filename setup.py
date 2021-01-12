import os
import re
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand


v = open(os.path.join(os.path.dirname(__file__), "alembic", "__init__.py"))
VERSION = (
    re.compile(r""".*__version__ = ["'](.*?)["']""", re.S)
    .match(v.read())
    .group(1)
)
v.close()


class UseTox(TestCommand):
    RED = 31
    RESET_SEQ = "\033[0m"
    BOLD_SEQ = "\033[1m"
    COLOR_SEQ = "\033[1;%dm"

    def run_tests(self):
        sys.stderr.write(
            "%s%spython setup.py test is deprecated by pypa.  Please invoke "
            "'tox' with no arguments for a basic test run.\n%s"
            % (self.COLOR_SEQ % self.RED, self.BOLD_SEQ, self.RESET_SEQ)
        )
        sys.exit(1)


setup(
    version=VERSION,
    cmdclass={"test": UseTox},
)
