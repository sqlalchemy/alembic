from alembic.ddl.impl import DefaultImpl
from sqlalchemy import types as sqltypes
import re

class PostgresqlImpl(DefaultImpl):
    __dialect__ = 'postgresql'
    transactional_ddl = True

    def compare_server_default(self, inspector_column, 
                            metadata_column, 
                            rendered_metadata_default):

        # don't do defaults for SERIAL columns
        if metadata_column.primary_key and \
            metadata_column is metadata_column.table._autoincrement_column:
            return False

        conn_col_default = inspector_column['default']

        if metadata_column.type._type_affinity is not sqltypes.String:
            rendered_metadata_default = re.sub(r"^'|'$", "", rendered_metadata_default)

        return not self.connection.scalar(
            "SELECT %s = %s" % (
                conn_col_default,
                rendered_metadata_default
            )
        )
