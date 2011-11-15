from alembic.ddl.impl import DefaultImpl
from alembic.ddl.base import alter_table, AddColumn
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


@compiles(AddColumn, 'mssql')
def visit_add_column(element, compiler, **kw):
    return "%s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        mysql_add_column(compiler, element.column, **kw)
    )

def mysql_add_column(compiler, column, **kw):
    return "ADD %s" % compiler.get_column_specification(column, **kw)

