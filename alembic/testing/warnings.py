# testing/warnings.py
# Copyright (C) 2005-2021 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php


import warnings

from sqlalchemy import exc as sa_exc


def setup_filters():
    """Set global warning behavior for the test suite."""

    warnings.resetwarnings()

    warnings.filterwarnings("error", category=sa_exc.SADeprecationWarning)
    warnings.filterwarnings("error", category=sa_exc.SAWarning)

    # some selected deprecations...
    warnings.filterwarnings("error", category=DeprecationWarning)

    # Python 3.15 emits this from linecache when a traceback is formatted
    # for a frame belonging to a module that has no __spec__, which is the
    # case for Mako's string-based template modules.  Fixed in Mako via
    # https://github.com/sqlalchemy/mako/issues/437; remove this filter
    # once a Mako release including that fix is required.
    warnings.filterwarnings(
        "ignore",
        r"Module globals is missing a __spec__\.loader",
        DeprecationWarning,
    )

    try:
        import pytest
    except ImportError:
        pass
    else:
        warnings.filterwarnings(
            "once", category=pytest.PytestDeprecationWarning
        )
