import functools

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import DDLElement, Column, \
    ForeignKeyConstraint, CheckConstraint
from sqlalchemy import Integer
from sqlalchemy import types as sqltypes
from sqlalchemy.sql.visitors import traverse
from .. import util

if util.sqla_09:
    from sqlalchemy.sql.elements import quoted_name


class AlterTable(DDLElement):

    """Represent an ALTER TABLE statement.

    Only the string name and optional schema name of the table
    is required, not a full Table object.

    """

    def __init__(self, table_name, schema=None):
        self.table_name = table_name
        self.schema = schema


class RenameTable(AlterTable):

    def __init__(self, old_table_name, new_table_name, schema=None):
        super(RenameTable, self).__init__(old_table_name, schema=schema)
        self.new_table_name = new_table_name


class AlterColumn(AlterTable):

    def __init__(self, name, column_name, schema=None,
                 existing_type=None,
                 existing_nullable=None,
                 existing_server_default=None):
        super(AlterColumn, self).__init__(name, schema=schema)
        self.column_name = column_name
        self.existing_type = sqltypes.to_instance(existing_type) \
            if existing_type is not None else None
        self.existing_nullable = existing_nullable
        self.existing_server_default = existing_server_default


class ColumnNullable(AlterColumn):

    def __init__(self, name, column_name, nullable, **kw):
        super(ColumnNullable, self).__init__(name, column_name,
                                             **kw)
        self.nullable = nullable


class ColumnType(AlterColumn):

    def __init__(self, name, column_name, type_, **kw):
        super(ColumnType, self).__init__(name, column_name,
                                         **kw)
        self.type_ = sqltypes.to_instance(type_)


class ColumnName(AlterColumn):

    def __init__(self, name, column_name, newname, **kw):
        super(ColumnName, self).__init__(name, column_name, **kw)
        self.newname = newname


class ColumnDefault(AlterColumn):

    def __init__(self, name, column_name, default, **kw):
        super(ColumnDefault, self).__init__(name, column_name, **kw)
        self.default = default


class AddColumn(AlterTable):

    def __init__(self, name, column, schema=None):
        super(AddColumn, self).__init__(name, schema=schema)
        self.column = column


class DropColumn(AlterTable):

    def __init__(self, name, column, schema=None):
        super(DropColumn, self).__init__(name, schema=schema)
        self.column = column


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


def _table_for_constraint(constraint):
    if isinstance(constraint, ForeignKeyConstraint):
        return constraint.parent
    else:
        return constraint.table


def _columns_for_constraint(constraint):
    if isinstance(constraint, ForeignKeyConstraint):
        return [fk.parent for fk in constraint.elements]
    elif isinstance(constraint, CheckConstraint):
        return _find_columns(constraint.sqltext)
    else:
        return list(constraint.columns)


def _fk_spec(constraint):
    if util.sqla_100:
        source_columns = constraint.column_keys
    else:
        source_columns = [
            element.parent.key for element in constraint.elements]

    source_table = constraint.parent.name
    source_schema = constraint.parent.schema
    target_schema = constraint.elements[0].column.table.schema
    target_table = constraint.elements[0].column.table.name
    target_columns = [element.column.name for element in constraint.elements]

    return (
        source_schema, source_table,
        source_columns, target_schema, target_table, target_columns)


def _is_type_bound(constraint):
    # this deals with SQLAlchemy #3260, don't copy CHECK constraints
    # that will be generated by the type.
    if util.sqla_100:
        # new feature added for #3260
        return constraint._type_bound
    else:
        # old way, look at what we know Boolean/Enum to use
        return (
            constraint._create_rule is not None and
            isinstance(
                getattr(constraint._create_rule, "target", None),
                sqltypes.SchemaType)
        )


def _find_columns(clause):
    """locate Column objects within the given expression."""

    cols = set()
    traverse(clause, {}, {'column': cols.add})
    return cols


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
