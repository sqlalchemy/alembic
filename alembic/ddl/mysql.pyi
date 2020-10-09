from sqlalchemy.dialects.mysql.base import MySQLDDLCompiler
from sqlalchemy.sql.ddl import DropConstraint
from sqlalchemy.sql.elements import TextClause
from sqlalchemy.sql.functions import Function
from sqlalchemy.sql.schema import (
    CheckConstraint,
    Constraint,
    DefaultClause,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.sql.sqltypes import (
    Boolean,
    DATETIME,
    Float,
    Integer,
)
from typing import (
    Optional,
    Type,
    Union,
)

def _mysql_alter_default(
    element: MySQLAlterDefault, compiler: MySQLDDLCompiler, **kw
) -> str: ...
def _mysql_change_column(
    element: MySQLChangeColumn, compiler: MySQLDDLCompiler, **kw
) -> str: ...
def _mysql_colspec(
    compiler: MySQLDDLCompiler,
    nullable: bool,
    server_default: Optional[Union[TextClause, bool, DefaultClause, str]],
    type_: Union[Boolean, DATETIME, Integer, Float],
    autoincrement: Optional[bool],
    comment: Optional[str],
) -> str: ...
def _mysql_drop_constraint(
    element: DropConstraint, compiler: MySQLDDLCompiler, **kw
) -> str: ...
def _mysql_modify_column(
    element: MySQLModifyColumn, compiler: MySQLDDLCompiler, **kw
) -> str: ...

class MySQLAlterDefault:
    def __init__(
        self,
        name: str,
        column_name: str,
        default: Optional[Union[str, Function]],
        schema: None = ...,
    ) -> None: ...

class MySQLChangeColumn:
    def __init__(
        self,
        name: str,
        column_name: str,
        schema: Optional[str] = ...,
        newname: Optional[str] = ...,
        type_: Optional[Union[Boolean, Type[Integer], DATETIME, Float]] = ...,
        nullable: Optional[bool] = ...,
        default: Optional[Union[TextClause, bool, DefaultClause, str]] = ...,
        autoincrement: Optional[bool] = ...,
        comment: Optional[str] = ...,
    ) -> None: ...

class MySQLImpl:
    def _is_mysql_allowed_functional_default(
        self,
        type_: Optional[Union[Boolean, Type[Integer], DATETIME, Float]],
        server_default: Optional[Union[TextClause, Function, bool, str]],
    ) -> bool: ...
    def alter_column(
        self,
        table_name: str,
        column_name: str,
        nullable: Optional[bool] = ...,
        server_default: Optional[Union[TextClause, Function, bool, str]] = ...,
        name: Optional[str] = ...,
        type_: Optional[Type[Integer]] = ...,
        schema: Optional[str] = ...,
        existing_type: Optional[
            Union[Boolean, Type[Integer], DATETIME, Float]
        ] = ...,
        existing_server_default: Optional[
            Union[DefaultClause, str, bool]
        ] = ...,
        existing_nullable: Optional[bool] = ...,
        autoincrement: Optional[bool] = ...,
        existing_autoincrement: Optional[bool] = ...,
        comment: Optional[Union[str, bool]] = ...,
        existing_comment: Optional[str] = ...,
        **kw
    ) -> None: ...
    def drop_constraint(
        self,
        const: Union[
            Constraint,
            UniqueConstraint,
            ForeignKeyConstraint,
            PrimaryKeyConstraint,
            CheckConstraint,
        ],
    ) -> None: ...
