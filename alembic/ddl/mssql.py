from alembic.ddl.impl import DefaultImpl
from alembic.ddl.base import alter_table, AddColumn, ColumnName, \
    format_table_name, format_column_name, ColumnNullable, alter_column
from alembic import util
from sqlalchemy.ext.compiler import compiles

class MSSQLImpl(DefaultImpl):
    __dialect__ = 'mssql'
    transactional_ddl = True
    batch_separator = "GO"

    def __init__(self, *arg, **kw):
        super(MSSQLImpl, self).__init__(*arg, **kw)
        self.batch_separator = self.context_opts.get(
                                "mssql_batch_separator", 
                                self.batch_separator)

    def start_migrations(self):
        self.__dict__.pop('const_sym_counter', None)

    @util.memoized_property
    def const_sym_counter(self):
        return 1

    def _exec(self, construct, *args, **kw):
        super(MSSQLImpl, self)._exec(construct, *args, **kw)
        if self.as_sql and self.batch_separator:
            self.static_output(self.batch_separator)

    def emit_begin(self):
        self._exec("BEGIN TRANSACTION")

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

        if nullable is not None and existing_type is None:
            if type_ is not None:
                existing_type = type_
                # the NULL/NOT NULL alter will handle
                # the type alteration
                type_ = None
            else:
                raise util.CommandError(
                        "MS-SQL ALTER COLUMN operations "
                        "with NULL or NOT NULL require the "
                        "existing_type or a new type_ be passed.")

        super(MSSQLImpl, self).alter_column(
                        table_name, column_name, 
                        nullable=nullable,
                        server_default=server_default,
                        name=name,
                        type_=type_,
                        schema=schema,
                        existing_type=existing_type,
                        existing_server_default=existing_server_default,
                        existing_nullable=existing_nullable
        )

    def bulk_insert(self, table, rows):
        if self.as_sql:
            self._exec(
                "SET IDENTITY_INSERT %s ON" % 
                    self.dialect.identifier_preparer.format_table(table)
            )
            super(MSSQLImpl, self).bulk_insert(table, rows)
            self._exec(
                "SET IDENTITY_INSERT %s OFF" % 
                    self.dialect.identifier_preparer.format_table(table)
            )
        else:
            super(MSSQLImpl, self).bulk_insert(table, rows)


    def drop_column(self, table_name, column, **kw):
        drop_default = kw.pop('mssql_drop_default', False)
        if drop_default:
            self._exec(
                _exec_drop_col_constraint(self, 
                        table_name, column, 
                        'sys.default_constraints')
            )
        drop_check = kw.pop('mssql_drop_check', False)
        if drop_check:
            self._exec(
                _exec_drop_col_constraint(self, 
                        table_name, column, 
                        'sys.check_constraints')
            )
        super(MSSQLImpl, self).drop_column(table_name, column)

def _exec_drop_col_constraint(impl, tname, colname, type_):
    # from http://www.mssqltips.com/sqlservertip/1425/working-with-default-constraints-in-sql-server/
    # TODO: needs table formatting, etc.
    counter = impl.const_sym_counter
    impl.const_sym_counter += 1

    return """declare @const_name_%(sym)s varchar(256)
select @const_name_%(sym)s = [name] from %(type)s
where parent_object_id = object_id('%(tname)s')
and col_name(parent_object_id, parent_column_id) = '%(colname)s'
exec('alter table %(tname)s drop constraint ' + @const_name_%(sym)s)""" % {
        'type':type_,
        'tname':tname,
        'colname':colname,
        'sym':counter
    }

@compiles(AddColumn, 'mssql')
def visit_add_column(element, compiler, **kw):
    return "%s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        mssql_add_column(compiler, element.column, **kw)
    )

def mssql_add_column(compiler, column, **kw):
    return "ADD %s" % compiler.get_column_specification(column, **kw)

@compiles(ColumnNullable, 'mssql')
def visit_column_nullable(element, compiler, **kw):
    return "%s %s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        compiler.dialect.type_compiler.process(element.existing_type),
        "NULL" if element.nullable else "NOT NULL"
    )


@compiles(ColumnName, 'mssql')
def visit_rename_column(element, compiler, **kw):
    return "EXEC sp_rename '%s.%s', '%s', 'COLUMN'" % (
        format_table_name(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        format_column_name(compiler, element.newname)
    )


