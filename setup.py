import os
import re
import sys

from setuptools import find_packages
from setuptools import setup
from setuptools.command.test import test as TestCommand


v = open(os.path.join(os.path.dirname(__file__), "alembic", "__init__.py"))
VERSION = (
    re.compile(r""".*__version__ = ["'](.*?)["']""", re.S)
    .match(v.read())
    .group(1)
)
v.close()


readme = os.path.join(os.path.dirname(__file__), "README.rst")

requires = [
    "SQLAlchemy>=1.1.0",
    "Mako",
    "python-editor>=0.3",
    "python-dateutil",
]


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
    name="alembic",
    version=VERSION,
    description="A database migration tool for SQLAlchemy.",
    long_description=open(readme).read(),
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Database :: Front-Ends",
    ],
    keywords="SQLAlchemy migrations",
    author="Mike Bayer",
    author_email="mike@zzzcomputing.com",
    url="https://alembic.sqlalchemy.org",
    project_urls={"Issue Tracker": "https://github.com/sqlalchemy/alembic/"},
    license="MIT",
    packages=find_packages(".", exclude=["examples*", "test*"]),
    include_package_data=True,
    cmdclass={"test": UseTox},
    zip_safe=False,
    install_requires=requires,
    entry_points={"console_scripts": ["alembic = alembic.config:main"]},
)
