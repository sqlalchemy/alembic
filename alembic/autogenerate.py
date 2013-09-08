"""Provide the 'autogenerate' feature which can produce migration operations
automatically."""

import logging
import re

from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.util import OrderedSet
from sqlalchemy import schema as sa_schema, types as sqltypes

from . import util
from .compat import string_types

log = logging.getLogger(__name__)

###################################################
# public
def compare_metadata(context, metadata):
    """Compare a database schema to that given in a
    :class:`~sqlalchemy.schema.MetaData` instance.

    The database connection is presented in the context
    of a :class:`.MigrationContext` object, which
    provides database connectivity as well as optional
    comparison functions to use for datatypes and
    server defaults - see the "autogenerate" arguments
    at :meth:`.EnvironmentContext.configure`
    for details on these.

    The return format is a list of "diff" directives,
    each representing individual differences::

        from alembic.migration import MigrationContext
        from alembic.autogenerate import compare_metadata
        from sqlalchemy.schema import SchemaItem
        from sqlalchemy.types import TypeEngine
        from sqlalchemy import (create_engine, MetaData, Column,
                Integer, String, Table)
        import pprint

        engine = create_engine("sqlite://")

        engine.execute('''
            create table foo (
                id integer not null primary key,
                old_data varchar,
                x integer
            )''')

        engine.execute('''
            create table bar (
                data varchar
            )''')

        metadata = MetaData()
        Table('foo', metadata,
            Column('id', Integer, primary_key=True),
            Column('data', Integer),
            Column('x', Integer, nullable=False)
        )
        Table('bat', metadata,
            Column('info', String)
        )

        mc = MigrationContext.configure(engine.connect())

        diff = compare_metadata(mc, metadata)
        pprint.pprint(diff, indent=2, width=20)

    Output::

        [ ( 'add_table',
            Table('bat', MetaData(bind=None),
                Column('info', String(), table=<bat>), schema=None)),
          ( 'remove_table',
            Table(u'bar', MetaData(bind=None),
                Column(u'data', VARCHAR(), table=<bar>), schema=None)),
          ( 'add_column',
            None,
            'foo',
            Column('data', Integer(), table=<foo>)),
          ( 'remove_column',
            None,
            'foo',
            Column(u'old_data', VARCHAR(), table=None)),
          [ ( 'modify_nullable',
              None,
              'foo',
              u'x',
              { 'existing_server_default': None,
                'existing_type': INTEGER()},
              True,
              False)]]


    :param context: a :class:`.MigrationContext`
     instance.
    :param metadata: a :class:`~sqlalchemy.schema.MetaData`
     instance.

    """
    autogen_context, connection = _autogen_context(context, None)
    diffs = []
    _produce_net_changes(connection, metadata, diffs, autogen_context)
    return diffs

###################################################
# top level

def _produce_migration_diffs(context, template_args,
                                imports, include_symbol=None,
                                include_object=None,
                                include_schemas=False):
    opts = context.opts
    metadata = opts['target_metadata']
    include_object = opts.get('include_object', include_object)
    include_symbol = opts.get('include_symbol', include_symbol)
    include_schemas = opts.get('include_schemas', include_schemas)

    object_filters = []
    if include_symbol:
        def include_symbol_filter(object, name, type_, reflected, compare_to):
            if type_ == "table":
                return include_symbol(name, object.schema)
            else:
                return True
        object_filters.append(include_symbol_filter)
    if include_object:
        object_filters.append(include_object)


    if metadata is None:
        raise util.CommandError(
                "Can't proceed with --autogenerate option; environment "
                "script %s does not provide "
                "a MetaData object to the context." % (
                    context.script.env_py_location
                ))
    autogen_context, connection = _autogen_context(context, imports)

    diffs = []
    _produce_net_changes(connection, metadata, diffs,
                                autogen_context, object_filters, include_schemas)
    template_args[opts['upgrade_token']] = \
            _indent(_produce_upgrade_commands(diffs, autogen_context))
    template_args[opts['downgrade_token']] = \
            _indent(_produce_downgrade_commands(diffs, autogen_context))
    template_args['imports'] = "\n".join(sorted(imports))

def _autogen_context(context, imports):
    opts = context.opts
    connection = context.bind
    return {
        'imports': imports,
        'connection': connection,
        'dialect': connection.dialect,
        'context': context,
        'opts': opts
    }, connection

def _indent(text):
    text = "### commands auto generated by Alembic - "\
                    "please adjust! ###\n" + text
    text += "\n### end Alembic commands ###"
    text = re.compile(r'^', re.M).sub("    ", text).strip()
    return text

###################################################
# walk structures


def _run_filters(object_, name, type_, reflected, compare_to, object_filters):
    for fn in object_filters:
        if not fn(object_, name, type_, reflected, compare_to):
            return False
    else:
        return True

def _produce_net_changes(connection, metadata, diffs, autogen_context,
                            object_filters=(),
                            include_schemas=False):
    inspector = Inspector.from_engine(connection)
    # TODO: not hardcode alembic_version here ?
    conn_table_names = set()
    if include_schemas:
        schemas = set(inspector.get_schema_names())
        # replace default schema name with None
        schemas.discard("information_schema")
        # replace the "default" schema with None
        schemas.add(None)
        schemas.discard(connection.dialect.default_schema_name)
    else:
        schemas = [None]

    for s in schemas:
        tables = set(inspector.get_table_names(schema=s)).\
                difference(['alembic_version'])
        conn_table_names.update(zip([s] * len(tables), tables))

    metadata_table_names = OrderedSet([(table.schema, table.name)
                                for table in metadata.sorted_tables])

    _compare_tables(conn_table_names, metadata_table_names,
                    object_filters,
                    inspector, metadata, diffs, autogen_context)

def _compare_tables(conn_table_names, metadata_table_names,
                    object_filters,
                    inspector, metadata, diffs, autogen_context):

    for s, tname in metadata_table_names.difference(conn_table_names):
        name = '%s.%s' % (s, tname) if s else tname
        metadata_table = metadata.tables[sa_schema._get_table_key(tname, s)]
        if _run_filters(metadata_table, tname, "table", False, None, object_filters):
            diffs.append(("add_table", metadata.tables[name]))
            log.info("Detected added table %r", name)

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

    if hasattr(inspector, 'get_unique_constraints'):
        can_inspect_uniques = True
    else:
        log.warn(
        "Unique constraints have not been inspected because the version "
        "of SQLAlchemy in use does not support it. Please see "
        "SQLAlchemy's documentation for which versions' "
        "sqlalchemy.engine.reflection.Inspector object include "
        "get_unique_constraints()."
        )
        can_inspect_uniques = False
        c_uniques = {}

    for s, tname in sorted(existing_tables):
        name = '%s.%s' % (s, tname) if s else tname
        metadata_table = metadata.tables[name]
        conn_table = existing_metadata.tables[name]
        if _run_filters(metadata_table, tname, "table", False, conn_table, object_filters):
            _compare_columns(s, tname, object_filters,
                    conn_table,
                    metadata_table,
                    diffs, autogen_context, inspector)
            if can_inspect_uniques:
                c_uniques = _compare_uniques(s, tname, 
                        object_filters, conn_table, metadata_table,
                        diffs, autogen_context, inspector)
            _compare_indexes(s, tname, object_filters,
                    conn_table,
                    metadata_table,
                    diffs, autogen_context, inspector, 
                    can_inspect_uniques, c_uniques)

    # TODO:
    # table constraints
    # sequences

###################################################
# element comparison

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


def _compare_uniques(schema, tname, object_filters, conn_table, 
            metadata_table, diffs, autogen_context, inspector):

    m_objs = dict(
        (i.name or _autogenerate_unique_constraint_name(i), i) \
        for i in metadata_table.constraints \
        if isinstance(i, sa_schema.UniqueConstraint)
    )
    m_keys = set(m_objs.keys())

    if hasattr(inspector, 'get_unique_constraints'):
        try:
            conn_uniques = inspector.get_unique_constraints(tname)
        except NoSuchTableError:
            conn_uniques = []
    else:
        conn_uniques = []
    c_objs = dict(
        (i['name'] or _autogenerate_unique_constraint_name({
            'table': conn_table, 'columns': i['columns']}),
         _make_unique_constraint(i, conn_table)) \
        for i in conn_uniques
    )
    c_keys = set(c_objs.keys())

    for key in (m_keys - c_keys):
        meta = m_objs[key]
        diffs.append(("add_constraint", meta))
        log.info("Detected added unique constraint '%s' on %s",
            key, ', '.join([
                "'%s'" % y.name for y in meta.columns
                ])
        )

    for key in (c_keys - m_keys):
        diffs.append(("remove_constraint", c_objs[key]))
        log.info("Detected removed unique constraint '%s' on '%s'",
            key, tname
        )

    for key in (m_keys & c_keys):
        meta = m_objs[key]
        conn = c_objs[key]
        conn_cols = [col.name for col in conn.columns]
        meta_cols = [col.name for col in meta.columns]

        if meta_cols != conn_cols:
            diffs.append(("remove_constraint", conn))
            diffs.append(("add_constraint", meta))
            log.info("Detected changed unique constraint '%s' on '%s':%s",
                key, tname, ' columns %r to %r' % (conn_cols, meta_cols)
            )

    # inspector.get_indexes() can conflate indexes and unique 
    # constraints when unique constraints are implemented by the database 
    # as an index. so we pass uniques to _compare_indexes() for 
    # deduplication
    return c_keys

def _compare_indexes(schema, tname, object_filters, conn_table, 
            metadata_table, diffs, autogen_context, inspector, 
            can_inspect_uniques, c_uniques_keys):

    try:
        c_objs = dict(
            (i['name'], _make_index(i, conn_table)) \
            for i in inspector.get_indexes(tname)
        )
    except NoSuchTableError:
        c_objs = {}

    # deduplicate between conn uniques and indexes, because either:
    #   1. a backend reports uniques as indexes, because uniques 
    #      are implemented as a type of index.
    #   2. our SQLA version does not reflect uniques
    # in either case, we need to avoid comparing a connection index 
    # for what we can tell from the metadata is meant as a unique constraint
    if not can_inspect_uniques:
        c_uniques_keys = set([
            i.name or _autogenerate_unique_constraint_name(i) \
            for i in metadata_table.constraints \
            if isinstance(i, sa_schema.UniqueConstraint)]
        )
    for name in c_objs.keys():
        if name in c_uniques_keys:
            c_objs.pop(name)

    c_keys = set(c_objs.keys())

    m_objs = dict(
        (i.name, i) for i in metadata_table.indexes \
        if i.name not in c_uniques_keys
    )
    m_keys = set(m_objs.keys())

    for key in (m_keys - c_keys):
        meta = m_objs[key]
        diffs.append(("add_index", meta))
        log.info("Detected added index '%s' on %s",
            key, ', '.join([
                "'%s'" % y.name for y in meta.expressions
                ])
        )

    for key in (c_keys - m_keys):
        diffs.append(("remove_index", c_objs[key]))
        log.info("Detected removed index '%s' on '%s'", key, tname)

    for key in (m_keys & c_keys):

        meta = m_objs[key]
        conn = c_objs[key]
        conn_exps = [exp.name for exp in conn.expressions]
        meta_exps = [exp.name for exp in meta.expressions]

        # todo: kwargs can differ, e.g., changing the type of index
        #       we can't detect this via the inspection API, though
        if (meta.unique or False != conn.unique or False)\
            or meta_exps != conn_exps:
            diffs.append(("remove_index", conn))
            diffs.append(("add_index", meta))

            msg = []
            if meta.unique or False != conn.unique or False:
                msg.append(' unique=%r to unique=%r' % (
                    conn.unique, meta.unique
                ))
            if meta_exps != conn_exps: 
                msg.append(' columns %r to %r' % (
                    conn_exps, meta_exps
                ))
            log.info("Detected changed index '%s' on '%s':%s",
                key, tname, ', '.join(msg)
            )

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


###################################################
# produce command structure

def _produce_upgrade_commands(diffs, autogen_context):
    buf = []
    for diff in diffs:
        buf.append(_invoke_command("upgrade", diff, autogen_context))
    if not buf:
        buf = ["pass"]
    return "\n".join(buf)

def _produce_downgrade_commands(diffs, autogen_context):
    buf = []
    for diff in reversed(diffs):
        buf.append(_invoke_command("downgrade", diff, autogen_context))
    if not buf:
        buf = ["pass"]
    return "\n".join(buf)

def _invoke_command(updown, args, autogen_context):
    if isinstance(args, tuple):
        return _invoke_adddrop_command(updown, args, autogen_context)
    else:
        return _invoke_modify_command(updown, args, autogen_context)

def _invoke_adddrop_command(updown, args, autogen_context):
    cmd_type = args[0]
    adddrop, cmd_type = cmd_type.split("_")

    cmd_args = args[1:] + (autogen_context,)

    _commands = {
        "table": (_drop_table, _add_table),
        "column": (_drop_column, _add_column),
        "index": (_drop_index, _add_index),
        "constraint": (_drop_constraint, _add_constraint),
    }

    cmd_callables = _commands[cmd_type]

    if (
        updown == "upgrade" and adddrop == "add"
    ) or (
        updown == "downgrade" and adddrop == "remove"
    ):
        return cmd_callables[1](*cmd_args)
    else:
        return cmd_callables[0](*cmd_args)

def _invoke_modify_command(updown, args, autogen_context):
    sname, tname, cname = args[0][1:4]
    kw = {}

    _arg_struct = {
        "modify_type": ("existing_type", "type_"),
        "modify_nullable": ("existing_nullable", "nullable"),
        "modify_default": ("existing_server_default", "server_default"),
    }
    for diff in args:
        diff_kw = diff[4]
        for arg in ("existing_type", \
                "existing_nullable", \
                "existing_server_default"):
            if arg in diff_kw:
                kw.setdefault(arg, diff_kw[arg])
        old_kw, new_kw = _arg_struct[diff[0]]
        if updown == "upgrade":
            kw[new_kw] = diff[-1]
            kw[old_kw] = diff[-2]
        else:
            kw[new_kw] = diff[-2]
            kw[old_kw] = diff[-1]

    if "nullable" in kw:
        kw.pop("existing_nullable", None)
    if "server_default" in kw:
        kw.pop("existing_server_default", None)
    return _modify_col(tname, cname, autogen_context, schema=sname, **kw)

###################################################
# render python

def _add_table(table, autogen_context):
    text = "%(prefix)screate_table(%(tablename)r,\n%(args)s" % {
        'tablename': table.name,
        'prefix': _alembic_autogenerate_prefix(autogen_context),
        'args': ',\n'.join(
            [col for col in
                [_render_column(col, autogen_context) for col in table.c]
            if col] +
            sorted([rcons for rcons in
                [_render_constraint(cons, autogen_context) for cons in
                    table.constraints]
                if rcons is not None
            ])
        )
    }
    if table.schema:
        text += ",\nschema=%r" % table.schema
    for k in sorted(table.kwargs):
        text += ",\n%s=%r" % (k.replace(" ", "_"), table.kwargs[k])
    text += "\n)"
    return text

def _drop_table(table, autogen_context):
    text = "%(prefix)sdrop_table(%(tname)r" % {
            "prefix": _alembic_autogenerate_prefix(autogen_context),
            "tname": table.name
        }
    if table.schema:
        text += ", schema=%r" % table.schema
    text += ")"
    return text

def _add_index(index, autogen_context):
    """
    Generate Alembic operations for the CREATE INDEX of an 
    :class:`~sqlalchemy.schema.Index` instance.
    """
    text = "op.create_index('%(name)s', '%(table)s', %(columns)s, unique=%(unique)r%(schema)s%(kwargs)s)" % {
        'name': index.name,
        'table': index.table,
        'columns': [exp.name for exp in index.expressions],
        'unique': index.unique or False,
        'schema': (", schema='%s'" % index.table.schema) if index.table.schema else '',
        'kwargs': (', '+', '.join(
            ["%s='%s'" % (key, val) for key, val in index.kwargs.items()]))\
            if len(index.kwargs) else ''
    }
    return text

def _drop_index(index, autogen_context):
    """
    Generate Alembic operations for the DROP INDEX of an 
    :class:`~sqlalchemy.schema.Index` instance.
    """
    text = "op.drop_index('%s', '%s')" % (index.name, index.table)
    return text

def _autogenerate_unique_constraint_name(constraint):
    """
    In order to both create and drop a constraint, we need a name known 
    ahead of time.
    """
    return 'uq_%s_%s' % (
        str(constraint.table).replace('.', '_'),
        '_'.join([col.name for col in constraint.columns])
    )

def _add_unique_constraint(constraint, autogen_context):
    """
    Generate Alembic operations for the ALTER TABLE .. ADD CONSTRAINT ... 
    UNIQUE of a :class:`~sqlalchemy.schema.UniqueConstraint` instance.
    """
    text = "%(prefix)screate_unique_constraint('%(name)s', '%(table)s', %(columns)s"\
            "%(deferrable)s%(initially)s%(schema)s)" % {
            'prefix': _alembic_autogenerate_prefix(autogen_context),
            'name': constraint.name or _autogenerate_unique_constraint_name(constraint),
            'table': constraint.table,
            'columns': [col.name for col in constraint.columns],
            'deferrable': (", deferrable='%s'" % constraint.deferrable) if constraint.deferrable else '',
            'initially': (", initially='%s'" % constraint.initially) if constraint.initially else '',
            'schema': (", schema='%s'" % constraint.table.schema) if constraint.table.schema else ''
        }
    return text

def _add_fk_constraint(constraint, autogen_context):
    raise NotImplementedError()

def _add_pk_constraint(constraint, autogen_context):
    raise NotImplementedError()

def _add_check_constraint(constraint, autogen_context):
    raise NotImplementedError()

def _add_constraint(constraint, autogen_context):
    """
    Dispatcher for the different types of constraints.
    """
    funcs = {
        "unique_constraint": _add_unique_constraint,
        "foreign_key_constraint": _add_fk_constraint,
        "primary_key_constraint": _add_pk_constraint,
        "check_constraint": _add_check_constraint,
        "column_check_constraint": _add_check_constraint,
    }
    return funcs[constraint.__visit_name__](constraint, autogen_context)

def _drop_constraint(constraint, autogen_context):
    """
    Generate Alembic operations for the ALTER TABLE ... DROP CONSTRAINT 
    of a  :class:`~sqlalchemy.schema.UniqueConstraint` instance.
    """
    text = "%(prefix)sdrop_constraint('%(name)s', '%(table)s')" % {
            'prefix': _alembic_autogenerate_prefix(autogen_context),
            'name': constraint.name or _autogenerate_unique_constraint_name(constraint),
            'table': constraint.table,
    }
    return text

def _add_column(schema, tname, column, autogen_context):
    text = "%(prefix)sadd_column(%(tname)r, %(column)s" % {
            "prefix": _alembic_autogenerate_prefix(autogen_context),
            "tname": tname,
            "column": _render_column(column, autogen_context)
            }
    if schema:
        text += ", schema=%r" % schema
    text += ")"
    return text

def _drop_column(schema, tname, column, autogen_context):
    text = "%(prefix)sdrop_column(%(tname)r, %(cname)r" % {
            "prefix": _alembic_autogenerate_prefix(autogen_context),
            "tname": tname,
            "cname": column.name
            }
    if schema:
        text += ", schema=%r" % schema
    text += ")"
    return text

def _modify_col(tname, cname,
                autogen_context,
                server_default=False,
                type_=None,
                nullable=None,
                existing_type=None,
                existing_nullable=None,
                existing_server_default=False,
                schema=None):
    sqla_prefix = _sqlalchemy_autogenerate_prefix(autogen_context)
    indent = " " * 11
    text = "%(prefix)salter_column(%(tname)r, %(cname)r" % {
                            'prefix': _alembic_autogenerate_prefix(
                                                autogen_context),
                            'tname': tname,
                            'cname': cname}
    text += ",\n%sexisting_type=%s" % (indent,
                    _repr_type(sqla_prefix, existing_type, autogen_context))
    if server_default is not False:
        rendered = _render_server_default(
                                server_default, autogen_context)
        text += ",\n%sserver_default=%s" % (indent, rendered)

    if type_ is not None:
        text += ",\n%stype_=%s" % (indent,
                        _repr_type(sqla_prefix, type_, autogen_context))
    if nullable is not None:
        text += ",\n%snullable=%r" % (
                        indent, nullable,)
    if existing_nullable is not None:
        text += ",\n%sexisting_nullable=%r" % (
                        indent, existing_nullable)
    if existing_server_default:
        rendered = _render_server_default(
                            existing_server_default,
                            autogen_context)
        text += ",\n%sexisting_server_default=%s" % (
                        indent, rendered)
    if schema:
        text += ",\n%sschema=%r" % (indent, schema)
    text += ")"
    return text

def _sqlalchemy_autogenerate_prefix(autogen_context):
    return autogen_context['opts']['sqlalchemy_module_prefix'] or ''

def _alembic_autogenerate_prefix(autogen_context):
    return autogen_context['opts']['alembic_module_prefix'] or ''

def _user_defined_render(type_, object_, autogen_context):
    if 'opts' in autogen_context and \
            'render_item' in autogen_context['opts']:
        render = autogen_context['opts']['render_item']
        if render:
            rendered = render(type_, object_, autogen_context)
            if rendered is not False:
                return rendered
    return False

def _render_column(column, autogen_context):
    rendered = _user_defined_render("column", column, autogen_context)
    if rendered is not False:
        return rendered

    opts = []
    if column.server_default:
        rendered = _render_server_default(
                            column.server_default, autogen_context
                    )
        if rendered:
            opts.append(("server_default", rendered))

    if not column.autoincrement:
        opts.append(("autoincrement", column.autoincrement))

    if column.nullable is not None:
        opts.append(("nullable", column.nullable))

    # TODO: for non-ascii colname, assign a "key"
    return "%(prefix)sColumn(%(name)r, %(type)s, %(kw)s)" % {
        'prefix': _sqlalchemy_autogenerate_prefix(autogen_context),
        'name': column.name,
        'type': _repr_type(_sqlalchemy_autogenerate_prefix(autogen_context),
                                column.type, autogen_context),
        'kw': ", ".join(["%s=%s" % (kwname, val) for kwname, val in opts])
    }

def _render_server_default(default, autogen_context):
    rendered = _user_defined_render("server_default", default, autogen_context)
    if rendered is not False:
        return rendered

    if isinstance(default, sa_schema.DefaultClause):
        if isinstance(default.arg, string_types):
            default = default.arg
        else:
            default = str(default.arg.compile(
                            dialect=autogen_context['dialect']))
    if isinstance(default, string_types):
        # TODO: this is just a hack to get
        # tests to pass until we figure out
        # WTF sqlite is doing
        default = re.sub(r"^'|'$", "", default)
        return repr(default)
    else:
        return None

def _repr_type(prefix, type_, autogen_context):
    rendered = _user_defined_render("type", type_, autogen_context)
    if rendered is not False:
        return rendered

    mod = type(type_).__module__
    imports = autogen_context.get('imports', None)
    if mod.startswith("sqlalchemy.dialects"):
        dname = re.match(r"sqlalchemy\.dialects\.(\w+)", mod).group(1)
        if imports is not None:
            imports.add("from sqlalchemy.dialects import %s" % dname)
        return "%s.%r" % (dname, type_)
    else:
        return "%s%r" % (prefix, type_)

def _render_constraint(constraint, autogen_context):
    renderer = _constraint_renderers.get(type(constraint), None)
    if renderer:
        return renderer(constraint, autogen_context)
    else:
        return None

def _render_primary_key(constraint, autogen_context):
    rendered = _user_defined_render("primary_key", constraint, autogen_context)
    if rendered is not False:
        return rendered

    opts = []
    if constraint.name:
        opts.append(("name", repr(constraint.name)))
    return "%(prefix)sPrimaryKeyConstraint(%(args)s)" % {
        "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
        "args": ", ".join(
            [repr(c.key) for c in constraint.columns] +
            ["%s=%s" % (kwname, val) for kwname, val in opts]
        ),
    }

def _fk_colspec(fk, metadata_schema):
    """Implement a 'safe' version of ForeignKey._get_colspec() that
    never tries to resolve the remote table.

    """
    if metadata_schema is None:
        return fk._get_colspec()
    else:
        # need to render schema breaking up tokens by hand, since the
        # ForeignKeyConstraint here may not actually have a remote
        # Table present
        tokens = fk._colspec.split(".")
        # no schema in the colspec, render it
        if len(tokens) == 2:
            return "%s.%s" % (metadata_schema, fk._colspec)
        else:
            return fk._colspec

def _render_foreign_key(constraint, autogen_context):
    rendered = _user_defined_render("foreign_key", constraint, autogen_context)
    if rendered is not False:
        return rendered

    opts = []
    if constraint.name:
        opts.append(("name", repr(constraint.name)))
    if constraint.onupdate:
        opts.append(("onupdate", repr(constraint.onupdate)))
    if constraint.ondelete:
        opts.append(("ondelete", repr(constraint.ondelete)))
    if constraint.initially:
        opts.append(("initially", repr(constraint.initially)))
    if constraint.deferrable:
        opts.append(("deferrable", repr(constraint.deferrable)))
    if constraint.use_alter:
        opts.append(("use_alter", repr(constraint.use_alter)))

    apply_metadata_schema = constraint.parent.metadata.schema
    return "%(prefix)sForeignKeyConstraint([%(cols)s], "\
            "[%(refcols)s], %(args)s)" % {
        "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
        "cols": ", ".join("'%s'" % f.parent.key for f in constraint.elements),
        "refcols": ", ".join(repr(_fk_colspec(f, apply_metadata_schema))
                            for f in constraint.elements),
        "args": ", ".join(
            ["%s=%s" % (kwname, val) for kwname, val in opts]
        ),
    }

def _render_check_constraint(constraint, autogen_context):
    rendered = _user_defined_render("check", constraint, autogen_context)
    if rendered is not False:
        return rendered

    # detect the constraint being part of
    # a parent type which is probably in the Table already.
    # ideally SQLAlchemy would give us more of a first class
    # way to detect this.
    if constraint._create_rule and \
        hasattr(constraint._create_rule, 'target') and \
        isinstance(constraint._create_rule.target,
                sqltypes.TypeEngine):
        return None
    opts = []
    if constraint.name:
        opts.append(("name", repr(constraint.name)))
    return "%(prefix)sCheckConstraint(%(sqltext)r%(opts)s)" % {
            "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
            "opts": ", " + (", ".join("%s=%s" % (k, v)
                            for k, v in opts)) if opts else "",
            "sqltext": str(
                constraint.sqltext.compile(
                    dialect=autogen_context['dialect']
                )
            )
        }

def _render_unique_constraint(constraint, autogen_context):
    rendered = _user_defined_render("unique", constraint, autogen_context)
    if rendered is not False:
        return rendered

    opts = []
    if constraint.name:
        opts.append(("name", "'%s'" % constraint.name))
    return "%(prefix)sUniqueConstraint(%(cols)s%(opts)s)" % {
        'opts': ", " + (", ".join("%s=%s" % (k, v)
                            for k, v in opts)) if opts else "",
        'cols': ",".join(["'%s'" % c.name for c in constraint.columns]),
        "prefix": _sqlalchemy_autogenerate_prefix(autogen_context)
        }
_constraint_renderers = {
    sa_schema.PrimaryKeyConstraint: _render_primary_key,
    sa_schema.ForeignKeyConstraint: _render_foreign_key,
    sa_schema.UniqueConstraint: _render_unique_constraint,
    sa_schema.CheckConstraint: _render_check_constraint
}
