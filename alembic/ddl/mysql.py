from sqlalchemy.ext.compiler import compiles
from sqlalchemy import types as sqltypes
from sqlalchemy import schema

from ..compat import string_types
from .. import util
from .impl import DefaultImpl
from .base import ColumnNullable, ColumnName, ColumnDefault, \
            ColumnType, AlterColumn, format_column_name, \
            format_server_default
from .base import alter_table

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
        if name is not None:
            self._exec(
                MySQLChangeColumn(
                    table_name, column_name,
                    schema=schema,
                    newname=name,
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
        elif nullable is not None or \
            type_ is not None or \
            autoincrement is not None:
            self._exec(
                MySQLModifyColumn(
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
        elif server_default is not False:
            self._exec(
                MySQLAlterDefault(
                    table_name, column_name, server_default,
                    schema=schema,
                )
            )

    def correct_for_autogen_constraints(self, conn_unique_constraints,
                                        conn_indexes,
                                        metadata_unique_constraints,
                                        metadata_indexes):
        removed = set()
        for idx in list(conn_indexes):
            # MySQL puts implicit indexes on FK columns, even if
            # composite and even if MyISAM, so can't check this too easily
            if idx.name == idx.columns.keys()[0]:
                conn_indexes.remove(idx)
                removed.add(idx.name)

        # then remove indexes from the "metadata_indexes"
        # that we've removed from reflected, otherwise they come out
        # as adds (see #202)
        for idx in list(metadata_indexes):
            if idx.name in removed:
                metadata_indexes.remove(idx)

class MySQLAlterDefault(AlterColumn):
    def __init__(self, name, column_name, default, schema=None):
        super(AlterColumn, self).__init__(name, schema=schema)
        self.column_name = column_name
        self.default = default


class MySQLChangeColumn(AlterColumn):
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
                "All MySQL CHANGE/MODIFY COLUMN operations "
                "require the existing type."
            )

        self.type_ = sqltypes.to_instance(type_)

class MySQLModifyColumn(MySQLChangeColumn):
    pass


@compiles(ColumnNullable, 'mysql')
@compiles(ColumnName, 'mysql')
@compiles(ColumnDefault, 'mysql')
@compiles(ColumnType, 'mysql')
def _mysql_doesnt_support_individual(element, compiler, **kw):
    raise NotImplementedError(
            "Individual alter column constructs not supported by MySQL"
        )


@compiles(MySQLAlterDefault, "mysql")
def _mysql_alter_default(element, compiler, **kw):
    return "%s ALTER COLUMN %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        "SET DEFAULT %s" % format_server_default(compiler, element.default)
             if element.default is not None
            else "DROP DEFAULT"
    )

@compiles(MySQLModifyColumn, "mysql")
def _mysql_modify_column(element, compiler, **kw):
    return "%s MODIFY %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        _mysql_colspec(
            compiler,
            nullable=element.nullable,
            server_default=element.default,
            type_=element.type_,
            autoincrement=element.autoincrement
        ),
    )


@compiles(MySQLChangeColumn, "mysql")
def _mysql_change_column(element, compiler, **kw):
    return "%s CHANGE %s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        format_column_name(compiler, element.newname),
        _mysql_colspec(
            compiler,
            nullable=element.nullable,
            server_default=element.default,
            type_=element.type_,
            autoincrement=element.autoincrement
        ),
    )

def _render_value(compiler, expr):
    if isinstance(expr, string_types):
        return "'%s'" % expr
    else:
        return compiler.sql_compiler.process(expr)

def _mysql_colspec(compiler, nullable, server_default, type_,
                                        autoincrement):
    spec = "%s %s" % (
        compiler.dialect.type_compiler.process(type_),
        "NULL" if nullable else "NOT NULL"
    )
    if autoincrement:
        spec += " AUTO_INCREMENT"
    if server_default is not False and server_default is not None:
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

