"""Nox configuration for Alembic."""

from __future__ import annotations

from glob import glob
import os
import shutil
import sys

import nox
from packaging.version import parse as parse_version

nox.needs_version = ">=2025.10.16"

if True:
    sys.path.insert(0, ".")
    from tools.toxnox import tox_parameters
    from tools.toxnox import apply_pytest_opts


SQLA_REPO = os.environ.get(
    "SQLA_REPO", "git+https://github.com/sqlalchemy/sqlalchemy.git"
)

PYTHON_VERSIONS = [
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
BACKEND = ["_nobackend", "backendonly"]

pyproject = nox.project.load_toml("pyproject.toml")

nox.options.sessions = ["tests"]
nox.options.tags = ["py"]


def filter_sqla(
    python: str,
    sqlalchemy: str,
    database: str | None = None,
    backendonly: str | None = None,
) -> bool:
    python_version = parse_version(python.rstrip("t"))
    if sqlalchemy == "sqla14":
        return python_version < parse_version("3.14")
    elif sqlalchemy == "sqlamain":
        return python_version >= parse_version("3.10")
    else:
        return True


@nox.session()
@tox_parameters(
    ["python", "sqlalchemy", "database", "backendonly"],
    [PYTHON_VERSIONS, SQLALCHEMY_VERSIONS, DATABASES, BACKEND],
    filter_=filter_sqla,
)
def tests(
    session: nox.Session,
    sqlalchemy: str,
    database: str,
    backendonly: str,
) -> None:
    """Run the main test suite against one database at a time"""

    _tests(
        session,
        sqlalchemy,
        database,
        backendonly=backendonly == "backendonly",
    )


@nox.session(name="coverage")
@tox_parameters(["database"], [DATABASES], base_tag="coverage")
def coverage(session: nox.Session, database: str) -> None:
    """Run tests with coverage."""

    _tests(session, "default", database, coverage=True)


def _tests(
    session: nox.Session,
    sqlalchemy: str,
    database: str,
    *,
    coverage: bool = False,
    backendonly: bool = False,
) -> None:
    match sqlalchemy:
        case "sqla14":
            session.install(f"{SQLA_REPO}@rel_1_4#egg=sqlalchemy")
        case "sqla20":
            session.install(f"{SQLA_REPO}@rel_2_0#egg=sqlalchemy")
        case "sqlamain":
            session.install(f"{SQLA_REPO}#egg=sqlalchemy")

    # for sqlalchemy == "default", the alembic install will install
    # current released SQLAlchemy version as a dependency
    shutil.rmtree("build/", ignore_errors=True)
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

    # for all sqlalchemy-custom options, use equals sign so that we avoid
    # https://github.com/pytest-dev/pytest/issues/13913

    match database:
        case "sqlite":
            cmd.extend(os.environ.get("TOX_SQLITE", "--db=sqlite").split())
        case "postgresql":
            session.install(
                *nox.project.dependency_groups(pyproject, "tests_postgresql")
            )
            cmd.extend(
                os.environ.get("TOX_POSTGRESQL", "--db=postgresql").split()
            )
        case "mysql":
            session.install(
                *nox.project.dependency_groups(pyproject, "tests_mysql")
            )
            cmd.extend(os.environ.get("TOX_MYSQL", "--db=mysql").split())
        case "oracle":
            # we'd like to use oracledb but SQLAlchemy 1.4 does not have
            # oracledb support...
            session.install(
                *nox.project.dependency_groups(pyproject, "tests_oracle")
            )
            if "ORACLE_HOME" in os.environ:
                session.env["ORACLE_HOME"] = os.environ.get("ORACLE_HOME")
            if "NLS_LANG" in os.environ:
                session.env["NLS_LANG"] = os.environ.get("NLS_LANG")
            cmd.extend(os.environ.get("TOX_ORACLE", "--db=oracle").split())
            cmd.append("--write-idents=db_idents.txt")
        case "mssql":
            session.install(
                *nox.project.dependency_groups(pyproject, "tests_mssql")
            )
            cmd.extend(os.environ.get("TOX_MSSQL", "--db=mssql").split())
            cmd.append("--write-idents=db_idents.txt")

    if backendonly:
        cmd.append("--backend-only")

    posargs = apply_pytest_opts(
        session,
        "alembic",
        [
            sqlalchemy,
            database,
        ],
        coverage=coverage,
    )

    cmd.extend(posargs)

    try:
        session.run(*cmd)
    finally:
        # Run cleanup for oracle/mssql
        if database in ["oracle", "mssql"]:
            session.run("python", "reap_dbs.py", "db_idents.txt")

        # Clean up scratch directories
        for scratch_dir in glob("scratch*"):
            if os.path.isdir(scratch_dir):
                shutil.rmtree(scratch_dir)


@nox.session(name="pep484")
def mypy_check(session: nox.Session) -> None:
    """Run mypy type checking."""

    shutil.rmtree("build/", ignore_errors=True)
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

    posargs = apply_pytest_opts(
        session,
        "alembic",
        [
            "pyoptimize",
        ],
    )

    cmd.extend(posargs)

    session.run(*cmd)
