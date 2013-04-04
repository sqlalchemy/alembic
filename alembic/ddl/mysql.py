from alembic.ddl.impl import DefaultImpl
from alembic.ddl.base import ColumnNullable, ColumnName, ColumnDefault, \
            ColumnType, AlterColumn
from sqlalchemy.ext.compiler import compiles
from alembic.ddl.base import alter_table
from alembic import util
from sqlalchemy import types as sqltypes
from sqlalchemy import schema

class MySQLImpl(DefaultImpl):
    __dialect__ = 'mysql'

    transactional_ddl = False

    def alter_column(self, table_name, column_name,
                        nullable=None,
                        server_default=False,
                        name=None,
                        type_=None,
                        schema=None,
                        autoincrement=None,
                        existing_type=None,
                        existing_server_default=None,
                        existing_nullable=None,
                        existing_autoincrement=None
                    ):
        self._exec(
            MySQLAlterColumn(
                table_name, column_name,
                schema=schema,
                newname=name if name is not None else column_name,
                nullable=nullable if nullable is not None else
                                existing_nullable
                                if existing_nullable is not None
                                else True,
                type_=type_ if type_ is not None else existing_type,
                default=server_default if server_default is not False
                                            else existing_server_default,
                autoincrement=autoincrement if autoincrement is not None
                                            else existing_autoincrement
            )
        )

class MySQLAlterColumn(AlterColumn):
    def __init__(self, name, column_name, schema=None,
                        newname=None,
                        type_=None,
                        nullable=None,
                        default=False,
                        autoincrement=None):
        super(AlterColumn, self).__init__(name, schema=schema)
        self.column_name = column_name
        self.nullable = nullable
        self.newname = newname
        self.default = default
        self.autoincrement = autoincrement
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
            type_=element.type_,
            autoincrement=element.autoincrement
        ),
    )

def _render_value(compiler, expr):
    if isinstance(expr, basestring):
        return "'%s'" % expr
    else:
        return compiler.sql_compiler.process(expr)

def _mysql_colspec(compiler, name, nullable, server_default, type_,
                                        autoincrement):
    spec = "%s %s %s" % (
        name,
        compiler.dialect.type_compiler.process(type_),
        "NULL" if nullable else "NOT NULL"
    )
    if autoincrement:
        spec += " AUTO_INCREMENT"
    if server_default != False:
        spec += " DEFAULT %s" % _render_value(compiler, server_default)

    return spec

@compiles(schema.DropConstraint, "mysql")
def _mysql_drop_constraint(element, compiler, **kw):
    """Redefine SQLAlchemy's drop constraint to
    raise errors for invalid constraint type."""

    constraint = element.element
    if isinstance(constraint, (schema.ForeignKeyConstraint,
                                schema.PrimaryKeyConstraint,
                                schema.UniqueConstraint)
                                ):
        return compiler.visit_drop_constraint(element, **kw)
    elif isinstance(constraint, schema.CheckConstraint):
        raise NotImplementedError(
                "MySQL does not support CHECK constraints.")
    else:
        raise NotImplementedError(
                "No generic 'DROP CONSTRAINT' in MySQL - "
                "please specify constraint type")

