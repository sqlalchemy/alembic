from __future__ import annotations

from collections.abc import Sequence
import logging
import re
from types import NoneType
from typing import Any
from typing import cast
from typing import TYPE_CHECKING

from sqlalchemy import schema as sa_schema
from sqlalchemy.sql.schema import DefaultClause

from ... import util
from ...util import DispatchPriority
from ...util import PriorityDispatchResult
from ...util import sqla_compat

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import quoted_name
    from sqlalchemy.sql.schema import Column

    from ...autogenerate.api import AutogenContext
    from ...operations.ops import AlterColumnOp
    from ...runtime.plugins import Plugin

log = logging.getLogger(__name__)


def _render_server_default_for_compare(
    metadata_default: Any, autogen_context: AutogenContext
) -> str | None:
    if isinstance(metadata_default, sa_schema.DefaultClause):
        if isinstance(metadata_default.arg, str):
            metadata_default = metadata_default.arg
        else:
            metadata_default = str(
                metadata_default.arg.compile(
                    dialect=autogen_context.dialect,
                    compile_kwargs={"literal_binds": True},
                )
            )
    if isinstance(metadata_default, str):
        return metadata_default
    else:
        return None


def _normalize_computed_default(sqltext: str) -> str:
    """we want to warn if a computed sql expression has changed.  however
    we don't want false positives and the warning is not that critical.
    so filter out most forms of variability from the SQL text.

    """

    return re.sub(r"[ \(\)'\"`\[\]\t\r\n]", "", sqltext).lower()


def _compare_computed_default(
    autogen_context: AutogenContext,
    alter_column_op: AlterColumnOp,
    schema: str | None,
    tname: str,
    cname: str,
    conn_col: Column[Any],
    metadata_col: Column[Any],
) -> PriorityDispatchResult:

    metadata_default = metadata_col.server_default
    conn_col_default = conn_col.server_default
    if conn_col_default is None and metadata_default is None:
        return PriorityDispatchResult.CONTINUE

    is_conn_computed = sqla_compat._server_default_is_computed(
        conn_col_default
    )
    is_meta_computed = sqla_compat._server_default_is_computed(
        metadata_default
    )

    if not is_conn_computed and not is_meta_computed:
        return PriorityDispatchResult.CONTINUE

    migration_context = autogen_context.migration_context
    user_compare_computed = migration_context._user_compare_computed

    if user_compare_computed is False:
        if is_conn_computed and not is_meta_computed:
            _warn_computed_not_supported(tname, cname)
        elif is_meta_computed:
            rendered_metadata = str(
                cast(sa_schema.Computed, metadata_default).sqltext.compile(
                    dialect=autogen_context.dialect,
                    compile_kwargs={"literal_binds": True},
                )
            )
            rendered_metadata = _normalize_computed_default(rendered_metadata)

            if is_conn_computed:
                rendered_conn = str(
                    cast(sa_schema.Computed, conn_col_default).sqltext.compile(
                        dialect=autogen_context.dialect,
                        compile_kwargs={"literal_binds": True},
                    )
                )
                rendered_conn = _normalize_computed_default(rendered_conn)
            else:
                rendered_conn = ""

            if rendered_metadata != rendered_conn:
                _warn_computed_not_supported(tname, cname)

        return PriorityDispatchResult.STOP

    alter_column_op.existing_server_default = conn_col_default

    rendered_metadata_computed = (
        str(
            cast(sa_schema.Computed, metadata_default).sqltext.compile(
                dialect=autogen_context.dialect,
                compile_kwargs={"literal_binds": True},
            )
        )
        if is_meta_computed
        else None
    )

    rendered_conn_computed = (
        str(
            cast(sa_schema.Computed, conn_col_default).sqltext.compile(
                dialect=autogen_context.dialect,
                compile_kwargs={"literal_binds": True},
            )
        )
        if is_conn_computed
        else None
    )

    if callable(user_compare_computed):
        is_diff = user_compare_computed(
            migration_context,
            conn_col,
            metadata_col,
            conn_col_default if is_conn_computed else None,
            metadata_default if is_meta_computed else None,
            rendered_metadata_computed,
        )
        if is_diff:
            alter_column_op.modify_server_default = metadata_default
            log.info(
                "User defined function %s detected "
                "computed default on column '%s.%s'",
                user_compare_computed,
                tname,
                cname,
            )
            return PriorityDispatchResult.STOP
        elif is_diff is False:
            return PriorityDispatchResult.STOP

    norm_meta = (
        _normalize_computed_default(rendered_metadata_computed)
        if rendered_metadata_computed
        else ""
    )
    norm_conn = (
        _normalize_computed_default(rendered_conn_computed)
        if rendered_conn_computed
        else ""
    )

    if norm_meta != norm_conn:
        alter_column_op.modify_server_default = metadata_default
        log.info(
            "Detected computed default change on column '%s.%s'",
            tname,
            cname,
        )

    return PriorityDispatchResult.STOP


def _warn_computed_not_supported(tname: str, cname: str) -> None:
    util.warn("Computed default on %s.%s cannot be modified" % (tname, cname))


def _compare_identity_default(
    autogen_context: AutogenContext,
    alter_column_op: AlterColumnOp,
    schema: str | None,
    tname: quoted_name | str,
    cname: quoted_name | str,
    conn_col: Column[Any],
    metadata_col: Column[Any],
    skip: Sequence[str] = (
        "order",
        "on_null",
        "oracle_order",
        "oracle_on_null",
    ),
) -> PriorityDispatchResult:

    metadata_default = metadata_col.server_default
    conn_col_default = conn_col.server_default
    if (
        conn_col_default is None
        and metadata_default is None
        or not sqla_compat._server_default_is_identity(
            metadata_default, conn_col_default
        )
    ):
        return PriorityDispatchResult.CONTINUE

    assert isinstance(
        metadata_col.server_default,
        (sa_schema.Identity, sa_schema.Sequence, NoneType),
    )
    assert isinstance(
        conn_col.server_default,
        (sa_schema.Identity, sa_schema.Sequence, NoneType),
    )

    impl = autogen_context.migration_context.impl
    diff, _, is_alter = impl._compare_identity_default(  # type: ignore[no-untyped-call]  # noqa: E501
        metadata_col.server_default, conn_col.server_default
    )

    if is_alter:
        alter_column_op.modify_server_default = metadata_default
        if diff:
            log.info(
                "Detected server default on column '%s.%s': "
                "identity options attributes %s",
                tname,
                cname,
                sorted(diff),
            )

            return PriorityDispatchResult.STOP

    return PriorityDispatchResult.CONTINUE


def _user_compare_server_default(
    autogen_context: AutogenContext,
    alter_column_op: AlterColumnOp,
    schema: str | None,
    tname: quoted_name | str,
    cname: quoted_name | str,
    conn_col: Column[Any],
    metadata_col: Column[Any],
) -> PriorityDispatchResult:

    metadata_default = metadata_col.server_default
    conn_col_default = conn_col.server_default
    if conn_col_default is None and metadata_default is None:
        return PriorityDispatchResult.CONTINUE

    if sqla_compat._server_default_is_computed(
        conn_col_default
    ) or sqla_compat._server_default_is_computed(metadata_default):
        return PriorityDispatchResult.CONTINUE

    alter_column_op.existing_server_default = conn_col_default

    migration_context = autogen_context.migration_context

    if migration_context._user_compare_server_default is False:
        return PriorityDispatchResult.STOP

    if not callable(migration_context._user_compare_server_default):
        return PriorityDispatchResult.CONTINUE

    rendered_metadata_default = _render_server_default_for_compare(
        metadata_default, autogen_context
    )
    rendered_conn_default = (
        cast(Any, conn_col_default).arg.text if conn_col_default else None
    )

    is_diff = migration_context._user_compare_server_default(
        migration_context,
        conn_col,
        metadata_col,
        rendered_conn_default,
        metadata_col.server_default,
        rendered_metadata_default,
    )
    if is_diff:
        alter_column_op.modify_server_default = metadata_default
        log.info(
            "User defined function %s detected "
            "server default on column '%s.%s'",
            migration_context._user_compare_server_default,
            tname,
            cname,
        )
        return PriorityDispatchResult.STOP
    elif is_diff is False:
        # if user compare server_default returns False and not None,
        # it means "dont do any more server_default comparison"
        return PriorityDispatchResult.STOP

    return PriorityDispatchResult.CONTINUE


def _dialect_impl_compare_server_default(
    autogen_context: AutogenContext,
    alter_column_op: AlterColumnOp,
    schema: str | None,
    tname: quoted_name | str,
    cname: quoted_name | str,
    conn_col: Column[Any],
    metadata_col: Column[Any],
) -> PriorityDispatchResult:
    """use dialect.impl.compare_server_default.

    This would in theory not be needed.  however we dont know if any
    third party libraries haven't made their own alembic dialect and
    implemented this method.

    """
    metadata_default = metadata_col.server_default
    conn_col_default = conn_col.server_default
    if conn_col_default is None and metadata_default is None:
        return PriorityDispatchResult.CONTINUE

    # this is already done by _user_compare_server_default,
    # but doing it here also for unit tests that want to call
    # _dialect_impl_compare_server_default directly
    alter_column_op.existing_server_default = conn_col_default

    if not isinstance(
        metadata_default, (DefaultClause, NoneType)
    ) or not isinstance(conn_col_default, (DefaultClause, NoneType)):
        return PriorityDispatchResult.CONTINUE

    migration_context = autogen_context.migration_context

    rendered_metadata_default = _render_server_default_for_compare(
        metadata_default, autogen_context
    )
    rendered_conn_default = (
        cast(Any, conn_col_default).arg.text if conn_col_default else None
    )

    is_diff = migration_context.impl.compare_server_default(  # type: ignore[no-untyped-call]  # noqa: E501
        conn_col,
        metadata_col,
        rendered_metadata_default,
        rendered_conn_default,
    )
    if is_diff:
        alter_column_op.modify_server_default = metadata_default
        log.info(
            "Dialect impl %s detected server default on column '%s.%s'",
            migration_context.impl,
            tname,
            cname,
        )
        return PriorityDispatchResult.STOP
    return PriorityDispatchResult.CONTINUE


def _setup_autoincrement(
    autogen_context: AutogenContext,
    alter_column_op: AlterColumnOp,
    schema: str | None,
    tname: quoted_name | str,
    cname: quoted_name,
    conn_col: Column[Any],
    metadata_col: Column[Any],
) -> PriorityDispatchResult:
    if metadata_col.table._autoincrement_column is metadata_col:
        alter_column_op.kw["autoincrement"] = True
    elif metadata_col.autoincrement is True:
        alter_column_op.kw["autoincrement"] = True
    elif metadata_col.autoincrement is False:
        alter_column_op.kw["autoincrement"] = False

    return PriorityDispatchResult.CONTINUE


def setup(plugin: Plugin) -> None:
    plugin.add_autogenerate_comparator(
        _user_compare_server_default,
        "column",
        "server_default",
        priority=DispatchPriority.FIRST,
    )
    plugin.add_autogenerate_comparator(
        _compare_computed_default,
        "column",
        "server_default",
    )

    plugin.add_autogenerate_comparator(
        _compare_identity_default,
        "column",
        "server_default",
    )

    plugin.add_autogenerate_comparator(
        _setup_autoincrement,
        "column",
        "server_default",
    )
    plugin.add_autogenerate_comparator(
        _dialect_impl_compare_server_default,
        "column",
        "server_default",
        priority=DispatchPriority.LAST,
    )
