from alembic.ddl.impl import DefaultImpl
from alembic.ddl.base import alter_table, AddColumn, ColumnName, format_table_name, format_column_name, ColumnNullable, alter_column
from sqlalchemy.ext.compiler import compiles

class MSSQLImpl(DefaultImpl):
    __dialect__ = 'mssql'
    transactional_ddl = True

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
                _exec_drop_col_constraint(table_name, column, 'sys.default_constraints')
            )
        drop_check = kw.pop('mssql_drop_check', False)
        if drop_check:
            self._exec(
                _exec_drop_col_constraint(table_name, column, 'sys.check_constraints')
            )
        super(MSSQLImpl, self).drop_column(table_name, column)


def _exec_drop_col_constraint(tname, colname, type_):
    # from http://www.mssqltips.com/sqlservertip/1425/working-with-default-constraints-in-sql-server/
    # TODO: needs table formatting, etc.
    return """declare @const_name varchar(256)
select @const_name = [name] from %(type)s
where parent_object_id = object_id('%(tname)s')
and col_name(parent_object_id, parent_column_id) = '%(colname)s'
exec('alter table %(tname)s drop constraint ' + @const_name)""" % {
        'type':type_,
        'tname':tname,
        'colname':colname
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
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "NULL" if element.nullable else "SET NOT NULL"
    )


@compiles(ColumnName, 'mssql')
def visit_rename_column(element, compiler, **kw):
    return "EXEC sp_rename '%s.%s', '%s', 'COLUMN'" % (
        format_table_name(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        format_column_name(compiler, element.newname)
    )


