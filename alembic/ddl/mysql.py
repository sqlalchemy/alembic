from alembic.ddl.impl import DefaultImpl
from alembic.ddl.base import ColumnNullable, ColumnName, ColumnDefault, ColumnType
from sqlalchemy.ext.compiler import compiles
from alembic.ddl.base import alter_table

class MySQLImpl(DefaultImpl):
    __dialect__ = 'mysql'


@compiles(ColumnNullable, 'mysql')
def _change_column_nullable(element, compiler, **kw):
    return _mysql_change(
        element, compiler,
        nullable=element.nullable,
    )

@compiles(ColumnName, 'mysql')
def _change_column_name(element, compiler, **kw):
    return _mysql_change(
        element, compiler,
        name=element.newname,
    )

@compiles(ColumnDefault, 'mysql')
def _change_column_default(element, compiler, **kw):
    return _mysql_change(
        element, compiler,
        server_default=element.default,
    )

@compiles(ColumnType, 'mysql')
def _change_column_type(element, compiler, **kw):
    return _mysql_change(
        element, compiler,
        type_=element.type_
    )

def _mysql_change(element, compiler, nullable=None, 
                server_default=False, type_=None,
                name=None):
    if name is None:
        name = element.column_name
    if nullable is None:
        nullable=True
    if server_default is False:
        server_default = element.existing_server_default
    if type_ is None:
        if element.existing_type is None:
            raise util.CommandError("All MySQL column alterations "
                        "require the existing type")
        type_ = element.existing_type
    return "%s CHANGE %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        element.column_name,
        _mysql_colspec(
            compiler,
            name=name,
            nullable=nullable,
            server_default=server_default,
            type_=type_
        ),
    )

def _mysql_colspec(compiler, name, nullable, server_default, type_):
    spec = "%s %s %s" % (
        name,
        compiler.dialect.type_compiler.process(type_),
        "NULL" if nullable else "NOT NULL"
    )
    if server_default:
        spec += " DEFAULT '%s'" % server_default

    return spec


