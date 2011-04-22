from alembic.context import DefaultContext

class MSSQLContext(DefaultContext):
    __dialect__ = 'mssql'
    transactional_ddl = True

    def bulk_insert(self, table, rows):
        if self.as_sql:
            self._exec(
                "SET IDENTITY_INSERT %s ON" % 
                    self.dialect.identifier_preparer.format_table(table)
            )
            super(MSSQLContext, self).bulk_insert(table, rows)
            self._exec(
                "SET IDENTITY_INSERT %s OFF" % 
                    self.dialect.identifier_preparer.format_table(table)
            )
        else:
            super(MSSQLContext, self).bulk_insert(table, rows)