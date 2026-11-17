#!/usr/bin/env python
"""
pytest plugin script.

This script is an extension to py.test which
installs SQLAlchemy's testing plugin into the local environment.

"""

import inspect
import os

import pytest

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

    @pytest.hookimpl(wrapper=True)
    def pytest_fixture_setup(fixturedef, request):
        result = yield

        # pytest only runs a fixture as a generator if
        # inspect.isgeneratorfunction() is true for it.  a decorator that
        # wraps a generator function in a plain function, such as an
        # exclusions / requirements rule under SQLAlchemy 2.0.52 and
        # earlier, defeats that; pytest then hands the un-iterated
        # generator to the test as the fixture value, so neither setup nor
        # teardown ever runs.  fail loudly rather than silently.
        if inspect.isgenerator(result):
            raise TypeError(
                f"fixture {fixturedef.argname!r} returned a generator object "
                "rather than being run as a generator fixture; a decorator "
                "applied to it most likely does not preserve generator "
                "functions.  Apply exclusions / requirements to the tests "
                "or class that use the fixture instead."
            )
        return result
