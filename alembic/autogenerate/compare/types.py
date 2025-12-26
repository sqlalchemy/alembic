from __future__ import annotations

import logging
from typing import Any
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

from sqlalchemy import types as sqltypes

from ...util import DispatchPriority
from ...util import PriorityDispatchResult

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import quoted_name
    from sqlalchemy.sql.schema import Column

    from ...autogenerate.api import AutogenContext
    from ...operations.ops import AlterColumnOp
    from ...runtime.plugins import Plugin


log = logging.getLogger(__name__)


def _compare_type_setup(
    alter_column_op: AlterColumnOp,
    tname: Union[quoted_name, str],
    cname: Union[quoted_name, str],
    conn_col: Column[Any],
    metadata_col: Column[Any],
) -> bool:

    conn_type = conn_col.type
    alter_column_op.existing_type = conn_type
    metadata_type = metadata_col.type
    if conn_type._type_affinity is sqltypes.NullType:
        log.info(
            "Couldn't determine database type for column '%s.%s'",
            tname,
            cname,
        )
        return False
    if metadata_type._type_affinity is sqltypes.NullType:
        log.info(
            "Column '%s.%s' has no type within the model; can't compare",
            tname,
            cname,
        )
        return False

    return True


def _user_compare_type(
    autogen_context: AutogenContext,
    alter_column_op: AlterColumnOp,
    schema: Optional[str],
    tname: Union[quoted_name, str],
    cname: Union[quoted_name, str],
    conn_col: Column[Any],
    metadata_col: Column[Any],
) -> PriorityDispatchResult:

    migration_context = autogen_context.migration_context

    if migration_context._user_compare_type is False:
        return PriorityDispatchResult.STOP

    if not _compare_type_setup(
        alter_column_op, tname, cname, conn_col, metadata_col
    ):
        return PriorityDispatchResult.CONTINUE

    if not callable(migration_context._user_compare_type):
        return PriorityDispatchResult.CONTINUE

    is_diff = migration_context._user_compare_type(
        migration_context,
        conn_col,
        metadata_col,
        conn_col.type,
        metadata_col.type,
    )
    if is_diff:
        alter_column_op.modify_type = metadata_col.type
        log.info(
            "Detected type change from %r to %r on '%s.%s'",
            conn_col.type,
            metadata_col.type,
            tname,
            cname,
        )
        return PriorityDispatchResult.STOP
    elif is_diff is False:
        # if user compare type returns False and not None,
        # it means "dont do any more type comparison"
        return PriorityDispatchResult.STOP

    return PriorityDispatchResult.CONTINUE


def _dialect_impl_compare_type(
    autogen_context: AutogenContext,
    alter_column_op: AlterColumnOp,
    schema: Optional[str],
    tname: Union[quoted_name, str],
    cname: Union[quoted_name, str],
    conn_col: Column[Any],
    metadata_col: Column[Any],
) -> PriorityDispatchResult:

    if not _compare_type_setup(
        alter_column_op, tname, cname, conn_col, metadata_col
    ):
        return PriorityDispatchResult.CONTINUE

    migration_context = autogen_context.migration_context
    is_diff = migration_context.impl.compare_type(conn_col, metadata_col)

    if is_diff:
        alter_column_op.modify_type = metadata_col.type
        log.info(
            "Detected type change from %r to %r on '%s.%s'",
            conn_col.type,
            metadata_col.type,
            tname,
            cname,
        )
        return PriorityDispatchResult.STOP

    return PriorityDispatchResult.CONTINUE


def setup(plugin: Plugin) -> None:
    plugin.add_autogenerate_comparator(
        _user_compare_type,
        "column",
        "types",
        priority=DispatchPriority.FIRST,
    )
    plugin.add_autogenerate_comparator(
        _dialect_impl_compare_type,
        "column",
        "types",
        priority=DispatchPriority.LAST,
    )
