from sqlalchemy.exc import NoSuchTableError
from sqlalchemy import schema as sa_schema, types as sqltypes
import logging
from .. import compat
from .render import _render_server_default
from sqlalchemy.util import OrderedSet


log = logging.getLogger(__name__)

def _run_filters(object_, name, type_, reflected, compare_to, object_filters):
    for fn in object_filters:
        if not fn(object_, name, type_, reflected, compare_to):
            return False
    else:
        return True

def _compare_tables(conn_table_names, metadata_table_names,
                    object_filters,
                    inspector, metadata, diffs, autogen_context):

    for s, tname in metadata_table_names.difference(conn_table_names):
        name = '%s.%s' % (s, tname) if s else tname
        metadata_table = metadata.tables[sa_schema._get_table_key(tname, s)]
        if _run_filters(metadata_table, tname, "table", False, None, object_filters):
            diffs.append(("add_table", metadata.tables[name]))
            log.info("Detected added table %r", name)
            _compare_indexes_and_uniques(s, tname, object_filters,
                    None,
                    metadata_table,
                    diffs, autogen_context, inspector)

    removal_metadata = sa_schema.MetaData()
    for s, tname in conn_table_names.difference(metadata_table_names):
        name = sa_schema._get_table_key(tname, s)
        exists = name in removal_metadata.tables
        t = sa_schema.Table(tname, removal_metadata, schema=s)
        if not exists:
            inspector.reflecttable(t, None)
        if _run_filters(t, tname, "table", True, None, object_filters):
            diffs.append(("remove_table", t))
            log.info("Detected removed table %r", name)

    existing_tables = conn_table_names.intersection(metadata_table_names)

    existing_metadata = sa_schema.MetaData()
    conn_column_info = {}
    for s, tname in existing_tables:
        name = sa_schema._get_table_key(tname, s)
        exists = name in existing_metadata.tables
        t = sa_schema.Table(tname, existing_metadata, schema=s)
        if not exists:
            inspector.reflecttable(t, None)
        conn_column_info[(s, tname)] = t

    for s, tname in sorted(existing_tables):
        name = '%s.%s' % (s, tname) if s else tname
        metadata_table = metadata.tables[name]
        conn_table = existing_metadata.tables[name]

        if _run_filters(metadata_table, tname, "table", False, conn_table, object_filters):
            _compare_columns(s, tname, object_filters,
                    conn_table,
                    metadata_table,
                    diffs, autogen_context, inspector)
            _compare_indexes_and_uniques(s, tname, object_filters,
                    conn_table,
                    metadata_table,
                    diffs, autogen_context, inspector)

    # TODO:
    # table constraints
    # sequences

def _make_index(params, conn_table):
    return sa_schema.Index(
            params['name'],
            *[conn_table.c[cname] for cname in params['column_names']],
            unique=params['unique']
    )

def _make_unique_constraint(params, conn_table):
    return sa_schema.UniqueConstraint(
            *[conn_table.c[cname] for cname in params['column_names']],
            name=params['name']
    )

def _compare_columns(schema, tname, object_filters, conn_table, metadata_table,
                                diffs, autogen_context, inspector):
    name = '%s.%s' % (schema, tname) if schema else tname
    metadata_cols_by_name = dict((c.name, c) for c in metadata_table.c)
    conn_col_names = dict((c.name, c) for c in conn_table.c)
    metadata_col_names = OrderedSet(sorted(metadata_cols_by_name))

    for cname in metadata_col_names.difference(conn_col_names):
        if _run_filters(metadata_cols_by_name[cname], cname,
                                "column", False, None, object_filters):
            diffs.append(
                ("add_column", schema, tname, metadata_cols_by_name[cname])
            )
            log.info("Detected added column '%s.%s'", name, cname)

    for cname in set(conn_col_names).difference(metadata_col_names):
        rem_col = sa_schema.Column(
                    cname,
                    conn_table.c[cname].type,
                    nullable=conn_table.c[cname].nullable,
                    server_default=conn_table.c[cname].server_default
                )
        if _run_filters(rem_col, cname,
                                "column", True, None, object_filters):
            diffs.append(
                ("remove_column", schema, tname, rem_col)
            )
            log.info("Detected removed column '%s.%s'", name, cname)

    for colname in metadata_col_names.intersection(conn_col_names):
        metadata_col = metadata_cols_by_name[colname]
        conn_col = conn_table.c[colname]
        if not _run_filters(
                    metadata_col, colname, "column", False, conn_col, object_filters):
            continue
        col_diff = []
        _compare_type(schema, tname, colname,
            conn_col,
            metadata_col,
            col_diff, autogen_context
        )
        _compare_nullable(schema, tname, colname,
            conn_col,
            metadata_col.nullable,
            col_diff, autogen_context
        )
        _compare_server_default(schema, tname, colname,
            conn_col,
            metadata_col,
            col_diff, autogen_context
        )
        if col_diff:
            diffs.append(col_diff)

class _constraint_sig(object):
    def __eq__(self, other):
        return self.const == other.const

    def __ne__(self, other):
        return self.const != other.const

    def __hash__(self):
        return hash(self.const)

class _uq_constraint_sig(_constraint_sig):
    is_index = False
    is_unique = True

    def __init__(self, const):
        self.const = const
        self.name = const.name
        self.sig = tuple(sorted([col.name for col in const.columns]))

    @property
    def column_names(self):
        return [col.name for col in self.const.columns]

class _ix_constraint_sig(_constraint_sig):
    is_index = True

    def __init__(self, const):
        self.const = const
        self.name = const.name
        self.sig = tuple(sorted([col.name for col in const.columns]))
        self.is_unique = bool(const.unique)

    @property
    def column_names(self):
        return _get_index_column_names(self.const)

def _get_index_column_names(idx):
    if compat.sqla_08:
        return [exp.name for exp in idx.expressions]
    else:
        return [col.name for col in idx.columns]

def _compare_indexes_and_uniques(schema, tname, object_filters, conn_table,
            metadata_table, diffs, autogen_context, inspector):

    is_create_table = conn_table is None

    # 1a. get raw indexes and unique constraints from metadata ...
    metadata_unique_constraints = set(uq for uq in metadata_table.constraints
            if isinstance(uq, sa_schema.UniqueConstraint)
    )
    metadata_indexes = set(metadata_table.indexes)

    # 1b. ... and from connection
    if conn_table is not None and hasattr(inspector, "get_unique_constraints"):
        try:
            conn_uniques = inspector.get_unique_constraints(tname)
        except (NotImplementedError, NoSuchTableError):
            conn_uniques = []
    else:
        conn_uniques = []


    try:
        conn_indexes = inspector.get_indexes(tname)
    except NoSuchTableError:
        conn_indexes = []

    # 2. convert conn-level objects from raw inspector records
    # into schema objects
    conn_uniques = set(_make_unique_constraint(uq_def, conn_table)
                                    for uq_def in conn_uniques)
    conn_indexes = set(_make_index(ix, conn_table) for ix in conn_indexes)

    # 3. give the dialect a chance to omit indexes and constraints that
    # we know are either added implicitly by the DB or that the DB
    # can't accurately report on
    autogen_context['context'].impl.\
                                correct_for_autogen_constraints(
                                        conn_uniques, conn_indexes,
                                        metadata_unique_constraints,
                                        metadata_indexes
                                )

    # 4. organize the constraints into "signature" collections, the
    # _constraint_sig() objects provide a consistent facade over both
    # Index and UniqueConstraint so we can easily work with them
    # interchangeably
    metadata_unique_constraints = set(_uq_constraint_sig(uq)
                                    for uq in metadata_unique_constraints
                                    )

    metadata_indexes = set(_ix_constraint_sig(ix) for ix in metadata_indexes)

    conn_unique_constraints = set(_uq_constraint_sig(uq) for uq in conn_uniques)

    conn_indexes = set(_ix_constraint_sig(ix) for ix in conn_indexes)

    # 5. index things by name, for those objects that have names
    metadata_names = dict(
                        (c.name, c) for c in
                        metadata_unique_constraints.union(metadata_indexes)
                        if c.name is not None)

    conn_uniques_by_name = dict((c.name, c) for c in conn_unique_constraints)
    conn_indexes_by_name = dict((c.name, c) for c in conn_indexes)

    conn_names = dict((c.name, c) for c in
                    conn_unique_constraints.union(conn_indexes)
                            if c.name is not None)

    doubled_constraints = dict(
        (name, (conn_uniques_by_name[name], conn_indexes_by_name[name]))
        for name in set(conn_uniques_by_name).intersection(conn_indexes_by_name)
    )

    # 6. index things by "column signature", to help with unnamed unique
    # constraints.
    conn_uniques_by_sig = dict((uq.sig, uq) for uq in conn_unique_constraints)
    metadata_uniques_by_sig = dict(
                            (uq.sig, uq) for uq in metadata_unique_constraints)
    metadata_indexes_by_sig = dict(
                            (ix.sig, ix) for ix in metadata_indexes)
    unnamed_metadata_uniques = dict((uq.sig, uq) for uq in
                            metadata_unique_constraints if uq.name is None)

    # assumptions:
    # 1. a unique constraint or an index from the connection *always*
    #    has a name.
    # 2. an index on the metadata side *always* has a name.
    # 3. a unique constraint on the metadata side *might* have a name.
    # 4. The backend may double up indexes as unique constraints and
    #    vice versa (e.g. MySQL, Postgresql)

    def obj_added(obj):
        if obj.is_index:
            diffs.append(("add_index", obj.const))
            log.info("Detected added index '%s' on %s",
                obj.name, ', '.join([
                    "'%s'" % obj.column_names
                    ])
            )
        else:
            if is_create_table:
                # unique constraints are created inline with table defs
                return
            diffs.append(("add_constraint", obj.const))
            log.info("Detected added unique constraint '%s' on %s",
                obj.name, ', '.join([
                    "'%s'" % obj.column_names
                    ])
            )

    def obj_removed(obj):
        if obj.is_index:
            diffs.append(("remove_index", obj.const))
            log.info("Detected removed index '%s' on '%s'", obj.name, tname)
        else:
            diffs.append(("remove_constraint", obj.const))
            log.info("Detected removed unique constraint '%s' on '%s'",
                obj.name, tname
            )

    def obj_changed(old, new, msg):
        if old.is_index:
            log.info("Detected changed index '%s' on '%s':%s",
                    old.name, tname, ', '.join(msg)
                )
            diffs.append(("remove_index", old.const))
            diffs.append(("add_index", new.const))
        else:
            log.info("Detected changed unique constraint '%s' on '%s':%s",
                    old.name, tname, ', '.join(msg)
                )
            diffs.append(("remove_constraint", old.const))
            diffs.append(("add_constraint", new.const))


    for added_name in sorted(set(metadata_names).difference(conn_names)):
        obj = metadata_names[added_name]
        obj_added(obj)


    for existing_name in sorted(set(metadata_names).intersection(conn_names)):
        metadata_obj = metadata_names[existing_name]

        if existing_name in doubled_constraints:
            conn_uq, conn_idx = doubled_constraints[existing_name]
            if metadata_obj.is_index:
                conn_obj = conn_idx
            else:
                conn_obj = conn_uq
        else:
            conn_obj = conn_names[existing_name]

        if conn_obj.is_index != metadata_obj.is_index:
            obj_removed(conn_obj)
            obj_added(metadata_obj)
        else:
            msg = []
            if conn_obj.is_unique != metadata_obj.is_unique:
                msg.append(' unique=%r to unique=%r' % (
                    conn_obj.is_unique, metadata_obj.is_unique
                ))
            if conn_obj.sig != metadata_obj.sig:
                msg.append(' columns %r to %r' % (
                    conn_obj.sig, metadata_obj.sig
                ))

            if msg:
                obj_changed(conn_obj, metadata_obj, msg)


    for removed_name in sorted(set(conn_names).difference(metadata_names)):
        conn_obj = conn_names[removed_name]
        if not conn_obj.is_index and conn_obj.sig in unnamed_metadata_uniques:
            continue
        elif removed_name in doubled_constraints:
            if conn_obj.sig not in metadata_indexes_by_sig and \
                conn_obj.sig not in metadata_uniques_by_sig:
                conn_uq, conn_idx = doubled_constraints[removed_name]
                obj_removed(conn_uq)
                obj_removed(conn_idx)
        else:
            obj_removed(conn_obj)

    for uq_sig in unnamed_metadata_uniques:
        if uq_sig not in conn_uniques_by_sig:
            obj_added(unnamed_metadata_uniques[uq_sig])


def _compare_nullable(schema, tname, cname, conn_col,
                            metadata_col_nullable, diffs,
                            autogen_context):
    conn_col_nullable = conn_col.nullable
    if conn_col_nullable is not metadata_col_nullable:
        diffs.append(
            ("modify_nullable", schema, tname, cname,
                {
                    "existing_type": conn_col.type,
                    "existing_server_default": conn_col.server_default,
                },
                conn_col_nullable,
                metadata_col_nullable),
        )
        log.info("Detected %s on column '%s.%s'",
            "NULL" if metadata_col_nullable else "NOT NULL",
            tname,
            cname
        )

def _compare_type(schema, tname, cname, conn_col,
                            metadata_col, diffs,
                            autogen_context):

    conn_type = conn_col.type
    metadata_type = metadata_col.type
    if conn_type._type_affinity is sqltypes.NullType:
        log.info("Couldn't determine database type "
                    "for column '%s.%s'", tname, cname)
        return
    if metadata_type._type_affinity is sqltypes.NullType:
        log.info("Column '%s.%s' has no type within "
                        "the model; can't compare", tname, cname)
        return

    isdiff = autogen_context['context']._compare_type(conn_col, metadata_col)

    if isdiff:

        diffs.append(
            ("modify_type", schema, tname, cname,
                    {
                        "existing_nullable": conn_col.nullable,
                        "existing_server_default": conn_col.server_default,
                    },
                    conn_type,
                    metadata_type),
        )
        log.info("Detected type change from %r to %r on '%s.%s'",
            conn_type, metadata_type, tname, cname
        )

def _compare_server_default(schema, tname, cname, conn_col, metadata_col,
                                diffs, autogen_context):

    metadata_default = metadata_col.server_default
    conn_col_default = conn_col.server_default
    if conn_col_default is None and metadata_default is None:
        return False
    rendered_metadata_default = _render_server_default(
                            metadata_default, autogen_context)
    rendered_conn_default = conn_col.server_default.arg.text \
                            if conn_col.server_default else None
    isdiff = autogen_context['context']._compare_server_default(
                        conn_col, metadata_col,
                        rendered_metadata_default,
                        rendered_conn_default
                    )
    if isdiff:
        conn_col_default = rendered_conn_default
        diffs.append(
            ("modify_default", schema, tname, cname,
                {
                    "existing_nullable": conn_col.nullable,
                    "existing_type": conn_col.type,
                },
                conn_col_default,
                metadata_default),
        )
        log.info("Detected server default on column '%s.%s'",
            tname,
            cname
        )



