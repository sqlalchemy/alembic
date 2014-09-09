import re

from .. import compat
from .base import compiles, alter_table, format_table_name, RenameTable
from .impl import DefaultImpl


class PostgresqlImpl(DefaultImpl):
    __dialect__ = 'postgresql'
    transactional_ddl = True

    def compare_server_default(self, inspector_column,
                               metadata_column,
                               rendered_metadata_default,
                               rendered_inspector_default):

        # don't do defaults for SERIAL columns
        if metadata_column.primary_key and \
                metadata_column is metadata_column.table._autoincrement_column:
            return False

        conn_col_default = rendered_inspector_default

        if None in (conn_col_default, rendered_metadata_default):
            return conn_col_default != rendered_metadata_default

        if metadata_column.server_default is not None and \
            isinstance(metadata_column.server_default.arg,
                       compat.string_types) and \
                not re.match(r"^'.+'$", rendered_metadata_default):
            rendered_metadata_default = "'%s'" % rendered_metadata_default

        return not self.connection.scalar(
            "SELECT %s = %s" % (
                conn_col_default,
                rendered_metadata_default
            )
        )


@compiles(RenameTable, "postgresql")
def visit_rename_table(element, compiler, **kw):
    return "%s RENAME TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_table_name(compiler, element.new_table_name, None)
    )
