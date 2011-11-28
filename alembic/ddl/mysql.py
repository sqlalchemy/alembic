from alembic.ddl.impl import DefaultImpl
from alembic.ddl.base import ColumnNullable, ColumnName, ColumnDefault, ColumnType, AlterColumn
from sqlalchemy.ext.compiler import compiles
from alembic.ddl.base import alter_table
from alembic import util
from sqlalchemy import types as sqltypes

class MySQLImpl(DefaultImpl):
    __dialect__ = 'mysql'

    def alter_column(self, table_name, column_name, 
                        nullable=None,
                        server_default=False,
                        name=None,
                        type_=None,
                        schema=None,
                        existing_type=None,
                        existing_server_default=None,
                        existing_nullable=None
                    ):
        self._exec(
            MySQLAlterColumn(
                table_name, column_name,
                schema=schema,
                newname=name if name is not None else column_name,
                nullable =nullable if nullable is not None else 
                                existing_nullable if existing_nullable is not None
                                else True,
                type_=type_ if type_ is not None else existing_type,
                default=server_default if server_default is not False else existing_server_default,
            )
        )

class MySQLAlterColumn(AlterColumn):
    def __init__(self, name, column_name, schema=None,
                        newname=None,
                        type_=None,
                        nullable=None,
                        default=False):
        super(AlterColumn, self).__init__(name, schema=schema)
        self.column_name = column_name
        self.nullable = nullable
        self.newname = newname
        self.default = default
        if type_ is None:
            raise util.CommandError(
                "All MySQL ALTER COLUMN operations "
                "require the existing type."
            )

        self.type_ = sqltypes.to_instance(type_)

@compiles(ColumnNullable, 'mysql')
@compiles(ColumnName, 'mysql')
@compiles(ColumnDefault, 'mysql')
@compiles(ColumnType, 'mysql')
def _mysql_doesnt_support_individual(element, compiler, **kw):
    raise NotImplementedError(
            "Individual alter column constructs not supported by MySQL"
        )


@compiles(MySQLAlterColumn, "mysql")
def _mysql_alter_column(element, compiler, **kw):
    return "%s CHANGE %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        element.column_name,
        _mysql_colspec(
            compiler,
            name=element.newname,
            nullable=element.nullable,
            server_default=element.default,
            type_=element.type_
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


