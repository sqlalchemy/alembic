# mypy: allow-untyped-defs, allow-untyped-calls, allow-incomplete-defs

from __future__ import annotations

import logging
from typing import Any
from typing import cast
from typing import Collection
from typing import Dict
from typing import Mapping
from typing import Optional
from typing import TYPE_CHECKING
from typing import TypeVar
from typing import Union

from sqlalchemy import schema as sa_schema
from sqlalchemy import text
from sqlalchemy.sql import expression
from sqlalchemy.sql.schema import ForeignKeyConstraint
from sqlalchemy.sql.schema import Index
from sqlalchemy.sql.schema import UniqueConstraint

from .util import _InspectorConv
from ... import util
from ...ddl._autogen import is_index_sig
from ...ddl._autogen import is_uq_sig
from ...operations import ops
from ...util import PriorityDispatchResult
from ...util import sqla_compat

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import ReflectedForeignKeyConstraint
    from sqlalchemy.engine.interfaces import ReflectedIndex
    from sqlalchemy.engine.interfaces import ReflectedUniqueConstraint
    from sqlalchemy.sql.elements import quoted_name
    from sqlalchemy.sql.elements import TextClause
    from sqlalchemy.sql.schema import Column
    from sqlalchemy.sql.schema import Table

    from ...autogenerate.api import AutogenContext
    from ...ddl._autogen import _constraint_sig
    from ...ddl.impl import DefaultImpl
    from ...operations.ops import AlterColumnOp
    from ...operations.ops import ModifyTableOps
    from ...runtime.plugins import Plugin

_C = TypeVar("_C", bound=Union[UniqueConstraint, ForeignKeyConstraint, Index])


log = logging.getLogger(__name__)


def _compare_indexes_and_uniques(
    autogen_context: AutogenContext,
    modify_ops: ModifyTableOps,
    schema: Optional[str],
    tname: Union[quoted_name, str],
    conn_table: Optional[Table],
    metadata_table: Optional[Table],
) -> PriorityDispatchResult:
    inspector = autogen_context.inspector
    is_create_table = conn_table is None
    is_drop_table = metadata_table is None
    impl = autogen_context.migration_context.impl

    # 1a. get raw indexes and unique constraints from metadata ...
    if metadata_table is not None:
        metadata_unique_constraints = {
            uq
            for uq in metadata_table.constraints
            if isinstance(uq, sa_schema.UniqueConstraint)
        }
        metadata_indexes = set(metadata_table.indexes)
    else:
        metadata_unique_constraints = set()
        metadata_indexes = set()

    conn_uniques: Collection[UniqueConstraint] = frozenset()
    conn_indexes: Collection[Index] = frozenset()

    supports_unique_constraints = False

    unique_constraints_duplicate_unique_indexes = False

    if conn_table is not None:
        conn_uniques_reflected: Collection[ReflectedUniqueConstraint] = (
            frozenset()
        )
        conn_indexes_reflected: Collection[ReflectedIndex] = frozenset()

        # 1b. ... and from connection, if the table exists
        try:
            conn_uniques_reflected = _InspectorConv(
                inspector
            ).get_unique_constraints(tname, schema=schema)

            supports_unique_constraints = True
        except NotImplementedError:
            pass
        except TypeError:
            # number of arguments is off for the base
            # method in SQLAlchemy due to the cache decorator
            # not being present
            pass
        else:
            conn_uniques_reflected = [
                uq
                for uq in conn_uniques_reflected
                if autogen_context.run_name_filters(
                    uq["name"],
                    "unique_constraint",
                    {"table_name": tname, "schema_name": schema},
                )
            ]
            for uq in conn_uniques_reflected:
                if uq.get("duplicates_index"):
                    unique_constraints_duplicate_unique_indexes = True
        try:
            conn_indexes_reflected = _InspectorConv(inspector).get_indexes(
                tname, schema=schema
            )
        except NotImplementedError:
            pass
        else:
            conn_indexes_reflected = [
                ix
                for ix in conn_indexes_reflected
                if autogen_context.run_name_filters(
                    ix["name"],
                    "index",
                    {"table_name": tname, "schema_name": schema},
                )
            ]

        # 2. convert conn-level objects from raw inspector records
        # into schema objects
        if is_drop_table:
            # for DROP TABLE uniques are inline, don't need them
            conn_uniques = set()
        else:
            conn_uniques = {
                _make_unique_constraint(impl, uq_def, conn_table)
                for uq_def in conn_uniques_reflected
            }

        conn_indexes = {
            index
            for index in (
                _make_index(impl, ix, conn_table)
                for ix in conn_indexes_reflected
            )
            if index is not None
        }

    # 2a. if the dialect dupes unique indexes as unique constraints
    # (mysql and oracle), correct for that

    if unique_constraints_duplicate_unique_indexes:
        _correct_for_uq_duplicates_uix(
            conn_uniques,
            conn_indexes,
            metadata_unique_constraints,
            metadata_indexes,
            autogen_context.dialect,
            impl,
        )

    # 3. give the dialect a chance to omit indexes and constraints that
    # we know are either added implicitly by the DB or that the DB
    # can't accurately report on
    impl.correct_for_autogen_constraints(
        conn_uniques,  # type: ignore[arg-type]
        conn_indexes,  # type: ignore[arg-type]
        metadata_unique_constraints,
        metadata_indexes,
    )

    # 4. organize the constraints into "signature" collections, the
    # _constraint_sig() objects provide a consistent facade over both
    # Index and UniqueConstraint so we can easily work with them
    # interchangeably
    metadata_unique_constraints_sig = {
        impl._create_metadata_constraint_sig(uq)
        for uq in metadata_unique_constraints
    }

    metadata_indexes_sig = {
        impl._create_metadata_constraint_sig(ix) for ix in metadata_indexes
    }

    conn_unique_constraints = {
        impl._create_reflected_constraint_sig(uq) for uq in conn_uniques
    }

    conn_indexes_sig = {
        impl._create_reflected_constraint_sig(ix) for ix in conn_indexes
    }

    # 5. index things by name, for those objects that have names
    metadata_names = {
        cast(str, c.md_name_to_sql_name(autogen_context)): c
        for c in metadata_unique_constraints_sig.union(metadata_indexes_sig)
        if c.is_named
    }

    conn_uniques_by_name: Dict[
        sqla_compat._ConstraintName,
        _constraint_sig[sa_schema.UniqueConstraint],
    ]
    conn_indexes_by_name: Dict[
        sqla_compat._ConstraintName, _constraint_sig[sa_schema.Index]
    ]

    conn_uniques_by_name = {c.name: c for c in conn_unique_constraints}
    conn_indexes_by_name = {c.name: c for c in conn_indexes_sig}
    conn_names = {
        c.name: c
        for c in conn_unique_constraints.union(conn_indexes_sig)
        if sqla_compat.constraint_name_string(c.name)
    }

    doubled_constraints = {
        name: (conn_uniques_by_name[name], conn_indexes_by_name[name])
        for name in set(conn_uniques_by_name).intersection(
            conn_indexes_by_name
        )
    }

    # 6. index things by "column signature", to help with unnamed unique
    # constraints.
    conn_uniques_by_sig = {uq.unnamed: uq for uq in conn_unique_constraints}
    metadata_uniques_by_sig = {
        uq.unnamed: uq for uq in metadata_unique_constraints_sig
    }
    unnamed_metadata_uniques = {
        uq.unnamed: uq
        for uq in metadata_unique_constraints_sig
        if not sqla_compat._constraint_is_named(
            uq.const, autogen_context.dialect
        )
    }

    # assumptions:
    # 1. a unique constraint or an index from the connection *always*
    #    has a name.
    # 2. an index on the metadata side *always* has a name.
    # 3. a unique constraint on the metadata side *might* have a name.
    # 4. The backend may double up indexes as unique constraints and
    #    vice versa (e.g. MySQL, Postgresql)

    def obj_added(
        obj: (
            _constraint_sig[sa_schema.UniqueConstraint]
            | _constraint_sig[sa_schema.Index]
        ),
    ):
        if is_index_sig(obj):
            if autogen_context.run_object_filters(
                obj.const, obj.name, "index", False, None
            ):
                modify_ops.ops.append(ops.CreateIndexOp.from_index(obj.const))
                log.info(
                    "Detected added index %r on '%s'",
                    obj.name,
                    obj.column_names,
                )
        elif is_uq_sig(obj):
            if not supports_unique_constraints:
                # can't report unique indexes as added if we don't
                # detect them
                return
            if is_create_table or is_drop_table:
                # unique constraints are created inline with table defs
                return
            if autogen_context.run_object_filters(
                obj.const, obj.name, "unique_constraint", False, None
            ):
                modify_ops.ops.append(
                    ops.AddConstraintOp.from_constraint(obj.const)
                )
                log.info(
                    "Detected added unique constraint %r on '%s'",
                    obj.name,
                    obj.column_names,
                )
        else:
            assert False

    def obj_removed(
        obj: (
            _constraint_sig[sa_schema.UniqueConstraint]
            | _constraint_sig[sa_schema.Index]
        ),
    ):
        if is_index_sig(obj):
            if obj.is_unique and not supports_unique_constraints:
                # many databases double up unique constraints
                # as unique indexes.  without that list we can't
                # be sure what we're doing here
                return

            if autogen_context.run_object_filters(
                obj.const, obj.name, "index", True, None
            ):
                modify_ops.ops.append(ops.DropIndexOp.from_index(obj.const))
                log.info("Detected removed index %r on %r", obj.name, tname)
        elif is_uq_sig(obj):
            if is_create_table or is_drop_table:
                # if the whole table is being dropped, we don't need to
                # consider unique constraint separately
                return
            if autogen_context.run_object_filters(
                obj.const, obj.name, "unique_constraint", True, None
            ):
                modify_ops.ops.append(
                    ops.DropConstraintOp.from_constraint(obj.const)
                )
                log.info(
                    "Detected removed unique constraint %r on %r",
                    obj.name,
                    tname,
                )
        else:
            assert False

    def obj_changed(
        old: (
            _constraint_sig[sa_schema.UniqueConstraint]
            | _constraint_sig[sa_schema.Index]
        ),
        new: (
            _constraint_sig[sa_schema.UniqueConstraint]
            | _constraint_sig[sa_schema.Index]
        ),
        msg: str,
    ):
        if is_index_sig(old):
            assert is_index_sig(new)

            if autogen_context.run_object_filters(
                new.const, new.name, "index", False, old.const
            ):
                log.info(
                    "Detected changed index %r on %r: %s", old.name, tname, msg
                )
                modify_ops.ops.append(ops.DropIndexOp.from_index(old.const))
                modify_ops.ops.append(ops.CreateIndexOp.from_index(new.const))
        elif is_uq_sig(old):
            assert is_uq_sig(new)

            if autogen_context.run_object_filters(
                new.const, new.name, "unique_constraint", False, old.const
            ):
                log.info(
                    "Detected changed unique constraint %r on %r: %s",
                    old.name,
                    tname,
                    msg,
                )
                modify_ops.ops.append(
                    ops.DropConstraintOp.from_constraint(old.const)
                )
                modify_ops.ops.append(
                    ops.AddConstraintOp.from_constraint(new.const)
                )
        else:
            assert False

    for removed_name in sorted(set(conn_names).difference(metadata_names)):
        conn_obj = conn_names[removed_name]
        if (
            is_uq_sig(conn_obj)
            and conn_obj.unnamed in unnamed_metadata_uniques
        ):
            continue
        elif removed_name in doubled_constraints:
            conn_uq, conn_idx = doubled_constraints[removed_name]
            if (
                all(
                    conn_idx.unnamed != meta_idx.unnamed
                    for meta_idx in metadata_indexes_sig
                )
                and conn_uq.unnamed not in metadata_uniques_by_sig
            ):
                obj_removed(conn_uq)
                obj_removed(conn_idx)
        else:
            obj_removed(conn_obj)

    for existing_name in sorted(set(metadata_names).intersection(conn_names)):
        metadata_obj = metadata_names[existing_name]

        if existing_name in doubled_constraints:
            conn_uq, conn_idx = doubled_constraints[existing_name]
            if is_index_sig(metadata_obj):
                conn_obj = conn_idx
            else:
                conn_obj = conn_uq
        else:
            conn_obj = conn_names[existing_name]

        if type(conn_obj) != type(metadata_obj):
            obj_removed(conn_obj)
            obj_added(metadata_obj)
        else:
            # TODO: for plugins, let's do is_index_sig / is_uq_sig
            # here so we know index or unique, then
            # do a sub-dispatch,
            # autogen_context.comparators.dispatch("index")
            # or
            # autogen_context.comparators.dispatch("unique_constraint")
            #
            comparison = metadata_obj.compare_to_reflected(conn_obj)

            if comparison.is_different:
                # constraint are different
                obj_changed(conn_obj, metadata_obj, comparison.message)
            elif comparison.is_skip:
                # constraint cannot be compared, skip them
                thing = (
                    "index" if is_index_sig(conn_obj) else "unique constraint"
                )
                log.info(
                    "Cannot compare %s %r, assuming equal and skipping. %s",
                    thing,
                    conn_obj.name,
                    comparison.message,
                )
            else:
                # constraint are equal
                assert comparison.is_equal

    for added_name in sorted(set(metadata_names).difference(conn_names)):
        obj = metadata_names[added_name]
        obj_added(obj)

    for uq_sig in unnamed_metadata_uniques:
        if uq_sig not in conn_uniques_by_sig:
            obj_added(unnamed_metadata_uniques[uq_sig])

    return PriorityDispatchResult.CONTINUE


def _correct_for_uq_duplicates_uix(
    conn_unique_constraints,
    conn_indexes,
    metadata_unique_constraints,
    metadata_indexes,
    dialect,
    impl,
):
    # dedupe unique indexes vs. constraints, since MySQL / Oracle
    # doesn't really have unique constraints as a separate construct.
    # but look in the metadata and try to maintain constructs
    # that already seem to be defined one way or the other
    # on that side.  This logic was formerly local to MySQL dialect,
    # generalized to Oracle and others. See #276

    # resolve final rendered name for unique constraints defined in the
    # metadata.   this includes truncation of long names.  naming convention
    # names currently should already be set as cons.name, however leave this
    # to the sqla_compat to decide.
    metadata_cons_names = [
        (sqla_compat._get_constraint_final_name(cons, dialect), cons)
        for cons in metadata_unique_constraints
    ]

    metadata_uq_names = {
        name for name, cons in metadata_cons_names if name is not None
    }

    unnamed_metadata_uqs = {
        impl._create_metadata_constraint_sig(cons).unnamed
        for name, cons in metadata_cons_names
        if name is None
    }

    metadata_ix_names = {
        sqla_compat._get_constraint_final_name(cons, dialect)
        for cons in metadata_indexes
        if cons.unique
    }

    # for reflection side, names are in their final database form
    # already since they're from the database
    conn_ix_names = {cons.name: cons for cons in conn_indexes if cons.unique}

    uqs_dupe_indexes = {
        cons.name: cons
        for cons in conn_unique_constraints
        if cons.info["duplicates_index"]
    }

    for overlap in uqs_dupe_indexes:
        if overlap not in metadata_uq_names:
            if (
                impl._create_reflected_constraint_sig(
                    uqs_dupe_indexes[overlap]
                ).unnamed
                not in unnamed_metadata_uqs
            ):
                conn_unique_constraints.discard(uqs_dupe_indexes[overlap])
        elif overlap not in metadata_ix_names:
            conn_indexes.discard(conn_ix_names[overlap])


_IndexColumnSortingOps: Mapping[str, Any] = util.immutabledict(
    {
        "asc": expression.asc,
        "desc": expression.desc,
        "nulls_first": expression.nullsfirst,
        "nulls_last": expression.nullslast,
        "nullsfirst": expression.nullsfirst,  # 1_3 name
        "nullslast": expression.nullslast,  # 1_3 name
    }
)


def _make_index(
    impl: DefaultImpl, params: ReflectedIndex, conn_table: Table
) -> Optional[Index]:
    exprs: list[Union[Column[Any], TextClause]] = []
    sorting = params.get("column_sorting")

    for num, col_name in enumerate(params["column_names"]):
        item: Union[Column[Any], TextClause]
        if col_name is None:
            assert "expressions" in params
            name = params["expressions"][num]
            item = text(name)
        else:
            name = col_name
            item = conn_table.c[col_name]
        if sorting and name in sorting:
            for operator in sorting[name]:
                if operator in _IndexColumnSortingOps:
                    item = _IndexColumnSortingOps[operator](item)
        exprs.append(item)
    ix = sa_schema.Index(
        params["name"],
        *exprs,
        unique=params["unique"],
        _table=conn_table,
        **impl.adjust_reflected_dialect_options(params, "index"),
    )
    if "duplicates_constraint" in params:
        ix.info["duplicates_constraint"] = params["duplicates_constraint"]
    return ix


def _make_unique_constraint(
    impl: DefaultImpl, params: ReflectedUniqueConstraint, conn_table: Table
) -> UniqueConstraint:
    uq = sa_schema.UniqueConstraint(
        *[conn_table.c[cname] for cname in params["column_names"]],
        name=params["name"],
        **impl.adjust_reflected_dialect_options(params, "unique_constraint"),
    )
    if "duplicates_index" in params:
        uq.info["duplicates_index"] = params["duplicates_index"]

    return uq


def _make_foreign_key(
    params: ReflectedForeignKeyConstraint, conn_table: Table
) -> ForeignKeyConstraint:
    tname = params["referred_table"]
    if params["referred_schema"]:
        tname = "%s.%s" % (params["referred_schema"], tname)

    options = params.get("options", {})

    const = sa_schema.ForeignKeyConstraint(
        [conn_table.c[cname] for cname in params["constrained_columns"]],
        ["%s.%s" % (tname, n) for n in params["referred_columns"]],
        onupdate=options.get("onupdate"),
        ondelete=options.get("ondelete"),
        deferrable=options.get("deferrable"),
        initially=options.get("initially"),
        name=params["name"],
    )
    # needed by 0.7
    conn_table.append_constraint(const)
    return const


def _compare_foreign_keys(
    autogen_context: AutogenContext,
    modify_table_ops: ModifyTableOps,
    schema: Optional[str],
    tname: Union[quoted_name, str],
    conn_table: Table,
    metadata_table: Table,
) -> PriorityDispatchResult:
    # if we're doing CREATE TABLE, all FKs are created
    # inline within the table def
    if conn_table is None or metadata_table is None:
        return PriorityDispatchResult.CONTINUE

    inspector = autogen_context.inspector
    metadata_fks = {
        fk
        for fk in metadata_table.constraints
        if isinstance(fk, sa_schema.ForeignKeyConstraint)
    }

    conn_fks_list = [
        fk
        for fk in _InspectorConv(inspector).get_foreign_keys(
            tname, schema=schema
        )
        if autogen_context.run_name_filters(
            fk["name"],
            "foreign_key_constraint",
            {"table_name": tname, "schema_name": schema},
        )
    ]

    conn_fks = {
        _make_foreign_key(const, conn_table) for const in conn_fks_list
    }

    impl = autogen_context.migration_context.impl

    # give the dialect a chance to correct the FKs to match more
    # closely
    autogen_context.migration_context.impl.correct_for_autogen_foreignkeys(
        conn_fks, metadata_fks
    )

    metadata_fks_sig = {
        impl._create_metadata_constraint_sig(fk) for fk in metadata_fks
    }

    conn_fks_sig = {
        impl._create_reflected_constraint_sig(fk) for fk in conn_fks
    }

    # check if reflected FKs include options, indicating the backend
    # can reflect FK options
    if conn_fks_list and "options" in conn_fks_list[0]:
        conn_fks_by_sig = {c.unnamed: c for c in conn_fks_sig}
        metadata_fks_by_sig = {c.unnamed: c for c in metadata_fks_sig}
    else:
        # otherwise compare by sig without options added
        conn_fks_by_sig = {c.unnamed_no_options: c for c in conn_fks_sig}
        metadata_fks_by_sig = {
            c.unnamed_no_options: c for c in metadata_fks_sig
        }

    metadata_fks_by_name = {
        c.name: c for c in metadata_fks_sig if c.name is not None
    }
    conn_fks_by_name = {c.name: c for c in conn_fks_sig if c.name is not None}

    def _add_fk(obj, compare_to):
        if autogen_context.run_object_filters(
            obj.const, obj.name, "foreign_key_constraint", False, compare_to
        ):
            modify_table_ops.ops.append(
                ops.CreateForeignKeyOp.from_constraint(const.const)
            )

            log.info(
                "Detected added foreign key (%s)(%s) on table %s%s",
                ", ".join(obj.source_columns),
                ", ".join(obj.target_columns),
                "%s." % obj.source_schema if obj.source_schema else "",
                obj.source_table,
            )

    def _remove_fk(obj, compare_to):
        if autogen_context.run_object_filters(
            obj.const, obj.name, "foreign_key_constraint", True, compare_to
        ):
            modify_table_ops.ops.append(
                ops.DropConstraintOp.from_constraint(obj.const)
            )
            log.info(
                "Detected removed foreign key (%s)(%s) on table %s%s",
                ", ".join(obj.source_columns),
                ", ".join(obj.target_columns),
                "%s." % obj.source_schema if obj.source_schema else "",
                obj.source_table,
            )

    # so far it appears we don't need to do this by name at all.
    # SQLite doesn't preserve constraint names anyway

    for removed_sig in set(conn_fks_by_sig).difference(metadata_fks_by_sig):
        const = conn_fks_by_sig[removed_sig]
        if removed_sig not in metadata_fks_by_sig:
            compare_to = (
                metadata_fks_by_name[const.name].const
                if const.name and const.name in metadata_fks_by_name
                else None
            )
            _remove_fk(const, compare_to)

    for added_sig in set(metadata_fks_by_sig).difference(conn_fks_by_sig):
        const = metadata_fks_by_sig[added_sig]
        if added_sig not in conn_fks_by_sig:
            compare_to = (
                conn_fks_by_name[const.name].const
                if const.name and const.name in conn_fks_by_name
                else None
            )
            _add_fk(const, compare_to)

    return PriorityDispatchResult.CONTINUE


def _compare_nullable(
    autogen_context: AutogenContext,
    alter_column_op: AlterColumnOp,
    schema: Optional[str],
    tname: Union[quoted_name, str],
    cname: Union[quoted_name, str],
    conn_col: Column[Any],
    metadata_col: Column[Any],
) -> PriorityDispatchResult:
    metadata_col_nullable = metadata_col.nullable
    conn_col_nullable = conn_col.nullable
    alter_column_op.existing_nullable = conn_col_nullable

    if conn_col_nullable is not metadata_col_nullable:
        if (
            sqla_compat._server_default_is_computed(
                metadata_col.server_default, conn_col.server_default
            )
            and sqla_compat._nullability_might_be_unset(metadata_col)
            or (
                sqla_compat._server_default_is_identity(
                    metadata_col.server_default, conn_col.server_default
                )
            )
        ):
            log.info(
                "Ignoring nullable change on identity column '%s.%s'",
                tname,
                cname,
            )
        else:
            alter_column_op.modify_nullable = metadata_col_nullable
            log.info(
                "Detected %s on column '%s.%s'",
                "NULL" if metadata_col_nullable else "NOT NULL",
                tname,
                cname,
            )
            # column nullablity changed, no further nullable checks needed
            return PriorityDispatchResult.STOP

    return PriorityDispatchResult.CONTINUE


def setup(plugin: Plugin) -> None:
    plugin.add_autogenerate_comparator(
        _compare_indexes_and_uniques,
        "table",
        "indexes",
    )
    plugin.add_autogenerate_comparator(
        _compare_foreign_keys,
        "table",
        "foreignkeys",
    )
    plugin.add_autogenerate_comparator(
        _compare_nullable,
        "column",
        "nullable",
    )
