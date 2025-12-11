from __future__ import annotations

import logging
from typing import Any
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

from ...operations import ops
from ...util import PriorityDispatchResult

if TYPE_CHECKING:

    from sqlalchemy.sql.elements import quoted_name
    from sqlalchemy.sql.schema import Column
    from sqlalchemy.sql.schema import Table

    from ..api import AutogenContext
    from ...operations.ops import AlterColumnOp
    from ...operations.ops import ModifyTableOps
    from ...runtime.plugins import Plugin

log = logging.getLogger(__name__)


def _compare_column_comment(
    autogen_context: AutogenContext,
    alter_column_op: AlterColumnOp,
    schema: Optional[str],
    tname: Union[quoted_name, str],
    cname: quoted_name,
    conn_col: Column[Any],
    metadata_col: Column[Any],
) -> PriorityDispatchResult:
    assert autogen_context.dialect is not None
    if not autogen_context.dialect.supports_comments:
        return PriorityDispatchResult.CONTINUE

    metadata_comment = metadata_col.comment
    conn_col_comment = conn_col.comment
    if conn_col_comment is None and metadata_comment is None:
        return PriorityDispatchResult.CONTINUE

    alter_column_op.existing_comment = conn_col_comment

    if conn_col_comment != metadata_comment:
        alter_column_op.modify_comment = metadata_comment
        log.info("Detected column comment '%s.%s'", tname, cname)

        return PriorityDispatchResult.STOP
    else:
        return PriorityDispatchResult.CONTINUE


def _compare_table_comment(
    autogen_context: AutogenContext,
    modify_table_ops: ModifyTableOps,
    schema: Optional[str],
    tname: Union[quoted_name, str],
    conn_table: Optional[Table],
    metadata_table: Optional[Table],
) -> PriorityDispatchResult:
    assert autogen_context.dialect is not None
    if not autogen_context.dialect.supports_comments:
        return PriorityDispatchResult.CONTINUE

    # if we're doing CREATE TABLE, comments will be created inline
    # with the create_table op.
    if conn_table is None or metadata_table is None:
        return PriorityDispatchResult.CONTINUE

    if conn_table.comment is None and metadata_table.comment is None:
        return PriorityDispatchResult.CONTINUE

    if metadata_table.comment is None and conn_table.comment is not None:
        modify_table_ops.ops.append(
            ops.DropTableCommentOp(
                tname, existing_comment=conn_table.comment, schema=schema
            )
        )
        return PriorityDispatchResult.STOP
    elif metadata_table.comment != conn_table.comment:
        modify_table_ops.ops.append(
            ops.CreateTableCommentOp(
                tname,
                metadata_table.comment,
                existing_comment=conn_table.comment,
                schema=schema,
            )
        )
        return PriorityDispatchResult.STOP

    return PriorityDispatchResult.CONTINUE


def setup(plugin: Plugin) -> None:
    plugin.add_autogenerate_comparator(
        _compare_column_comment,
        "column",
        "comments",
    )
    plugin.add_autogenerate_comparator(
        _compare_table_comment,
        "table",
        "comments",
    )
