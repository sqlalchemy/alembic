import functools
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import DDLElement

class AlterTable(DDLElement):
    """Represent an ALTER TABLE statement.

    Only the string name and optional schema name of the table
    is required, not a full Table object.

    """
    def __init__(self, table_name, schema=None):
        self.table_name = table_name
        self.schema = schema

class AlterColumn(AlterTable):
    def __init__(self, name, column_name, schema=None):
        super(AlterColumn, self).__init__(name, schema=schema)
        self.column_name = column_name

class ColumnNullable(AlterColumn):
    def __init__(self, name, column_name, nullable, schema=None):
        super(ColumnNullable, self).__init__(name, column_name, schema=schema)
        self.nullable = nullable

class ColumnType(AlterColumn):
    def __init__(self, name, column_name, type_, schema=None):
        super(ColumnType, self).__init__(name, column_name, schema=schema)
        self.type_ = type_

class ColumnName(AlterColumn):
    def __init__(self, name, column_name, newname, schema=None):
        super(ColumnName, self).__init__(name, column_name, schema=schema)
        self.newname = newname

class ColumnDefault(AlterColumn):
    def __init__(self, name, column_name, default, schema=None):
        super(ColumnDefault, self).__init__(name, column_name, schema=schema)
        self.default = default

class AddColumn(AlterTable):
    def __init__(self, name, column, schema=None):
        super(AddColumn, self).__init__(name, schema=schema)
        self.column = column

class DropColumn(AlterTable):
    def __init__(self, name, column, schema=None):
        super(DropColumn, self).__init__(name, schema=schema)
        self.column = column

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
        "NULL" if element.nullable else "SET NOT NULL"
    )

@compiles(ColumnName)
def visit_column_name(element, compiler, **kw):
    return "%s %s RENAME TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        format_column_name(compiler, element.newname)
    )

def quote_dotted(name, quote):
    """quote the elements of a dotted name"""

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

def alter_table(compiler, name, schema):
    return "ALTER TABLE %s" % format_table_name(compiler, name, schema)

def drop_column(compiler, name):
    return 'DROP COLUMN %s' % format_column_name(compiler, name)

def alter_column(compiler, name):
    return 'ALTER COLUMN %s' % format_column_name(compiler, name)

def add_column(compiler, column, **kw):
    return "ADD COLUMN %s" % compiler.get_column_specification(column, **kw)


