import re

from ..util import compat
from .. import util
from .base import compiles, alter_table, format_table_name, RenameTable
from .impl import DefaultImpl
from sqlalchemy.dialects.postgresql import INTEGER, BIGINT
from sqlalchemy import text, Numeric, Column

if compat.sqla_08:
    from sqlalchemy.sql.expression import UnaryExpression
else:
    from sqlalchemy.sql.expression import _UnaryExpression as UnaryExpression

import logging

log = logging.getLogger(__name__)


class PostgresqlImpl(DefaultImpl):
    __dialect__ = 'postgresql'
    transactional_ddl = True

    def prep_table_for_batch(self, table):
        for constraint in table.constraints:
            if constraint.name is not None:
                self.drop_constraint(constraint)

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
                not re.match(r"^'.+'$", rendered_metadata_default) and \
                not isinstance(inspector_column.type, Numeric):
                # don't single quote if the column type is float/numeric,
                # otherwise a comparison such as SELECT 5 = '5.0' will fail
            rendered_metadata_default = re.sub(
                r"^u?'?|'?$", "'", rendered_metadata_default)

        return not self.connection.scalar(
            "SELECT %s = %s" % (
                conn_col_default,
                rendered_metadata_default
            )
        )

    def autogen_column_reflect(self, inspector, table, column_info):
        if column_info.get('default') and \
                isinstance(column_info['type'], (INTEGER, BIGINT)):
            seq_match = re.match(
                r"nextval\('(.+?)'::regclass\)",
                column_info['default'])
            if seq_match:
                info = inspector.bind.execute(text(
                    "select c.relname, a.attname "
                    "from pg_class as c join pg_depend d on d.objid=c.oid and "
                    "d.classid='pg_class'::regclass and "
                    "d.refclassid='pg_class'::regclass "
                    "join pg_class t on t.oid=d.refobjid "
                    "join pg_attribute a on a.attrelid=t.oid and "
                    "a.attnum=d.refobjsubid "
                    "where c.relkind='S' and c.relname=:seqname"
                ), seqname=seq_match.group(1)).first()
                if info:
                    seqname, colname = info
                    if colname == column_info['name']:
                        log.info(
                            "Detected sequence named '%s' as "
                            "owned by integer column '%s(%s)', "
                            "assuming SERIAL and omitting" % (
                                seqname, table.name, colname
                            ))
                        # sequence, and the owner is this column,
                        # its a SERIAL - whack it!
                        del column_info['default']

    def correct_for_autogen_constraints(self, conn_unique_constraints,
                                        conn_indexes,
                                        metadata_unique_constraints,
                                        metadata_indexes):
        conn_uniques_by_name = dict(
            (c.name, c) for c in conn_unique_constraints)
        conn_indexes_by_name = dict(
            (c.name, c) for c in conn_indexes)

        # TODO: if SQLA 1.0, make use of "duplicates_constraint"
        # metadata
        doubled_constraints = dict(
            (name, (conn_uniques_by_name[name], conn_indexes_by_name[name]))
            for name in set(conn_uniques_by_name).intersection(
                conn_indexes_by_name)
        )
        for name, (uq, ix) in doubled_constraints.items():
            conn_indexes.remove(ix)

        for idx in list(metadata_indexes):
            if idx.name in conn_indexes_by_name:
                continue
            if compat.sqla_08:
                exprs = idx.expressions
            else:
                exprs = idx.columns
            for expr in exprs:
                if not isinstance(expr, (Column, UnaryExpression)):
                    util.warn(
                        "autogenerate skipping functional index %s; "
                        "not supported by SQLAlchemy reflection" % idx.name
                    )
                    metadata_indexes.discard(idx)


@compiles(RenameTable, "postgresql")
def visit_rename_table(element, compiler, **kw):
    return "%s RENAME TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_table_name(compiler, element.new_table_name, None)
    )
