from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from . import comments
from . import constraints
from . import schema
from . import server_defaults
from . import tables
from . import types
from ... import util
from ...runtime.plugins import Plugin

if TYPE_CHECKING:
    from ..api import AutogenContext
    from ...operations.ops import MigrationScript
    from ...operations.ops import UpgradeOps


log = logging.getLogger(__name__)

comparators = util.PriorityDispatcher()
"""global registry which alembic keeps empty, but copies when creating
a new AutogenContext.

This is to support a variety of third party plugins that hook their autogen
functionality onto this collection.

"""


def _populate_migration_script(
    autogen_context: AutogenContext, migration_script: MigrationScript
) -> None:
    upgrade_ops = migration_script.upgrade_ops_list[-1]
    downgrade_ops = migration_script.downgrade_ops_list[-1]

    _produce_net_changes(autogen_context, upgrade_ops)
    upgrade_ops.reverse_into(downgrade_ops)


def _produce_net_changes(
    autogen_context: AutogenContext, upgrade_ops: UpgradeOps
) -> None:
    assert autogen_context.dialect is not None

    autogen_context.comparators.dispatch(
        "autogenerate", qualifier=autogen_context.dialect.name
    )(autogen_context, upgrade_ops)


Plugin.setup_plugin_from_module(schema, "alembic.autogenerate.schemas")
Plugin.setup_plugin_from_module(tables, "alembic.autogenerate.tables")
Plugin.setup_plugin_from_module(types, "alembic.autogenerate.types")
Plugin.setup_plugin_from_module(
    constraints, "alembic.autogenerate.constraints"
)
Plugin.setup_plugin_from_module(
    server_defaults, "alembic.autogenerate.defaults"
)
Plugin.setup_plugin_from_module(comments, "alembic.autogenerate.comments")
