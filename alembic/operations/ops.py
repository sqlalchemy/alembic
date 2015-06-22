from sqlalchemy.schema import DDLElement, AddConstraint, CreateIndex
from sqlalchemy import types as sqltypes


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

