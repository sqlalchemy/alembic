"""Nox configuration for Alembic."""

from __future__ import annotations

import os
import sys
from typing import Optional
from typing import Sequence

import nox
from packaging.version import parse as parse_version

if True:
    sys.path.insert(0, ".")
    from tools.toxnox import move_junit_file
    from tools.toxnox import tox_parameters
    from tools.toxnox import extract_opts


SQLA_REPO = os.environ.get(
    "SQLA_REPO", "git+https://github.com/sqlalchemy/sqlalchemy.git"
)

PYTHON_VERSIONS = [
    "3.8",
    "3.9",
    "3.10",
    "3.11",
    "3.12",
    "3.13",
    "3.13t",
    "3.14",
    "3.14t",
]
DATABASES = ["sqlite", "postgresql", "mysql", "oracle", "mssql"]
SQLALCHEMY_VERSIONS = ["default", "sqla14", "sqla20", "sqlamain"]

pyproject = nox.project.load_toml("pyproject.toml")

nox.options.sessions = ["tests"]
nox.options.tags = ["py"]


def filter_sqla(
    python: str, sqlalchemy: str, database: Optional[str] = None
) -> bool:
    python_version = parse_version(python.rstrip("t"))
    if sqlalchemy == "sqla14":
        return python_version < parse_version("3.14")
    elif sqlalchemy == "sqlamain":
        return python_version > parse_version("3.9")
    else:
        return True


@nox.session()
@tox_parameters(
    ["python", "sqlalchemy", "database"],
    [PYTHON_VERSIONS, SQLALCHEMY_VERSIONS, DATABASES],
    filter_=filter_sqla,
)
def tests(session: nox.Session, sqlalchemy: str, database: str) -> None:
    """Run the main test suite against one database at a time"""

    _tests(session, sqlalchemy, [database])


@nox.session()
@tox_parameters(
    ["python", "sqlalchemy"],
    [PYTHON_VERSIONS, SQLALCHEMY_VERSIONS],
    filter_=filter_sqla,
    base_tag="all",
)
def tests_alldb(session: nox.Session, sqlalchemy: str) -> None:
    """Run the main test suite against all backends at once"""

    _tests(session, sqlalchemy, DATABASES)


@nox.session(name="coverage")
@tox_parameters(
    ["database"],
    [DATABASES],
    base_tag="coverage",
)
def coverage(session: nox.Session, database: str) -> None:
    """Run tests with coverage."""

    _tests(session, "default", [database], coverage=True)


def _tests(
    session: nox.Session,
    sqlalchemy: str,
    databases: Sequence[str],
    coverage: bool = False,
) -> None:
    if sqlalchemy == "sqla14":
        session.install(f"{SQLA_REPO}@rel_1_4#egg=sqlalchemy")
    elif sqlalchemy == "sqla20":
        session.install(f"{SQLA_REPO}@rel_2_0#egg=sqlalchemy")
    elif sqlalchemy == "sqlamain":
        session.install(f"{SQLA_REPO}#egg=sqlalchemy")

    # for sqlalchemy == "default", the alembic install will install
    # current released SQLAlchemy version as a dependency
    if coverage:
        session.install("-e", ".")
    else:
        session.install(".")

    session.install(*nox.project.dependency_groups(pyproject, "tests"))

    if coverage:
        session.install(*nox.project.dependency_groups(pyproject, "coverage"))

    session.env["SQLALCHEMY_WARN_20"] = "1"

    cmd = ["python", "-m", "pytest"]

    if coverage:
        cmd.extend(
            [
                "--cov=alembic",
                "--cov-append",
                "--cov-report",
                "term",
                "--cov-report",
                "xml",
            ],
        )

    cmd.extend(os.environ.get("TOX_WORKERS", "-n4").split())

    for database in databases:
        if database == "sqlite":
            cmd.extend(os.environ.get("TOX_SQLITE", "--db sqlite").split())
        elif database == "postgresql":
            session.install(
                *nox.project.dependency_groups(pyproject, "tests_postgresql")
            )
            cmd.extend(
                os.environ.get("TOX_POSTGRESQL", "--db postgresql").split()
            )
        elif database == "mysql":
            session.install(
                *nox.project.dependency_groups(pyproject, "tests_mysql")
            )
            cmd.extend(os.environ.get("TOX_MYSQL", "--db mysql").split())
        elif database == "oracle":
            # we'd like to use oracledb but SQLAlchemy 1.4 does not have
            # oracledb support...
            session.install(
                *nox.project.dependency_groups(pyproject, "tests_oracle")
            )
            if "ORACLE_HOME" in os.environ:
                session.env["ORACLE_HOME"] = os.environ.get("ORACLE_HOME")
            if "NLS_LANG" in os.environ:
                session.env["NLS_LANG"] = os.environ.get("NLS_LANG")
            cmd.extend(os.environ.get("TOX_ORACLE", "--db oracle").split())
            cmd.extend("--write-idents db_idents.txt".split())
        elif database == "mssql":
            session.install(
                *nox.project.dependency_groups(pyproject, "tests_mssql")
            )
            cmd.extend(os.environ.get("TOX_MSSQL", "--db mssql").split())
            cmd.extend("--write-idents db_idents.txt".split())

    posargs, opts = extract_opts(session.posargs, "generate-junit")

    if opts.generate_junit:
        cmd.extend(["--junitxml", "junit-tmp.xml"])

    cmd.extend(posargs)

    try:
        session.run(*cmd)
    finally:
        # name the suites distinctly as well.   this is so that when they get
        # merged we can view each suite distinctly rather than them getting
        # overwritten with each other since they are running the same tests
        if opts.generate_junit:
            # produce individual junit files that are per-database (or as close
            # as we can get).  jenkins junit plugin will merge all the files...
            if len(databases) == 1:
                tag = "-".join(databases)
                junitfile = f"junit-{tag}.xml"
                suite_name = f"pytest-{tag}"
            else:
                junitfile = "junit-general.xml"
                suite_name = "pytest-general"

            move_junit_file("junit-tmp.xml", junitfile, suite_name)

        # Run cleanup for oracle/mssql
        for database in databases:
            if database in ["oracle", "mssql"]:
                session.run("python", "reap_dbs.py", "db_idents.txt")


@nox.session(name="pep484")
def mypy_check(session: nox.Session) -> None:
    """Run mypy type checking."""

    session.install(*nox.project.dependency_groups(pyproject, "mypy"))

    session.install("-e", ".")

    session.run(
        "mypy", "noxfile.py", "./alembic/", "--exclude", "alembic/templates"
    )


@nox.session(name="pep8")
def lint(session: nox.Session) -> None:
    """Run linting and formatting checks."""

    session.install(*nox.project.dependency_groups(pyproject, "lint"))

    file_paths = [
        "./alembic/",
        "./tests/",
        "./tools/",
        "noxfile.py",
        "docs/build/conf.py",
    ]
    session.run("flake8", *file_paths)
    session.run("black", "--check", *file_paths)


@nox.session(name="pyoptimize")
def test_pyoptimize(session: nox.Session) -> None:
    """Run the script consumption suite against .pyo files rather than .pyc"""

    session.install(*nox.project.dependency_groups(pyproject, "tests"))
    session.install(".")

    session.env["PYTHONOPTIMIZE"] = "1"
    session.env["SQLALCHEMY_WARN_20"] = "1"

    cmd = [
        "python",
        "-m",
        "pytest",
    ]
    cmd.extend(os.environ.get("TOX_WORKERS", "-n4").split())
    cmd.append("tests/test_script_consumption.py")

    posargs, opts = extract_opts(session.posargs, "generate-junit")
    if opts.generate_junit:
        cmd.extend(["--junitxml", "junit-general.xml"])

    cmd.extend(posargs)

    session.run(*cmd)
