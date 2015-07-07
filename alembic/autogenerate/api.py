"""Provide the 'autogenerate' feature which can produce migration operations
automatically."""

from ..operations import ops
from . import render
from . import compare
from .. import util


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

    .. seealso::

        :func:`.produce_migrations` - produces a :class:`.MigrationScript`
        structure based on metadata comparison.

    """

    migration_script = produce_migrations(context, metadata)
    return migration_script.upgrade_ops.as_diffs()


def produce_migrations(context, metadata):
    """Produce a :class:`.MigrationScript` structure based on schema
    comparison.

    This function does essentially what :func:`.compare_metadata` does,
    but then runs the resulting list of diffs to produce the full
    :class:`.MigrationScript` object.   For an example of what this looks like,
    see the example in :ref:`customizing_revision`.

    .. versionadded:: 0.8.0

    .. seealso::

        :func:`.compare_metadata` - returns more fundamental "diff"
        data from comparing a schema.

    """

    autogen_context = _autogen_context(context, metadata=metadata)

    upgrade_ops = ops.UpgradeOps([])
    compare._produce_net_changes(autogen_context, upgrade_ops)

    migration_script = ops.MigrationScript(
        rev_id=None,
        upgrade_ops=upgrade_ops,
        downgrade_ops=upgrade_ops.reverse(),
    )

    return migration_script


def render_python_code(
    up_or_down_op,
    sqlalchemy_module_prefix='sa.',
    alembic_module_prefix='op.',
    imports=(),
    render_item=None,
):
    """Render Python code given an :class:`.UpgradeOps` or
    :class:`.DowngradeOps` object.

    This is a convenience function that can be used to test the
    autogenerate output of a user-defined :class:`.MigrationScript` structure.

    """
    autogen_context = {
        'opts': {
            'sqlalchemy_module_prefix': sqlalchemy_module_prefix,
            'alembic_module_prefix': alembic_module_prefix,
            'render_item': render_item,
        },
        'imports': set(imports)
    }
    return render._indent(render._render_cmd_body(
        up_or_down_op, autogen_context))


def _render_migration_diffs(context, template_args, imports):
    """legacy, used by test_autogen_composition at the moment"""

    autogen_context = _autogen_context(context, imports=imports)

    upgrade_ops = ops.UpgradeOps([])
    compare._produce_net_changes(autogen_context, upgrade_ops)

    migration_script = ops.MigrationScript(
        rev_id=None,
        upgrade_ops=upgrade_ops,
        downgrade_ops=upgrade_ops.reverse(),
    )

    render._render_migration_script(
        autogen_context, migration_script, template_args
    )


def _autogen_context(
    context, imports=None, metadata=None, include_symbol=None,
        include_object=None, include_schemas=False):

    # as_sql=True is nonsensical here. autogenerate requires a connection
    # it can use to run queries against to get the database schema.
    if context.as_sql:
        raise util.CommandError(
            "autogenerate can't use as_sql=True as it prevents querying "
            "the database for schema information")

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
        'imports': imports if imports is not None else set(),
        'connection': connection,
        'dialect': connection.dialect,
        'context': context,
        'opts': opts,
        'metadata': metadata,
        'object_filters': object_filters,
        'include_schemas': include_schemas
    }

