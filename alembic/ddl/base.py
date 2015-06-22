import functools

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import Column
from sqlalchemy import Integer
from .. import util

# backwards compat
from ..util.sqla_compat import (  # noqa
    _table_for_constraint,
    _columns_for_constraint, _fk_spec, _is_type_bound, _find_columns)

# referenced in this module, but note
# also needs to be here for backwards compat
from ..operations import (  # noqa
    RenameTable, AddColumn, DropColumn,
    ColumnNullable, ColumnDefault, ColumnType, ColumnName,
    AlterColumn
)


if util.sqla_09:
    from sqlalchemy.sql.elements import quoted_name


@compiles(RenameTable)
def visit_rename_table(element, compiler, **kw):
    return "%s RENAME TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_table_name(compiler, element.new_table_name, element.schema)
    )


@compiles(AddColumn)
def visit_add_column(element, compiler, **kw):
    return "%s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        add_column(compiler, element.column, **kw)
    )


@compiles(DropColumn)
def visit_drop_column(element, compiler, **kw):
    return "%s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        drop_column(compiler, element.column.name, **kw)
    )


@compiles(ColumnNullable)
def visit_column_nullable(element, compiler, **kw):
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "DROP NOT NULL" if element.nullable else "SET NOT NULL"
    )


@compiles(ColumnType)
def visit_column_type(element, compiler, **kw):
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "TYPE %s" % format_type(compiler, element.type_)
    )


@compiles(ColumnName)
def visit_column_name(element, compiler, **kw):
    return "%s RENAME %s TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        format_column_name(compiler, element.newname)
    )


@compiles(ColumnDefault)
def visit_column_default(element, compiler, **kw):
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "SET DEFAULT %s" %
        format_server_default(compiler, element.default)
        if element.default is not None
        else "DROP DEFAULT"
    )


def quote_dotted(name, quote):
    """quote the elements of a dotted name"""

    if util.sqla_09 and isinstance(name, quoted_name):
        return quote(name)
    result = '.'.join([quote(x) for x in name.split('.')])
    return result


def format_table_name(compiler, name, schema):
    quote = functools.partial(compiler.preparer.quote, force=None)
    if schema:
        return quote_dotted(schema, quote) + "." + quote(name)
    else:
        return quote(name)


def format_column_name(compiler, name):
    return compiler.preparer.quote(name, None)


def format_server_default(compiler, default):
    return compiler.get_column_default_string(
        Column("x", Integer, server_default=default)
    )


def format_type(compiler, type_):
    return compiler.dialect.type_compiler.process(type_)


def alter_table(compiler, name, schema):
    return "ALTER TABLE %s" % format_table_name(compiler, name, schema)


def drop_column(compiler, name):
    return 'DROP COLUMN %s' % format_column_name(compiler, name)


def alter_column(compiler, name):
    return 'ALTER COLUMN %s' % format_column_name(compiler, name)


def add_column(compiler, column, **kw):
    return "ADD COLUMN %s" % compiler.get_column_specification(column, **kw)
