from __future__ import annotations

from typing import Any
from typing import Optional
from typing import TYPE_CHECKING
from typing import Union

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import sqltypes

from .base import AddColumn
from .base import alter_table
from .base import ColumnComment
from .base import ColumnDefault
from .base import ColumnName
from .base import ColumnNullable
from .base import ColumnType
from .base import format_column_name
from .base import format_server_default
from .base import format_table_name
from .base import format_type
from .base import IdentityColumnDefault
from .base import RenameTable
from .impl import DefaultImpl

if TYPE_CHECKING:
    from sqlalchemy.dialects.oracle.base import OracleDDLCompiler
    from sqlalchemy.engine.cursor import CursorResult
    from sqlalchemy.engine.cursor import LegacyCursorResult
    from sqlalchemy.sql.schema import Column


class OracleImpl(DefaultImpl):
    __dialect__ = "oracle"
    transactional_ddl = False
    batch_separator = "/"
    command_terminator = ""
    type_synonyms = DefaultImpl.type_synonyms + (
        {"VARCHAR", "VARCHAR2"},
        {"BIGINT", "INTEGER", "SMALLINT", "DECIMAL", "NUMERIC", "NUMBER"},
        {"DOUBLE", "FLOAT", "DOUBLE_PRECISION"},
    )
    identity_attrs_ignore = ()

    def __init__(self, *arg, **kw) -> None:
        super(OracleImpl, self).__init__(*arg, **kw)
        self.batch_separator = self.context_opts.get(
            "oracle_batch_separator", self.batch_separator
        )

    def _exec(
        self, construct: Any, *args, **kw
    ) -> Optional[Union["LegacyCursorResult", "CursorResult"]]:
        result = super(OracleImpl, self)._exec(construct, *args, **kw)
        if self.as_sql and self.batch_separator:
            self.static_output(self.batch_separator)
        return result

    def emit_begin(self) -> None:
        self._exec("SET TRANSACTION READ WRITE")

    def emit_commit(self) -> None:
        self._exec("COMMIT")


@compiles(AddColumn, "oracle")
def visit_add_column(
    element: "AddColumn", compiler: "OracleDDLCompiler", **kw
) -> str:
    return "%s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        add_column(compiler, element.column, **kw),
    )


@compiles(ColumnNullable, "oracle")
def visit_column_nullable(
    element: "ColumnNullable", compiler: "OracleDDLCompiler", **kw
) -> str:
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "NULL" if element.nullable else "NOT NULL",
    )


@compiles(ColumnType, "oracle")
def visit_column_type(
    element: "ColumnType", compiler: "OracleDDLCompiler", **kw
) -> str:
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "%s" % format_type(compiler, element.type_),
    )


@compiles(ColumnName, "oracle")
def visit_column_name(
    element: "ColumnName", compiler: "OracleDDLCompiler", **kw
) -> str:
    return "%s RENAME COLUMN %s TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_column_name(compiler, element.column_name),
        format_column_name(compiler, element.newname),
    )


@compiles(ColumnDefault, "oracle")
def visit_column_default(
    element: "ColumnDefault", compiler: "OracleDDLCompiler", **kw
) -> str:
    return "%s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "DEFAULT %s" % format_server_default(compiler, element.default)
        if element.default is not None
        else "DEFAULT NULL",
    )


@compiles(ColumnComment, "oracle")
def visit_column_comment(
    element: "ColumnComment", compiler: "OracleDDLCompiler", **kw
) -> str:
    ddl = "COMMENT ON COLUMN {table_name}.{column_name} IS {comment}"

    comment = compiler.sql_compiler.render_literal_value(
        (element.comment if element.comment is not None else ""),
        sqltypes.String(),
    )

    return ddl.format(
        table_name=element.table_name,
        column_name=element.column_name,
        comment=comment,
    )


@compiles(RenameTable, "oracle")
def visit_rename_table(
    element: "RenameTable", compiler: "OracleDDLCompiler", **kw
) -> str:
    return "%s RENAME TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_table_name(compiler, element.new_table_name, None),
    )


def alter_column(compiler: "OracleDDLCompiler", name: str) -> str:
    return "MODIFY %s" % format_column_name(compiler, name)


def add_column(compiler: "OracleDDLCompiler", column: "Column", **kw) -> str:
    return "ADD %s" % compiler.get_column_specification(column, **kw)


@compiles(IdentityColumnDefault, "oracle")
def visit_identity_column(
    element: "IdentityColumnDefault", compiler: "OracleDDLCompiler", **kw
):
    text = "%s %s " % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
    )
    if element.default is None:
        # drop identity
        text += "DROP IDENTITY"
        return text
    else:
        text += compiler.visit_identity_column(element.default)
        return text
