#!/usr/bin/env python
"""
pytest plugin script.

This script is an extension to py.test which
installs SQLAlchemy's testing plugin into the local environment.

"""
import os

import pytest

os.environ["SQLALCHEMY_WARN_20"] = "true"

pytest.register_assert_rewrite("sqlalchemy.testing.assertions")


# ideally, SQLAlchemy would allow us to just import bootstrap,
# but for now we have to use its "load from a file" approach

# use bootstrapping so that test plugins are loaded
# without touching the main library before coverage starts
bootstrap_file = os.path.join(
    os.path.dirname(__file__),
    "..",
    "alembic",
    "testing",
    "plugin",
    "bootstrap.py",
)


with open(bootstrap_file) as f:
    code = compile(f.read(), "bootstrap.py", "exec")
    to_bootstrap = "pytest"
    exec(code, globals(), locals())

    try:
        from sqlalchemy.testing import asyncio
    except ImportError:
        pass
    else:
        asyncio.ENABLE_ASYNCIO = False

    from sqlalchemy.testing.plugin.pytestplugin import *  # noqa

    wrap_pytest_sessionstart = pytest_sessionstart  # noqa

    def pytest_sessionstart(session):
        wrap_pytest_sessionstart(session)
        from alembic.testing import warnings

        warnings.setup_filters()
