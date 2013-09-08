"""Provide the 'autogenerate' feature which can produce migration operations
automatically."""

import logging
import re

from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.util import OrderedSet
from .compare import _compare_tables
from .render import _drop_table, _drop_column, _drop_index, _drop_constraint, \
        _add_table, _add_column, _add_index, _add_constraint, _modify_col
from .. import util

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


###################################################
# element comparison


###################################################
# render python


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
