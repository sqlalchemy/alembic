"""Provide the 'autogenerate' feature which can produce migration operations
automatically."""

import logging

from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.util import OrderedSet
from .compare import _compare_tables
from . import compose
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

    autogen_context = _autogen_context(context, metadata=metadata)

    # as_sql=True is nonsensical here. autogenerate requires a connection
    # it can use to run queries against to get the database schema.
    if context.as_sql:
        raise util.CommandError(
            "autogenerate can't use as_sql=True as it prevents querying "
            "the database for schema information")

    diffs = []

    _produce_net_changes(autogen_context, diffs)

    return diffs


def _render_migration_diffs(context, template_args, imports):

    autogen_context = _autogen_context(context, imports)

    diffs = []
    _produce_net_changes(autogen_context, diffs)
    compose._render_diffs(diffs, autogen_context, template_args)


def _autogen_context(
    context, imports=None, metadata=None, include_symbol=None,
        include_object=None, include_schemas=False):

    opts = context.opts
    metadata = opts['target_metadata'] if metadata is None else metadata
    include_schemas = opts.get('include_schemas', include_schemas)

    include_symbol = opts.get('include_symbol', include_symbol)
    include_object = opts.get('include_object', include_object)

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

    opts = context.opts
    connection = context.bind
    return {
        'imports': imports,
        'connection': connection,
        'dialect': connection.dialect,
        'context': context,
        'opts': opts,
        'metadata': metadata,
        'object_filters': object_filters,
        'include_schemas': include_schemas
    }


def _produce_net_changes(autogen_context, diffs):

    metadata = autogen_context['metadata']
    connection = autogen_context['connection']
    object_filters = autogen_context.get('object_filters', ())
    include_schemas = autogen_context.get('include_schemas', False)

    inspector = Inspector.from_engine(connection)
    conn_table_names = set()

    default_schema = connection.dialect.default_schema_name
    if include_schemas:
        schemas = set(inspector.get_schema_names())
        # replace default schema name with None
        schemas.discard("information_schema")
        # replace the "default" schema with None
        schemas.add(None)
        schemas.discard(default_schema)
    else:
        schemas = [None]

    version_table_schema = autogen_context['context'].version_table_schema
    version_table = autogen_context['context'].version_table

    for s in schemas:
        tables = set(inspector.get_table_names(schema=s))
        if s == version_table_schema:
            tables = tables.difference(
                [autogen_context['context'].version_table]
            )
        conn_table_names.update(zip([s] * len(tables), tables))

    metadata_table_names = OrderedSet(
        [(table.schema, table.name) for table in metadata.sorted_tables]
    ).difference([(version_table_schema, version_table)])

    _compare_tables(conn_table_names, metadata_table_names,
                    object_filters,
                    inspector, metadata, diffs, autogen_context)


