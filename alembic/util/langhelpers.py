from __future__ import annotations

import collections
from collections.abc import Iterable
import enum
import textwrap
from typing import Any
from typing import Callable
from typing import cast
from typing import Dict
from typing import List
from typing import Mapping
from typing import MutableMapping
from typing import NoReturn
from typing import Optional
from typing import overload
from typing import Sequence
from typing import Set
from typing import Tuple
from typing import Type
from typing import TypeVar
import uuid
import warnings

from sqlalchemy.util import asbool as asbool  # noqa: F401
from sqlalchemy.util import immutabledict as immutabledict  # noqa: F401
from sqlalchemy.util import to_list as to_list  # noqa: F401
from sqlalchemy.util import unique_list as unique_list

from .compat import inspect_getfullargspec

if True:
    # zimports workaround :(
    from sqlalchemy.util import (  # noqa: F401
        memoized_property as memoized_property,
    )


EMPTY_DICT: Mapping[Any, Any] = immutabledict()
_T = TypeVar("_T", bound=Any)

_C = TypeVar("_C", bound=Callable[..., Any])


class _ModuleClsMeta(type):
    def __setattr__(cls, key: str, value: Callable[..., Any]) -> None:
        super().__setattr__(key, value)
        cls._update_module_proxies(key)  # type: ignore


class ModuleClsProxy(metaclass=_ModuleClsMeta):
    """Create module level proxy functions for the
    methods on a given class.

    The functions will have a compatible signature
    as the methods.

    """

    _setups: Dict[
        Type[Any],
        Tuple[
            Set[str],
            List[Tuple[MutableMapping[str, Any], MutableMapping[str, Any]]],
        ],
    ] = collections.defaultdict(lambda: (set(), []))

    @classmethod
    def _update_module_proxies(cls, name: str) -> None:
        attr_names, modules = cls._setups[cls]
        for globals_, locals_ in modules:
            cls._add_proxied_attribute(name, globals_, locals_, attr_names)

    def _install_proxy(self) -> None:
        attr_names, modules = self._setups[self.__class__]
        for globals_, locals_ in modules:
            globals_["_proxy"] = self
            for attr_name in attr_names:
                globals_[attr_name] = getattr(self, attr_name)

    def _remove_proxy(self) -> None:
        attr_names, modules = self._setups[self.__class__]
        for globals_, locals_ in modules:
            globals_["_proxy"] = None
            for attr_name in attr_names:
                del globals_[attr_name]

    @classmethod
    def create_module_class_proxy(
        cls,
        globals_: MutableMapping[str, Any],
        locals_: MutableMapping[str, Any],
    ) -> None:
        attr_names, modules = cls._setups[cls]
        modules.append((globals_, locals_))
        cls._setup_proxy(globals_, locals_, attr_names)

    @classmethod
    def _setup_proxy(
        cls,
        globals_: MutableMapping[str, Any],
        locals_: MutableMapping[str, Any],
        attr_names: Set[str],
    ) -> None:
        for methname in dir(cls):
            cls._add_proxied_attribute(methname, globals_, locals_, attr_names)

    @classmethod
    def _add_proxied_attribute(
        cls,
        methname: str,
        globals_: MutableMapping[str, Any],
        locals_: MutableMapping[str, Any],
        attr_names: Set[str],
    ) -> None:
        if not methname.startswith("_"):
            meth = getattr(cls, methname)
            if callable(meth):
                locals_[methname] = cls._create_method_proxy(
                    methname, globals_, locals_
                )
            else:
                attr_names.add(methname)

    @classmethod
    def _create_method_proxy(
        cls,
        name: str,
        globals_: MutableMapping[str, Any],
        locals_: MutableMapping[str, Any],
    ) -> Callable[..., Any]:
        fn = getattr(cls, name)

        def _name_error(name: str, from_: Exception) -> NoReturn:
            raise NameError(
                "Can't invoke function '%s', as the proxy object has "
                "not yet been "
                "established for the Alembic '%s' class.  "
                "Try placing this code inside a callable."
                % (name, cls.__name__)
            ) from from_

        globals_["_name_error"] = _name_error

        translations = getattr(fn, "_legacy_translations", [])
        if translations:
            spec = inspect_getfullargspec(fn)
            if spec[0] and spec[0][0] == "self":
                spec[0].pop(0)

            outer_args = inner_args = "*args, **kw"
            translate_str = "args, kw = _translate(%r, %r, %r, args, kw)" % (
                fn.__name__,
                tuple(spec),
                translations,
            )

            def translate(
                fn_name: str, spec: Any, translations: Any, args: Any, kw: Any
            ) -> Any:
                return_kw = {}
                return_args = []

                for oldname, newname in translations:
                    if oldname in kw:
                        warnings.warn(
                            "Argument %r is now named %r "
                            "for method %s()." % (oldname, newname, fn_name)
                        )
                        return_kw[newname] = kw.pop(oldname)
                return_kw.update(kw)

                args = list(args)
                if spec[3]:
                    pos_only = spec[0][: -len(spec[3])]
                else:
                    pos_only = spec[0]
                for arg in pos_only:
                    if arg not in return_kw:
                        try:
                            return_args.append(args.pop(0))
                        except IndexError:
                            raise TypeError(
                                "missing required positional argument: %s"
                                % arg
                            )
                return_args.extend(args)

                return return_args, return_kw

            globals_["_translate"] = translate
        else:
            outer_args = "*args, **kw"
            inner_args = "*args, **kw"
            translate_str = ""

        func_text = textwrap.dedent(
            """\
        def %(name)s(%(args)s):
            %(doc)r
            %(translate)s
            try:
                p = _proxy
            except NameError as ne:
                _name_error('%(name)s', ne)
            return _proxy.%(name)s(%(apply_kw)s)
            e
        """
            % {
                "name": name,
                "translate": translate_str,
                "args": outer_args,
                "apply_kw": inner_args,
                "doc": fn.__doc__,
            }
        )
        lcl: MutableMapping[str, Any] = {}

        exec(func_text, cast("Dict[str, Any]", globals_), lcl)
        return cast("Callable[..., Any]", lcl[name])


def _with_legacy_names(translations: Any) -> Any:
    def decorate(fn: _C) -> _C:
        fn._legacy_translations = translations  # type: ignore[attr-defined]
        return fn

    return decorate


def rev_id() -> str:
    return uuid.uuid4().hex[-12:]


@overload
def to_tuple(x: Any, default: Tuple[Any, ...]) -> Tuple[Any, ...]: ...


@overload
def to_tuple(x: None, default: Optional[_T] = ...) -> _T: ...


@overload
def to_tuple(
    x: Any, default: Optional[Tuple[Any, ...]] = None
) -> Tuple[Any, ...]: ...


def to_tuple(
    x: Any, default: Optional[Tuple[Any, ...]] = None
) -> Optional[Tuple[Any, ...]]:
    if x is None:
        return default
    elif isinstance(x, str):
        return (x,)
    elif isinstance(x, Iterable):
        return tuple(x)
    else:
        return (x,)


def dedupe_tuple(tup: Tuple[str, ...]) -> Tuple[str, ...]:
    return tuple(unique_list(tup))


class PriorityDispatchResult(enum.Enum):
    """indicate an action after running a function within a
    :class:`.PriorityDispatcher`

    .. versionadded:: 1.18.0

    """

    CONTINUE = enum.auto()
    """Continue running more functions.

    Any return value that is not PriorityDispatchResult.STOP is equivalent
    to this.

    """

    STOP = enum.auto()
    """Stop running any additional functions within the subgroup"""


class DispatchPriority(enum.IntEnum):
    """Indicate which of three sub-collections a function inside a
    :class:`.PriorityDispatcher` should be placed.

    .. versionadded:: 1.18.0

    """

    FIRST = 50
    """Run the funciton in the first batch of functions (highest priority)"""

    MEDIUM = 25
    """Run the function at normal priority (this is the default)"""

    LAST = 10
    """Run the function in the last batch of functions"""


class Dispatcher:
    def __init__(self) -> None:
        self._registry: Dict[Tuple[Any, ...], Any] = {}

    def dispatch_for(
        self,
        target: Any,
        *,
        qualifier: str = "default",
        replace: bool = False,
    ) -> Callable[[_C], _C]:
        def decorate(fn: _C) -> _C:
            if (target, qualifier) in self._registry and not replace:
                raise ValueError(
                    "Can not set dispatch function for object "
                    f"{target!r}: key already exists. To replace "
                    "existing function, use replace=True."
                )
            self._registry[(target, qualifier)] = fn
            return fn

        return decorate

    def dispatch(self, obj: Any, qualifier: str = "default") -> Any:
        if isinstance(obj, str):
            targets: Sequence[Any] = [obj]
        elif isinstance(obj, type):
            targets = obj.__mro__
        else:
            targets = type(obj).__mro__

        if qualifier != "default":
            qualifiers = [qualifier, "default"]
        else:
            qualifiers = ["default"]

        for spcls in targets:
            for qualifier in qualifiers:
                if (spcls, qualifier) in self._registry:
                    return self._registry[(spcls, qualifier)]
        else:
            raise ValueError("no dispatch function for object: %s" % obj)

    def branch(self) -> Dispatcher:
        """Return a copy of this dispatcher that is independently
        writable."""

        d = Dispatcher()
        d._registry.update(self._registry)
        return d


class PriorityDispatcher:
    """registers lists of functions at multiple levels of priorty and provides
    a target to invoke them in priority order.

    .. versionadded:: 1.18.0 - PriorityDispatcher replaces the job
       of Dispatcher(uselist=True)

    """

    def __init__(self) -> None:
        self._registry: dict[tuple[Any, ...], Any] = collections.defaultdict(
            list
        )

    def dispatch_for(
        self,
        target: str,
        *,
        priority: DispatchPriority = DispatchPriority.MEDIUM,
        qualifier: str = "default",
        subgroup: str | None = None,
    ) -> Callable[[_C], _C]:
        """return a decorator callable that registers a function at a
        given priority, with a given qualifier, to fire off for a given
        subgroup.

        It's important this remains as a decorator to support third party
        plugins who are populating the dispatcher using that style.

        """

        def decorate(fn: _C) -> _C:
            self._registry[(target, qualifier, priority)].append(
                (fn, subgroup)
            )
            return fn

        return decorate

    def dispatch(
        self, target: str, *, qualifier: str = "default"
    ) -> Callable[..., None]:
        """Provide a callable for the given target and qualifier."""

        if qualifier != "default":
            qualifiers = [qualifier, "default"]
        else:
            qualifiers = ["default"]

        def go(*arg: Any, **kw: Any) -> Any:
            results_by_subgroup: dict[str, PriorityDispatchResult] = {}
            for priority in DispatchPriority:
                for qualifier in qualifiers:
                    for fn, subgroup in self._registry.get(
                        (target, qualifier, priority), ()
                    ):
                        if (
                            results_by_subgroup.get(
                                subgroup, PriorityDispatchResult.CONTINUE
                            )
                            is PriorityDispatchResult.STOP
                        ):
                            continue

                        result = fn(*arg, **kw)
                        results_by_subgroup[subgroup] = result

        return go

    def branch(self) -> PriorityDispatcher:
        """Return a copy of this dispatcher that is independently
        writable."""

        d = PriorityDispatcher()
        d.populate_with(self)
        return d

    def populate_with(self, other: PriorityDispatcher) -> None:
        """Populate this PriorityDispatcher with the contents of another one.

        Additive, does not remove existing contents.
        """
        for k in other._registry:
            new_list = other._registry[k]
            self._registry[k].extend(new_list)


def not_none(value: Optional[_T]) -> _T:
    assert value is not None
    return value
