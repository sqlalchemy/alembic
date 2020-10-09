from alembic.ddl.base import (
    AddColumn,
    ColumnDefault,
    ColumnName,
    ColumnNullable,
    ColumnType,
    RenameTable,
)
from sqlalchemy.dialects.mssql.base import (
    MSDDLCompiler,
    MSSQLCompiler,
)
from sqlalchemy.sql.schema import (
    Column,
    Index,
)
from sqlalchemy.sql.selectable import TableClause
from sqlalchemy.sql.sqltypes import (
    Boolean,
    Integer,
    String,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
)


def _exec_drop_col_constraint(
    element: _ExecDropConstraint,
    compiler: MSSQLCompiler,
    **kw
) -> str: ...


def _exec_drop_col_fk_constraint(
    element: _ExecDropFKConstraint,
    compiler: MSSQLCompiler,
    **kw
) -> str: ...


def mssql_add_column(
    compiler: MSDDLCompiler,
    column: Column,
    **kw
) -> str: ...


def visit_add_column(
    element: AddColumn,
    compiler: MSDDLCompiler,
    **kw
) -> str: ...


def visit_column_default(
    element: ColumnDefault,
    compiler: MSDDLCompiler,
    **kw
) -> str: ...


def visit_column_nullable(
    element: ColumnNullable,
    compiler: MSDDLCompiler,
    **kw
) -> str: ...


def visit_column_type(
    element: ColumnType,
    compiler: MSDDLCompiler,
    **kw
) -> str: ...


def visit_rename_column(
    element: ColumnName,
    compiler: MSDDLCompiler,
    **kw
) -> str: ...


def visit_rename_table(
    element: RenameTable,
    compiler: MSDDLCompiler,
    **kw
) -> str: ...


class MSSQLImpl:
    def __init__(self, *arg, **kw) -> None: ...
    def _exec(self, construct: Any, *args, **kw) -> None: ...
    def alter_column(
        self,
        table_name: str,
        column_name: str,
        nullable: Optional[bool] = ...,
        server_default: Optional[Union[str, bool]] = ...,
        name: Optional[str] = ...,
        type_: Optional[Union[Type[Integer], String, Boolean]] = ...,
        schema: Optional[str] = ...,
        existing_type: Optional[Union[Type[Integer], Boolean]] = ...,
        existing_server_default: Optional[Union[str, bool]] = ...,
        existing_nullable: None = ...,
        **kw
    ) -> None: ...
    def bulk_insert(
        self,
        table: TableClause,
        rows: List[Dict[str, Union[int, str]]],
        **kw
    ) -> None: ...
    def create_index(self, index: Index) -> None: ...
    def drop_column(
        self,
        table_name: str,
        column: Column,
        schema: Optional[str] = ...,
        **kw
    ) -> None: ...
    def emit_begin(self) -> None: ...
    def emit_commit(self) -> None: ...


class _ExecDropConstraint:
    def __init__(
        self,
        tname: str,
        colname: Union[Column, str],
        type_: str,
        schema: Optional[str]
    ) -> None: ...


class _ExecDropFKConstraint:
    def __init__(self, tname: str, colname: Column, schema: Optional[str]) -> None: ...
