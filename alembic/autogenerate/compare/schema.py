# mypy: allow-untyped-calls

from __future__ import annotations

import logging
from typing import Optional
from typing import Set
from typing import TYPE_CHECKING

from sqlalchemy import inspect

from ...util import PriorityDispatchResult

if TYPE_CHECKING:
    from sqlalchemy.engine.reflection import Inspector

    from ...autogenerate.api import AutogenContext
    from ...operations.ops import UpgradeOps
    from ...runtime.plugins import Plugin


log = logging.getLogger(__name__)


def _produce_net_changes(
    autogen_context: AutogenContext, upgrade_ops: UpgradeOps
) -> PriorityDispatchResult:
    connection = autogen_context.connection
    assert connection is not None
    include_schemas = autogen_context.opts.get("include_schemas", False)

    inspector: Inspector = inspect(connection)

    default_schema = connection.dialect.default_schema_name
    schemas: Set[Optional[str]]
    if include_schemas:
        schemas = set(inspector.get_schema_names())
        # replace default schema name with None
        schemas.discard("information_schema")
        # replace the "default" schema with None
        schemas.discard(default_schema)
        schemas.add(None)
    else:
        schemas = {None}

    schemas = {
        s for s in schemas if autogen_context.run_name_filters(s, "schema", {})
    }

    assert autogen_context.dialect is not None
    autogen_context.comparators.dispatch(
        "schema", qualifier=autogen_context.dialect.name
    )(autogen_context, upgrade_ops, schemas)

    return PriorityDispatchResult.CONTINUE


def setup(plugin: Plugin) -> None:
    plugin.add_autogenerate_comparator(
        _produce_net_changes,
        "autogenerate",
    )
