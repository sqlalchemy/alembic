"""vendored pytestplugin functions from the most recent SQLAlchemy versions.

Alembic tests need to run on older versions of SQLAlchemy that don't
necessarily have all the latest testing fixtures.

"""
try:
    # installed by bootstrap.py
    import sqla_plugin_base as plugin_base
except ImportError:
    # assume we're a package, use traditional import
    from . import plugin_base

import inspect
import itertools
import operator
import os
import re
import sys

import pytest
from sqlalchemy.testing.plugin.pytestplugin import *  # noqa
from sqlalchemy.testing.plugin.pytestplugin import pytest_configure as spc


# override selected SQLAlchemy pytest hooks with vendored functionality
def pytest_configure(config):
    spc(config)

    plugin_base.set_fixture_functions(PytestFixtureFunctions)


def pytest_pycollect_makeitem(collector, name, obj):

    if inspect.isclass(obj) and plugin_base.want_class(name, obj):
        return [
            pytest.Class(parametrize_cls.__name__, parent=collector)
            for parametrize_cls in _parametrize_cls(collector.module, obj)
        ]
    elif (
        inspect.isfunction(obj)
        and isinstance(collector, pytest.Instance)
        and plugin_base.want_method(collector.cls, obj)
    ):
        # None means, fall back to default logic, which includes
        # method-level parametrize
        return None
    else:
        # empty list means skip this item
        return []


_current_class = None


def _parametrize_cls(module, cls):
    """implement a class-based version of pytest parametrize."""

    if "_sa_parametrize" not in cls.__dict__:
        return [cls]

    _sa_parametrize = cls._sa_parametrize
    classes = []
    for full_param_set in itertools.product(
        *[params for argname, params in _sa_parametrize]
    ):
        cls_variables = {}

        for argname, param in zip(
            [_sa_param[0] for _sa_param in _sa_parametrize], full_param_set
        ):
            if not argname:
                raise TypeError("need argnames for class-based combinations")
            argname_split = re.split(r",\s*", argname)
            for arg, val in zip(argname_split, param.values):
                cls_variables[arg] = val
        parametrized_name = "_".join(
            # token is a string, but in py2k py.test is giving us a unicode,
            # so call str() on it.
            str(re.sub(r"\W", "", token))
            for param in full_param_set
            for token in param.id.split("-")
        )
        name = "%s_%s" % (cls.__name__, parametrized_name)
        newcls = type.__new__(type, name, (cls,), cls_variables)
        setattr(module, name, newcls)
        classes.append(newcls)
    return classes


def getargspec(fn):
    if sys.version_info.major == 3:
        return inspect.getfullargspec(fn)
    else:
        return inspect.getargspec(fn)


class PytestFixtureFunctions(plugin_base.FixtureFunctions):
    def skip_test_exception(self, *arg, **kw):
        return pytest.skip.Exception(*arg, **kw)

    _combination_id_fns = {
        "i": lambda obj: obj,
        "r": repr,
        "s": str,
        "n": operator.attrgetter("__name__"),
    }

    def combinations(self, *arg_sets, **kw):
        """facade for pytest.mark.paramtrize.

        Automatically derives argument names from the callable which in our
        case is always a method on a class with positional arguments.

        ids for parameter sets are derived using an optional template.

        """
        from alembic.testing import exclusions

        if sys.version_info.major == 3:
            if len(arg_sets) == 1 and hasattr(arg_sets[0], "__next__"):
                arg_sets = list(arg_sets[0])
        else:
            if len(arg_sets) == 1 and hasattr(arg_sets[0], "next"):
                arg_sets = list(arg_sets[0])

        argnames = kw.pop("argnames", None)

        exclusion_combinations = []

        def _filter_exclusions(args):
            result = []
            gathered_exclusions = []
            for a in args:
                if isinstance(a, exclusions.compound):
                    gathered_exclusions.append(a)
                else:
                    result.append(a)

            exclusion_combinations.extend(
                [(exclusion, result) for exclusion in gathered_exclusions]
            )
            return result

        id_ = kw.pop("id_", None)

        if id_:
            _combination_id_fns = self._combination_id_fns

            # because itemgetter is not consistent for one argument vs.
            # multiple, make it multiple in all cases and use a slice
            # to omit the first argument
            _arg_getter = operator.itemgetter(
                0,
                *[
                    idx
                    for idx, char in enumerate(id_)
                    if char in ("n", "r", "s", "a")
                ]
            )
            fns = [
                (operator.itemgetter(idx), _combination_id_fns[char])
                for idx, char in enumerate(id_)
                if char in _combination_id_fns
            ]
            arg_sets = [
                pytest.param(
                    *_arg_getter(_filter_exclusions(arg))[1:],
                    id="-".join(
                        comb_fn(getter(arg)) for getter, comb_fn in fns
                    )
                )
                for arg in [
                    (arg,) if not isinstance(arg, tuple) else arg
                    for arg in arg_sets
                ]
            ]
        else:
            # ensure using pytest.param so that even a 1-arg paramset
            # still needs to be a tuple.  otherwise paramtrize tries to
            # interpret a single arg differently than tuple arg
            arg_sets = [
                pytest.param(*_filter_exclusions(arg))
                for arg in [
                    (arg,) if not isinstance(arg, tuple) else arg
                    for arg in arg_sets
                ]
            ]

        def decorate(fn):
            if inspect.isclass(fn):
                if "_sa_parametrize" not in fn.__dict__:
                    fn._sa_parametrize = []
                fn._sa_parametrize.append((argnames, arg_sets))
                return fn
            else:
                if argnames is None:
                    _argnames = getargspec(fn).args[1:]
                else:
                    _argnames = argnames

                if exclusion_combinations:
                    for exclusion, combination in exclusion_combinations:
                        combination_by_kw = {
                            argname: val
                            for argname, val in zip(_argnames, combination)
                        }
                        exclusion = exclusion.with_combination(
                            **combination_by_kw
                        )
                        fn = exclusion(fn)
                return pytest.mark.parametrize(_argnames, arg_sets)(fn)

        return decorate

    def param_ident(self, *parameters):
        ident = parameters[0]
        return pytest.param(*parameters[1:], id=ident)

    def fixture(self, *arg, **kw):
        return pytest.fixture(*arg, **kw)

    def get_current_test_name(self):
        return os.environ.get("PYTEST_CURRENT_TEST")
