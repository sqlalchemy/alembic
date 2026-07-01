# mypy: allow-untyped-defs, allow-untyped-calls, allow-incomplete-defs

from __future__ import annotations

import logging
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

from sqlalchemy import schema as sa_schema

from .util import _InspectorConv
from ...operations import ops
from ...util import PriorityDispatchResult
from ...util import sqla_compat

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import ReflectedCheckConstraint
    from sqlalchemy.sql.elements import quoted_name
    from sqlalchemy.sql.schema import CheckConstraint
    from sqlalchemy.sql.schema import Table

    from ...autogenerate.api import AutogenContext
    from ...ddl.impl import DefaultImpl
    from ...operations.ops import ModifyTableOps
    from ...runtime.plugins import Plugin


log = logging.getLogger(__name__)


def _make_check_constraint(
    impl: DefaultImpl,
    params: ReflectedCheckConstraint,
    conn_table: Table,
) -> CheckConstraint:
    const = sa_schema.CheckConstraint(
        params["sqltext"],
        name=params["name"],
        **impl.adjust_reflected_dialect_options(params, "check_constraint"),
    )
    conn_table.append_constraint(const)
    return const


def _compare_check_constraints(
    autogen_context: AutogenContext,
    modify_table_ops: ModifyTableOps,
    schema: Optional[str],
    tname: Union[quoted_name, str],
    conn_table: Optional[Table],
    metadata_table: Optional[Table],
) -> PriorityDispatchResult:
    if conn_table is None or metadata_table is None:
        return PriorityDispatchResult.CONTINUE

    inspector = autogen_context.inspector
    impl = autogen_context.migration_context.impl

    metadata_ck_constraints = {
        ck
        for ck in metadata_table.constraints
        if isinstance(ck, sa_schema.CheckConstraint)
        and not sqla_compat._is_type_bound(ck)
    }

    try:
        conn_ck_list = _InspectorConv(inspector).get_check_constraints(
            tname, schema=schema
        )
    except NotImplementedError:
        return PriorityDispatchResult.CONTINUE

    conn_ck_list = [
        ck
        for ck in conn_ck_list
        if ck.get("name") is not None
        and autogen_context.run_name_filters(
            ck["name"],
            "check_constraint",
            {"table_name": tname, "schema_name": schema},
        )
    ]

    conn_ck_objs = {
        _make_check_constraint(impl, ck_def, conn_table)
        for ck_def in conn_ck_list
    }

    metadata_ck_sig = {
        impl._create_metadata_constraint_sig(ck)
        for ck in metadata_ck_constraints
        if sqla_compat._constraint_is_named(ck, autogen_context.dialect)
    }

    conn_ck_sig = {
        impl._create_reflected_constraint_sig(ck) for ck in conn_ck_objs
    }

    metadata_ck_by_name = {
        c.name: c
        for c in metadata_ck_sig
        if sqla_compat.constraint_name_string(c.name)
    }
    conn_ck_by_name = {
        c.name: c
        for c in conn_ck_sig
        if sqla_compat.constraint_name_string(c.name)
    }

    for removed_name in sorted(
        set(conn_ck_by_name).difference(metadata_ck_by_name)
    ):
        conn_obj = conn_ck_by_name[removed_name]
        if autogen_context.run_object_filters(
            conn_obj.const,
            conn_obj.name,
            "check_constraint",
            True,
            None,
        ):
            modify_table_ops.ops.append(
                ops.DropConstraintOp.from_constraint(conn_obj.const)
            )
            log.info(
                "Detected removed check constraint %r on table %r",
                conn_obj.name,
                tname,
            )

    for existing_name in sorted(
        set(metadata_ck_by_name).intersection(conn_ck_by_name)
    ):
        metadata_obj = metadata_ck_by_name[existing_name]
        conn_obj = conn_ck_by_name[existing_name]

        comparison = metadata_obj.compare_to_reflected(conn_obj)

        if comparison.is_different:
            if autogen_context.run_object_filters(
                metadata_obj.const,
                metadata_obj.name,
                "check_constraint",
                False,
                conn_obj.const,
            ):
                log.info(
                    "Detected changed check constraint %r on table %r: %s",
                    existing_name,
                    tname,
                    comparison.message,
                )
                modify_table_ops.ops.append(
                    ops.DropConstraintOp.from_constraint(conn_obj.const)
                )
                modify_table_ops.ops.append(
                    ops.AddConstraintOp.from_constraint(metadata_obj.const)
                )
        elif comparison.is_skip:
            log.info(
                "Cannot compare check constraint %r, "
                "assuming equal and skipping. %s",
                existing_name,
                comparison.message,
            )

    for added_name in sorted(
        set(metadata_ck_by_name).difference(conn_ck_by_name)
    ):
        metadata_obj = metadata_ck_by_name[added_name]
        if autogen_context.run_object_filters(
            metadata_obj.const,
            metadata_obj.name,
            "check_constraint",
            False,
            None,
        ):
            modify_table_ops.ops.append(
                ops.AddConstraintOp.from_constraint(metadata_obj.const)
            )
            log.info(
                "Detected added check constraint %r on table %r",
                metadata_obj.name,
                tname,
            )

    return PriorityDispatchResult.CONTINUE


def setup(plugin: Plugin) -> None:
    plugin.add_autogenerate_comparator(
        _compare_check_constraints,
        "table",
        "checkconstraints",
    )
