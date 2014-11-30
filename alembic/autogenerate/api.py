"""Provide the 'autogenerate' feature which can produce migration operations
automatically."""

import logging
import itertools
import re

from ..compat import StringIO

from mako.pygen import PythonPrinter
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.util import OrderedSet
from .compare import _compare_tables
from .render import _drop_table, _drop_column, _drop_index, _drop_constraint, \
    _add_table, _add_column, _add_index, _add_constraint, _modify_col, \
    _add_fk_constraint
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

    object_filters = _get_object_filters(context.opts)
    include_schemas = context.opts.get('include_schemas', False)

    _produce_net_changes(connection, metadata, diffs, autogen_context,
                         object_filters, include_schemas)

    return diffs

###################################################
# top level


def _produce_migration_diffs(context, template_args,
                             imports, include_symbol=None,
                             include_object=None,
                             include_schemas=False):
    opts = context.opts
    metadata = opts['target_metadata']
    include_schemas = opts.get('include_schemas', include_schemas)

    object_filters = _get_object_filters(opts, include_symbol, include_object)

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

    template_args[opts['upgrade_token']] = _indent(_render_cmd_body(
        _produce_upgrade_commands, diffs, autogen_context))
    template_args[opts['downgrade_token']] = _indent(_render_cmd_body(
        _produce_downgrade_commands, diffs, autogen_context))
    template_args['imports'] = "\n".join(sorted(imports))


def _indent(text):
    text = re.compile(r'^', re.M).sub("    ", text).strip()
    text = re.compile(r' +$', re.M).sub("", text)
    return text


def _render_cmd_body(fn, diffs, autogen_context):

    buf = StringIO()
    printer = PythonPrinter(buf)

    printer.writeline(
        "### commands auto generated by Alembic - "
        "please adjust! ###"
    )

    for line in fn(diffs, autogen_context):
        printer.writeline(line)

    printer.writeline("### end Alembic commands ###")

    return buf.getvalue()


def _get_object_filters(
        context_opts, include_symbol=None, include_object=None):
    include_symbol = context_opts.get('include_symbol', include_symbol)
    include_object = context_opts.get('include_object', include_object)

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

    return object_filters


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


###################################################
# walk structures


def _produce_net_changes(connection, metadata, diffs, autogen_context,
                         object_filters=(),
                         include_schemas=False):
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


def _produce_upgrade_commands(diffs, autogen_context):
    return _produce_commands("upgrade", diffs, autogen_context)


def _produce_downgrade_commands(diffs, autogen_context):
    return _produce_commands("downgrade", diffs, autogen_context)


def _produce_commands(type_, diffs, autogen_context):
    opts = autogen_context['opts']
    render_as_batch = opts.get('render_as_batch', False)

    if diffs:
        if type_ == 'downgrade':
            diffs = reversed(diffs)
        for (schema, table), subdiffs in _group_diffs_by_table(diffs):
            if table is not None and render_as_batch:
                yield "with op.batch_alter_table"\
                    "(%r, schema=%r) as batch_op:" % (table, schema)
                autogen_context['batch_prefix'] = 'batch_op.'
            for diff in subdiffs:
                yield _invoke_command(type_, diff, autogen_context)
            if table is not None and render_as_batch:
                del autogen_context['batch_prefix']
                yield ""
    else:
        yield "pass"


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
        "fk": (_drop_constraint, _add_fk_constraint)
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
        for arg in ("existing_type",
                    "existing_nullable",
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


def _group_diffs_by_table(diffs):
    _adddrop = {
        "table": lambda diff: (None, None),
        "column": lambda diff: (diff[0], diff[1]),
        "index": lambda diff: (diff[0].table.schema, diff[0].table.name),
        "constraint": lambda diff: (diff[0].table.schema, diff[0].table.name),
        "fk": lambda diff: (diff[0].parent.schema, diff[0].parent.name)
    }

    def _derive_table(diff):
        if isinstance(diff, tuple):
            cmd_type = diff[0]
            adddrop, cmd_type = cmd_type.split("_")
            return _adddrop[cmd_type](diff[1:])
        else:
            sname, tname = diff[0][1:3]
            return sname, tname

    return itertools.groupby(diffs, _derive_table)
