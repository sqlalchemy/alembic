"""vendored plugin_base functions from the most recent SQLAlchemy versions.

Alembic tests need to run on older versions of SQLAlchemy that don't
necessarily have all the latest testing fixtures.

"""
from __future__ import absolute_import

import abc
import sys

from sqlalchemy.testing.plugin.plugin_base import *  # noqa
from sqlalchemy.testing.plugin.plugin_base import post
from sqlalchemy.testing.plugin.plugin_base import post_begin as sqla_post_begin
from sqlalchemy.testing.plugin.plugin_base import stop_test_class as sqla_stc

py3k = sys.version_info >= (3, 0)


if py3k:

    ABC = abc.ABC
else:

    class ABC(object):
        __metaclass__ = abc.ABCMeta


def post_begin():
    sqla_post_begin()

    import warnings

    try:
        import pytest
    except ImportError:
        pass
    else:
        warnings.filterwarnings(
            "once", category=pytest.PytestDeprecationWarning
        )

    from sqlalchemy import exc

    if hasattr(exc, "RemovedIn20Warning"):
        warnings.filterwarnings(
            "error",
            category=exc.RemovedIn20Warning,
            message=".*Engine.execute",
        )
        warnings.filterwarnings(
            "error",
            category=exc.RemovedIn20Warning,
            message=".*Passing a string",
        )


# override selected SQLAlchemy pytest hooks with vendored functionality
def stop_test_class(cls):
    sqla_stc(cls)
    import os
    from alembic.testing.env import _get_staging_directory

    assert not os.path.exists(_get_staging_directory()), (
        "staging directory %s was not cleaned up" % _get_staging_directory()
    )


def want_class(name, cls):
    from sqlalchemy.testing import config
    from sqlalchemy.testing import fixtures

    if not issubclass(cls, fixtures.TestBase):
        return False
    elif name.startswith("_"):
        return False
    elif (
        config.options.backend_only
        and not getattr(cls, "__backend__", False)
        and not getattr(cls, "__sparse_backend__", False)
    ):
        return False
    else:
        return True


@post
def _init_symbols(options, file_config):
    from sqlalchemy.testing import config
    from alembic.testing import fixture_functions as alembic_config

    config._fixture_functions = (
        alembic_config._fixture_functions
    ) = _fixture_fn_class()


class FixtureFunctions(ABC):
    @abc.abstractmethod
    def skip_test_exception(self, *arg, **kw):
        raise NotImplementedError()

    @abc.abstractmethod
    def combinations(self, *args, **kw):
        raise NotImplementedError()

    @abc.abstractmethod
    def param_ident(self, *args, **kw):
        raise NotImplementedError()

    @abc.abstractmethod
    def fixture(self, *arg, **kw):
        raise NotImplementedError()

    def get_current_test_name(self):
        raise NotImplementedError()


_fixture_fn_class = None


def set_fixture_functions(fixture_fn_class):
    from sqlalchemy.testing.plugin import plugin_base

    global _fixture_fn_class
    _fixture_fn_class = plugin_base._fixture_fn_class = fixture_fn_class
