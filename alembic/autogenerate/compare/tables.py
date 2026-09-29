# mypy: allow-untyped-calls

from __future__ import annotations

from collections.abc import Iterator
import contextlib
import logging
from typing import TYPE_CHECKING

from sqlalchemy import event
from sqlalchemy import exc as sa_exc
from sqlalchemy import schema as sa_schema
from sqlalchemy.schema import sort_tables_and_constraints
from sqlalchemy.util import OrderedSet

from .util import _InspectorConv
from ...operations import ops
from ...util import PriorityDispatchResult

if TYPE_CHECKING:
    from sqlalchemy.engine.reflection import Inspector
    from sqlalchemy.sql.elements import quoted_name
    from sqlalchemy.sql.schema import ForeignKeyConstraint
    from sqlalchemy.sql.schema import Table

    from ...autogenerate.api import AutogenContext
    from ...operations.ops import ModifyTableOps
    from ...operations.ops import UpgradeOps
    from ...runtime.plugins import Plugin


log = logging.getLogger(__name__)


def _autogen_for_tables(
    autogen_context: AutogenContext,
    upgrade_ops: UpgradeOps,
    schemas: set[str | None],
) -> PriorityDispatchResult:
    inspector = autogen_context.inspector

    conn_table_names: set[tuple[str | None, str]] = set()

    version_table_schema = (
        autogen_context.migration_context.version_table_schema
    )
    version_table = autogen_context.migration_context.version_table

    for schema_name in schemas:
        tables = available = set(inspector.get_table_names(schema=schema_name))
        if schema_name == version_table_schema:
            tables = tables.difference(
                [autogen_context.migration_context.version_table]
            )

        tablenames = [
            tname
            for tname in tables
            if autogen_context.run_name_filters(
                tname, "table", {"schema_name": schema_name}
            )
        ]

        conn_table_names.update((schema_name, tname) for tname in tablenames)

        inspector = autogen_context.inspector
        insp = _InspectorConv(inspector)
        insp.pre_cache_tables(schema_name, tablenames, available)

    # Use table insertion order rather than MetaData.sorted_tables so that
    # mutually-dependent FKs don't emit SAWarning here; CREATE/DROP TABLE
    # ops are reordered afterwards via sort_tables_and_constraints (#326).
    metadata_table_names = OrderedSet(
        [
            (table.schema, table.name)
            for table in autogen_context.table_key_to_table.values()
        ]
    ).difference([(version_table_schema, version_table)])

    _compare_tables(
        conn_table_names,
        metadata_table_names,
        inspector,
        upgrade_ops,
        autogen_context,
    )

    return PriorityDispatchResult.CONTINUE


def _compare_tables(
    conn_table_names: set[tuple[str | None, str]],
    metadata_table_names: set[tuple[str | None, str]],
    inspector: Inspector,
    upgrade_ops: UpgradeOps,
    autogen_context: AutogenContext,
) -> None:
    default_schema = inspector.bind.dialect.default_schema_name

    # tables coming from the connection will not have "schema"
    # set if it matches default_schema_name; so we need a list
    # of table names from local metadata that also have "None" if schema
    # == default_schema_name.  Most setups will be like this anyway but
    # some are not (see #170)
    metadata_table_names_no_dflt_schema = OrderedSet(
        [
            (schema if schema != default_schema else None, tname)
            for schema, tname in metadata_table_names
        ]
    )

    # to adjust for the MetaData collection storing the tables either
    # as "schemaname.tablename" or just "tablename", create a new lookup
    # which will match the "non-default-schema" keys to the Table object.
    tname_to_table = {
        no_dflt_schema: autogen_context.table_key_to_table[
            sa_schema._get_table_key(tname, schema)
        ]
        for no_dflt_schema, (schema, tname) in zip(
            metadata_table_names_no_dflt_schema, metadata_table_names
        )
    }
    metadata_table_names = metadata_table_names_no_dflt_schema

    for s, tname in metadata_table_names.difference(conn_table_names):
        name = "%s.%s" % (s, tname) if s else tname
        metadata_table = tname_to_table[(s, tname)]
        if autogen_context.run_object_filters(
            metadata_table, tname, "table", False, None
        ):
            upgrade_ops.ops.append(
                ops.CreateTableOp.from_table(metadata_table)
            )
            log.info("Detected added table %r", name)
            modify_table_ops = ops.ModifyTableOps(tname, [], schema=s)

            autogen_context.comparators.dispatch(
                "table", qualifier=autogen_context.dialect.name
            )(
                autogen_context,
                modify_table_ops,
                s,
                tname,
                None,
                metadata_table,
            )
            if not modify_table_ops.is_empty():
                upgrade_ops.ops.append(modify_table_ops)

    removal_metadata = sa_schema.MetaData()
    for s, tname in conn_table_names.difference(metadata_table_names):
        name = sa_schema._get_table_key(tname, s)

        # a name might be present already if a previous reflection pulled
        # this table in via foreign key constraint
        exists = name in removal_metadata.tables
        t = sa_schema.Table(tname, removal_metadata, schema=s)

        if not exists:
            event.listen(
                t,
                "column_reflect",
                # fmt: off
                autogen_context.migration_context.impl.
                _compat_autogen_column_reflect
                (inspector),
                # fmt: on
            )
            _InspectorConv(inspector).reflect_table(t)
        if autogen_context.run_object_filters(t, tname, "table", True, None):
            modify_table_ops = ops.ModifyTableOps(tname, [], schema=s)

            autogen_context.comparators.dispatch(
                "table", qualifier=autogen_context.dialect.name
            )(autogen_context, modify_table_ops, s, tname, t, None)
            if not modify_table_ops.is_empty():
                upgrade_ops.ops.append(modify_table_ops)

            upgrade_ops.ops.append(ops.DropTableOp.from_table(t))
            log.info("Detected removed table %r", name)

    existing_tables = conn_table_names.intersection(metadata_table_names)

    existing_metadata = sa_schema.MetaData()
    conn_column_info = {}
    for s, tname in existing_tables:
        name = sa_schema._get_table_key(tname, s)
        exists = name in existing_metadata.tables

        # a name might be present already if a previous reflection pulled
        # this table in via foreign key constraint
        t = sa_schema.Table(tname, existing_metadata, schema=s)
        if not exists:
            event.listen(
                t,
                "column_reflect",
                # fmt: off
                autogen_context.migration_context.impl.
                _compat_autogen_column_reflect(inspector),
                # fmt: on
            )
            _InspectorConv(inspector).reflect_table(t)

        conn_column_info[(s, tname)] = t

    for s, tname in sorted(existing_tables, key=lambda x: (x[0] or "", x[1])):
        s = s or None
        name = "%s.%s" % (s, tname) if s else tname
        metadata_table = tname_to_table[(s, tname)]
        conn_table = existing_metadata.tables[name]

        if autogen_context.run_object_filters(
            metadata_table, tname, "table", False, conn_table
        ):
            modify_table_ops = ops.ModifyTableOps(tname, [], schema=s)
            with _compare_columns(
                s,
                tname,
                conn_table,
                metadata_table,
                modify_table_ops,
                autogen_context,
                inspector,
            ):
                autogen_context.comparators.dispatch(
                    "table", qualifier=autogen_context.dialect.name
                )(
                    autogen_context,
                    modify_table_ops,
                    s,
                    tname,
                    conn_table,
                    metadata_table,
                )

            if not modify_table_ops.is_empty():
                upgrade_ops.ops.append(modify_table_ops)

    _rewrite_create_drop_table_fks(autogen_context, upgrade_ops)


def _create_table_op_from_stripped(
    op: ops.CreateTableOp, remaining_ids: set[int]
) -> ops.CreateTableOp:
    new_cols = [c for c in op.columns if id(c) not in remaining_ids]
    if len(new_cols) == len(op.columns):
        return op
    return ops.CreateTableOp(
        op.table_name,
        new_cols,
        schema=op.schema,
        if_not_exists=op.if_not_exists,
        _namespace_metadata=op._namespace_metadata,
        _constraints_included=op._constraints_included,
        comment=op.comment,
        info=dict(op.info) if op.info else {},
        prefixes=list(op.prefixes) if op.prefixes else None,
        **op.kw,
    )


def _sort_tables_for_ops(
    tables: list[Table],
) -> tuple[list[Table], list[ForeignKeyConstraint]]:
    remaining_fks: list[ForeignKeyConstraint] = []
    ordered: list[Table] = []
    for table, fks in sort_tables_and_constraints(tables):
        if table is None:
            remaining_fks.extend(fks)
        else:
            ordered.append(table)
    return ordered, remaining_fks


def _rewrite_create_table_fks(
    autogen_context: AutogenContext, upgrade_ops: UpgradeOps
) -> None:
    """Emit cyclic / use_alter FKs as create_foreign_key, reorder CREATE."""

    ops_list = list(upgrade_ops.ops)
    create_positions = [
        i for i, op in enumerate(ops_list) if isinstance(op, ops.CreateTableOp)
    ]
    if not create_positions:
        return

    key_to_table = autogen_context.table_key_to_table
    tables: list[Table] = []
    for i in create_positions:
        cop = ops_list[i]
        assert isinstance(cop, ops.CreateTableOp)
        key = sa_schema._get_table_key(cop.table_name, cop.schema)
        table = key_to_table.get(key)
        if table is None:
            table = cop.to_table()
        tables.append(table)

    try:
        ordered_tables, remaining_fks = _sort_tables_for_ops(tables)
    except sa_exc.NoReferencedTableError:
        return
    remaining_ids = {id(fk) for fk in remaining_fks}

    skip: set[int] = set()
    groups: dict[tuple[str | None, str], list] = {}
    for i in create_positions:
        cop = ops_list[i]
        assert isinstance(cop, ops.CreateTableOp)
        group: list = [_create_table_op_from_stripped(cop, remaining_ids)]
        skip.add(i)
        j = i + 1
        while j < len(ops_list) and isinstance(
            ops_list[j], ops.ModifyTableOps
        ):
            mop = ops_list[j]
            assert isinstance(mop, ops.ModifyTableOps)
            if mop.table_name == cop.table_name and mop.schema == cop.schema:
                group.append(mop)
                skip.add(j)
                j += 1
            else:
                break
        groups[(cop.schema, cop.table_name)] = group

    fk_ops = [
        ops.CreateForeignKeyOp.from_constraint(fk) for fk in remaining_fks
    ]

    new_ops: list = []
    placed = False
    for i, op in enumerate(ops_list):
        if i in skip:
            if not placed:
                for table in ordered_tables:
                    group = groups.get((table.schema, table.name))
                    if group is not None:
                        new_ops.extend(group)
                new_ops.extend(fk_ops)
                placed = True
            continue
        new_ops.append(op)
    if not placed:
        for table in ordered_tables:
            group = groups.get((table.schema, table.name))
            if group is not None:
                new_ops.extend(group)
        new_ops.extend(fk_ops)

    upgrade_ops.ops[:] = new_ops


def _table_from_drop_op(dop: ops.DropTableOp) -> Table | None:
    rev = dop._reverse
    if rev is None:
        return None
    md = rev._namespace_metadata
    if md is None:
        return dop.to_table()
    key = sa_schema._get_table_key(dop.table_name, dop.schema)
    return md.tables.get(key, dop.to_table())


def _rewrite_drop_table_fks(upgrade_ops: UpgradeOps) -> None:
    """Drop cyclic FKs before DROP TABLE, reverse-toposort the drops."""

    ops_list = list(upgrade_ops.ops)
    drop_positions = [
        i for i, op in enumerate(ops_list) if isinstance(op, ops.DropTableOp)
    ]
    if not drop_positions:
        return

    tables: list[Table] = []
    for i in drop_positions:
        dop = ops_list[i]
        assert isinstance(dop, ops.DropTableOp)
        table = _table_from_drop_op(dop)
        if table is None:
            table = dop.to_table()
        tables.append(table)

    try:
        ordered_tables, remaining_fks = _sort_tables_for_ops(tables)
    except sa_exc.NoReferencedTableError:
        # Dropped table FKs may point at tables that aren't in this
        # DropTableOp set (and aren't reconstructed onto the same MetaData).
        return

    skip: set[int] = set()
    groups: dict[tuple[str | None, str], list] = {}
    for i in drop_positions:
        dop = ops_list[i]
        assert isinstance(dop, ops.DropTableOp)
        group: list = []
        prev = i - 1
        if (
            prev >= 0
            and prev not in skip
            and isinstance(ops_list[prev], ops.ModifyTableOps)
        ):
            mop = ops_list[prev]
            assert isinstance(mop, ops.ModifyTableOps)
            if mop.table_name == dop.table_name and mop.schema == dop.schema:
                group.append(mop)
                skip.add(prev)
        group.append(dop)
        skip.add(i)
        groups[(dop.schema, dop.table_name)] = group

    fk_ops = [ops.DropConstraintOp.from_constraint(fk) for fk in remaining_fks]

    # DROP TABLE in reverse dependency order (dependents first)
    drop_order = list(reversed(ordered_tables))

    new_ops: list = []
    placed = False
    for i, op in enumerate(ops_list):
        if i in skip:
            if not placed:
                new_ops.extend(fk_ops)
                for table in drop_order:
                    group = groups.get((table.schema, table.name))
                    if group is not None:
                        new_ops.extend(group)
                placed = True
            continue
        new_ops.append(op)
    if not placed:
        new_ops.extend(fk_ops)
        for table in drop_order:
            group = groups.get((table.schema, table.name))
            if group is not None:
                new_ops.extend(group)

    upgrade_ops.ops[:] = new_ops


def _rewrite_create_drop_table_fks(
    autogen_context: AutogenContext, upgrade_ops: UpgradeOps
) -> None:
    _rewrite_create_table_fks(autogen_context, upgrade_ops)
    _rewrite_drop_table_fks(upgrade_ops)


@contextlib.contextmanager
def _compare_columns(
    schema: str | None,
    tname: quoted_name | str,
    conn_table: Table,
    metadata_table: Table,
    modify_table_ops: ModifyTableOps,
    autogen_context: AutogenContext,
    inspector: Inspector,
) -> Iterator[None]:
    name = "%s.%s" % (schema, tname) if schema else tname
    metadata_col_names = OrderedSet(
        c.name for c in metadata_table.c if not c.system
    )
    metadata_cols_by_name = {
        c.name: c for c in metadata_table.c if not c.system
    }

    conn_col_names = {
        c.name: c
        for c in conn_table.c
        if autogen_context.run_name_filters(
            c.name, "column", {"table_name": tname, "schema_name": schema}
        )
    }

    for cname in metadata_col_names.difference(conn_col_names):
        if autogen_context.run_object_filters(
            metadata_cols_by_name[cname], cname, "column", False, None
        ):
            modify_table_ops.ops.append(
                ops.AddColumnOp.from_column_and_tablename(
                    schema, tname, metadata_cols_by_name[cname]
                )
            )
            log.info("Detected added column '%s.%s'", name, cname)

    for colname in metadata_col_names.intersection(conn_col_names):
        metadata_col = metadata_cols_by_name[colname]
        conn_col = conn_table.c[colname]
        if not autogen_context.run_object_filters(
            metadata_col, colname, "column", False, conn_col
        ):
            continue
        alter_column_op = ops.AlterColumnOp(tname, colname, schema=schema)

        autogen_context.comparators.dispatch(
            "column", qualifier=autogen_context.dialect.name
        )(
            autogen_context,
            alter_column_op,
            schema,
            tname,
            colname,
            conn_col,
            metadata_col,
        )

        if alter_column_op.has_changes():
            modify_table_ops.ops.append(alter_column_op)

    yield

    for cname in set(conn_col_names).difference(metadata_col_names):
        if autogen_context.run_object_filters(
            conn_table.c[cname], cname, "column", True, None
        ):
            modify_table_ops.ops.append(
                ops.DropColumnOp.from_column_and_tablename(
                    schema, tname, conn_table.c[cname]
                )
            )
            log.info("Detected removed column '%s.%s'", name, cname)


def setup(plugin: Plugin) -> None:

    plugin.add_autogenerate_comparator(
        _autogen_for_tables,
        "schema",
        "tables",
    )
