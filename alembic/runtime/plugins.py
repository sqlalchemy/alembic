from __future__ import annotations

from importlib import metadata
import logging
import re
from types import ModuleType
from typing import Callable
from typing import Pattern
from typing import TYPE_CHECKING

from .. import util
from ..util import DispatchPriority
from ..util import PriorityDispatcher

if TYPE_CHECKING:
    from ..util import PriorityDispatchResult

_all_plugins = {}


log = logging.getLogger(__name__)


class Plugin:
    """Describe a series of functions that are pulled in as a plugin.

    This is initially to provide for portable lists of autogenerate
    comparison functions, however the setup for a plugin can run any
    other kinds of global registration as well.

    .. versionadded:: 1.18.0

    """

    def __init__(self, name: str):
        self.name = name
        log.info("setup plugin %s", name)
        if name in _all_plugins:
            raise ValueError(f"A plugin named {name} is already registered")
        _all_plugins[name] = self
        self.autogenerate_comparators = PriorityDispatcher()

    def remove(self) -> None:
        """remove this plugin"""

        del _all_plugins[self.name]

    def add_autogenerate_comparator(
        self,
        fn: Callable[..., PriorityDispatchResult],
        compare_target: str,
        compare_element: str | None = None,
        *,
        qualifier: str = "default",
        priority: DispatchPriority = DispatchPriority.MEDIUM,
    ) -> None:
        """Register an autogenerate comparison function.

        See the section :ref:`plugins_registering_autogenerate` for detailed
        examples on how to use this method.

        :param fn: The comparison function to register. The function receives
         arguments specific to the type of comparison being performed and
         should return a :class:`.PriorityDispatchResult` value.

        :param compare_target: The type of comparison being performed
         (e.g., ``"table"``, ``"column"``, ``"type"``).

        :param compare_element: Optional sub-element being compared within
         the target type.

        :param qualifier: Database dialect qualifier. Use ``"default"`` for
         all dialects, or specify a dialect name like ``"postgresql"`` to
         register a dialect-specific handler. Defaults to ``"default"``.

        :param priority: Execution priority for this comparison function.
         Functions are executed in priority order from
         :attr:`.DispatchPriority.FIRST` to :attr:`.DispatchPriority.LAST`.
         Defaults to :attr:`.DispatchPriority.MEDIUM`.

        """
        self.autogenerate_comparators.dispatch_for(
            compare_target,
            subgroup=compare_element,
            priority=priority,
            qualifier=qualifier,
        )(fn)

    @classmethod
    def populate_autogenerate_priority_dispatch(
        cls, comparators: PriorityDispatcher, include_plugins: list[str]
    ) -> None:
        """Populate all current autogenerate comparison functions into
        a given PriorityDispatcher."""

        exclude: set[Pattern[str]] = set()
        include: dict[str, Pattern[str]] = {}

        matched_expressions: set[str] = set()

        for name in include_plugins:
            if name.startswith("~"):
                exclude.add(_make_re(name[1:]))
            else:
                include[name] = _make_re(name)

        for plugin in _all_plugins.values():
            if any(excl.match(plugin.name) for excl in exclude):
                continue

            include_matches = [
                incl for incl in include if include[incl].match(plugin.name)
            ]
            if not include_matches:
                continue
            else:
                matched_expressions.update(include_matches)

            log.info("setting up autogenerate plugin %s", plugin.name)
            comparators.populate_with(plugin.autogenerate_comparators)

        never_matched = set(include).difference(matched_expressions)
        if never_matched:
            raise util.CommandError(
                f"Did not locate plugins: {', '.join(never_matched)}"
            )

    @classmethod
    def setup_plugin_from_module(cls, module: ModuleType, name: str) -> None:
        """Call the ``setup()`` function of a plugin module, identified by
        passing the module object itself.

        E.g.::

            from alembic.runtime.plugins import Plugin
            import myproject.alembic_plugin

            # Register the plugin manually
            Plugin.setup_plugin_from_module(
                myproject.alembic_plugin,
                "myproject.custom_operations"
            )

        This will generate a new :class:`.Plugin` object with the given
        name, which will register itself in the global list of plugins.
        Then the module's ``setup()`` function is invoked, passing that
        :class:`.Plugin` object.

        This exact process is invoked automatically at import time for any
        plugin module that is published via the ``alembic.plugins`` entrypoint.

        """
        module.setup(Plugin(name))


def _make_re(name: str) -> Pattern[str]:
    tokens = name.split(".")

    reg = r""
    for token in tokens:
        if token == "*":
            reg += r"\..+?"
        elif token.isidentifier():
            reg += r"\." + token
        else:
            raise ValueError(f"Invalid plugin expression {name!r}")

    # omit leading r'\.'
    return re.compile(f"^{reg[2:]}$")


def _setup() -> None:
    # setup third party plugins
    for entrypoint in metadata.entry_points(group="alembic.plugins"):
        for mod in entrypoint.load():
            Plugin.setup_plugin_from_module(mod, entrypoint.name)


_setup()
