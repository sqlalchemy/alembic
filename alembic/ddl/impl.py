from __future__ import annotations

from collections import namedtuple
import re
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Set
from typing import Tuple
from typing import Type
from typing import TYPE_CHECKING
from typing import Union

from sqlalchemy import cast
from sqlalchemy import schema
from sqlalchemy import text

from . import base
from .. import util
from ..util import sqla_compat

if TYPE_CHECKING:
    from io import StringIO
    from typing import Literal

    from sqlalchemy.engine import Connection
    from sqlalchemy.engine import Dialect
    from sqlalchemy.engine.cursor import CursorResult
    from sqlalchemy.engine.cursor import LegacyCursorResult
    from sqlalchemy.engine.reflection import Inspector
    from sqlalchemy.sql.dml import Update
    from sqlalchemy.sql.elements import ClauseElement
    from sqlalchemy.sql.elements import ColumnElement
    from sqlalchemy.sql.elements import quoted_name
    from sqlalchemy.sql.elements import TextClause
    from sqlalchemy.sql.schema import Column
    from sqlalchemy.sql.schema import Constraint
    from sqlalchemy.sql.schema import ForeignKeyConstraint
    from sqlalchemy.sql.schema import Index
    from sqlalchemy.sql.schema import Table
    from sqlalchemy.sql.schema import UniqueConstraint
    from sqlalchemy.sql.selectable import TableClause
    from sqlalchemy.sql.type_api import TypeEngine

    from .base import _ServerDefault
    from ..autogenerate.api import AutogenContext
    from ..operations.batch import ApplyBatchImpl
    from ..operations.batch import BatchOperationsImpl


class ImplMeta(type):
    def __init__(
        cls,
        classname: str,
        bases: Tuple[Type["DefaultImpl"]],
        dict_: Dict[str, Any],
    ):
        newtype = type.__init__(cls, classname, bases, dict_)
        if "__dialect__" in dict_:
            _impls[dict_["__dialect__"]] = cls
        return newtype


_impls: dict = {}

Params = namedtuple("Params", ["token0", "tokens", "args", "kwargs"])


class DefaultImpl(metaclass=ImplMeta):

    """Provide the entrypoint for major migration operations,
    including database-specific behavioral variances.

    While individual SQL/DDL constructs already provide
    for database-specific implementations, variances here
    allow for entirely different sequences of operations
    to take place for a particular migration, such as
    SQL Server's special 'IDENTITY INSERT' step for
    bulk inserts.

    """

    __dialect__ = "default"

    transactional_ddl = False
    command_terminator = ";"
    type_synonyms: Tuple[Set[str], ...] = ({"NUMERIC", "DECIMAL"},)
    type_arg_extract: Sequence[str] = ()
    # on_null is known to be supported only by oracle
    identity_attrs_ignore: Tuple[str, ...] = ("on_null",)

    def __init__(
        self,
        dialect: "Dialect",
        connection: Optional["Connection"],
        as_sql: bool,
        transactional_ddl: Optional[bool],
        output_buffer: Optional["StringIO"],
        context_opts: Dict[str, Any],
    ) -> None:
        self.dialect = dialect
        self.connection = connection
        self.as_sql = as_sql
        self.literal_binds = context_opts.get("literal_binds", False)

        self.output_buffer = output_buffer
        self.memo: dict = {}
        self.context_opts = context_opts
        if transactional_ddl is not None:
            self.transactional_ddl = transactional_ddl

        if self.literal_binds:
            if not self.as_sql:
                raise util.CommandError(
                    "Can't use literal_binds setting without as_sql mode"
                )

    @classmethod
    def get_by_dialect(cls, dialect: "Dialect") -> Any:
        return _impls[dialect.name]

    def static_output(self, text: str) -> None:
        assert self.output_buffer is not None
        self.output_buffer.write(text + "\n\n")
        self.output_buffer.flush()

    def requires_recreate_in_batch(
        self, batch_op: "BatchOperationsImpl"
    ) -> bool:
        """Return True if the given :class:`.BatchOperationsImpl`
        would need the table to be recreated and copied in order to
        proceed.

        Normally, only returns True on SQLite when operations other
        than add_column are present.

        """
        return False

    def prep_table_for_batch(
        self, batch_impl: "ApplyBatchImpl", table: "Table"
    ) -> None:
        """perform any operations needed on a table before a new
        one is created to replace it in batch mode.

        the PG dialect uses this to drop constraints on the table
        before the new one uses those same names.

        """

    @property
    def bind(self) -> Optional["Connection"]:
        return self.connection

    def _exec(
        self,
        construct: Union["ClauseElement", str],
        execution_options: None = None,
        multiparams: Sequence[dict] = (),
        params: Dict[str, int] = util.immutabledict(),
    ) -> Optional[Union["LegacyCursorResult", "CursorResult"]]:
        if isinstance(construct, str):
            construct = text(construct)
        if self.as_sql:
            if multiparams or params:
                # TODO: coverage
                raise Exception("Execution arguments not allowed with as_sql")

            if self.literal_binds and not isinstance(
                construct, schema.DDLElement
            ):
                compile_kw = dict(compile_kwargs={"literal_binds": True})
            else:
                compile_kw = {}

            self.static_output(
                str(construct.compile(dialect=self.dialect, **compile_kw))
                .replace("\t", "    ")
                .strip()
                + self.command_terminator
            )
            return None
        else:
            conn = self.connection
            assert conn is not None
            if execution_options:
                conn = conn.execution_options(**execution_options)
            if params:
                assert isinstance(multiparams, tuple)
                multiparams += (params,)

            return conn.execute(construct, multiparams)

    def execute(
        self,
        sql: Union["Update", "TextClause", str],
        execution_options: None = None,
    ) -> None:
        self._exec(sql, execution_options)

    def alter_column(
        self,
        table_name: str,
        column_name: str,
        nullable: Optional[bool] = None,
        server_default: Union["_ServerDefault", "Literal[False]"] = False,
        name: Optional[str] = None,
        type_: Optional["TypeEngine"] = None,
        schema: Optional[str] = None,
        autoincrement: Optional[bool] = None,
        comment: Optional[Union[str, "Literal[False]"]] = False,
        existing_comment: Optional[str] = None,
        existing_type: Optional["TypeEngine"] = None,
        existing_server_default: Optional["_ServerDefault"] = None,
        existing_nullable: Optional[bool] = None,
        existing_autoincrement: Optional[bool] = None,
        **kw: Any,
    ) -> None:
        if autoincrement is not None or existing_autoincrement is not None:
            util.warn(
                "autoincrement and existing_autoincrement "
                "only make sense for MySQL",
                stacklevel=3,
            )
        if nullable is not None:
            self._exec(
                base.ColumnNullable(
                    table_name,
                    column_name,
                    nullable,
                    schema=schema,
                    existing_type=existing_type,
                    existing_server_default=existing_server_default,
                    existing_nullable=existing_nullable,
                    existing_comment=existing_comment,
                )
            )
        if server_default is not False:
            kw = {}
            cls_: Type[
                Union[
                    base.ComputedColumnDefault,
                    base.IdentityColumnDefault,
                    base.ColumnDefault,
                ]
            ]
            if sqla_compat._server_default_is_computed(
                server_default, existing_server_default
            ):
                cls_ = base.ComputedColumnDefault
            elif sqla_compat._server_default_is_identity(
                server_default, existing_server_default
            ):
                cls_ = base.IdentityColumnDefault
                kw["impl"] = self
            else:
                cls_ = base.ColumnDefault
            self._exec(
                cls_(
                    table_name,
                    column_name,
                    server_default,  # type:ignore[arg-type]
                    schema=schema,
                    existing_type=existing_type,
                    existing_server_default=existing_server_default,
                    existing_nullable=existing_nullable,
                    existing_comment=existing_comment,
                    **kw,
                )
            )
        if type_ is not None:
            self._exec(
                base.ColumnType(
                    table_name,
                    column_name,
                    type_,
                    schema=schema,
                    existing_type=existing_type,
                    existing_server_default=existing_server_default,
                    existing_nullable=existing_nullable,
                    existing_comment=existing_comment,
                )
            )

        if comment is not False:
            self._exec(
                base.ColumnComment(
                    table_name,
                    column_name,
                    comment,
                    schema=schema,
                    existing_type=existing_type,
                    existing_server_default=existing_server_default,
                    existing_nullable=existing_nullable,
                    existing_comment=existing_comment,
                )
            )

        # do the new name last ;)
        if name is not None:
            self._exec(
                base.ColumnName(
                    table_name,
                    column_name,
                    name,
                    schema=schema,
                    existing_type=existing_type,
                    existing_server_default=existing_server_default,
                    existing_nullable=existing_nullable,
                )
            )

    def add_column(
        self,
        table_name: str,
        column: "Column",
        schema: Optional[Union[str, "quoted_name"]] = None,
    ) -> None:
        self._exec(base.AddColumn(table_name, column, schema=schema))

    def drop_column(
        self,
        table_name: str,
        column: "Column",
        schema: Optional[str] = None,
        **kw,
    ) -> None:
        self._exec(base.DropColumn(table_name, column, schema=schema))

    def add_constraint(self, const: Any) -> None:
        if const._create_rule is None or const._create_rule(self):
            self._exec(schema.AddConstraint(const))

    def drop_constraint(self, const: "Constraint") -> None:
        self._exec(schema.DropConstraint(const))

    def rename_table(
        self,
        old_table_name: str,
        new_table_name: Union[str, "quoted_name"],
        schema: Optional[Union[str, "quoted_name"]] = None,
    ) -> None:
        self._exec(
            base.RenameTable(old_table_name, new_table_name, schema=schema)
        )

    def create_table(self, table: "Table") -> None:
        table.dispatch.before_create(
            table, self.connection, checkfirst=False, _ddl_runner=self
        )
        self._exec(schema.CreateTable(table))
        table.dispatch.after_create(
            table, self.connection, checkfirst=False, _ddl_runner=self
        )
        for index in table.indexes:
            self._exec(schema.CreateIndex(index))

        with_comment = (
            self.dialect.supports_comments and not self.dialect.inline_comments
        )
        comment = table.comment
        if comment and with_comment:
            self.create_table_comment(table)

        for column in table.columns:
            comment = column.comment
            if comment and with_comment:
                self.create_column_comment(column)

    def drop_table(self, table: "Table") -> None:
        table.dispatch.before_drop(
            table, self.connection, checkfirst=False, _ddl_runner=self
        )
        self._exec(schema.DropTable(table))
        table.dispatch.after_drop(
            table, self.connection, checkfirst=False, _ddl_runner=self
        )

    def create_index(self, index: "Index") -> None:
        self._exec(schema.CreateIndex(index))

    def create_table_comment(self, table: "Table") -> None:
        self._exec(schema.SetTableComment(table))

    def drop_table_comment(self, table: "Table") -> None:
        self._exec(schema.DropTableComment(table))

    def create_column_comment(self, column: "ColumnElement") -> None:
        self._exec(schema.SetColumnComment(column))

    def drop_index(self, index: "Index") -> None:
        self._exec(schema.DropIndex(index))

    def bulk_insert(
        self,
        table: Union["TableClause", "Table"],
        rows: List[dict],
        multiinsert: bool = True,
    ) -> None:
        if not isinstance(rows, list):
            raise TypeError("List expected")
        elif rows and not isinstance(rows[0], dict):
            raise TypeError("List of dictionaries expected")
        if self.as_sql:
            for row in rows:
                self._exec(
                    sqla_compat._insert_inline(table).values(
                        **dict(
                            (
                                k,
                                sqla_compat._literal_bindparam(
                                    k, v, type_=table.c[k].type
                                )
                                if not isinstance(
                                    v, sqla_compat._literal_bindparam
                                )
                                else v,
                            )
                            for k, v in row.items()
                        )
                    )
                )
        else:
            # work around http://www.sqlalchemy.org/trac/ticket/2461
            if not hasattr(table, "_autoincrement_column"):
                table._autoincrement_column = None
            if rows:
                if multiinsert:
                    self._exec(
                        sqla_compat._insert_inline(table), multiparams=rows
                    )
                else:
                    for row in rows:
                        self._exec(
                            sqla_compat._insert_inline(table).values(**row)
                        )

    def _tokenize_column_type(self, column: "Column") -> Params:
        definition = self.dialect.type_compiler.process(column.type).lower()

        # tokenize the SQLAlchemy-generated version of a type, so that
        # the two can be compared.
        #
        # examples:
        # NUMERIC(10, 5)
        # TIMESTAMP WITH TIMEZONE
        # INTEGER UNSIGNED
        # INTEGER (10) UNSIGNED
        # INTEGER(10) UNSIGNED
        # varchar character set utf8
        #

        tokens = re.findall(r"[\w\-_]+|\(.+?\)", definition)

        term_tokens = []
        paren_term = None

        for token in tokens:
            if re.match(r"^\(.*\)$", token):
                paren_term = token
            else:
                term_tokens.append(token)

        params = Params(term_tokens[0], term_tokens[1:], [], {})

        if paren_term:
            for term in re.findall("[^(),]+", paren_term):
                if "=" in term:
                    key, val = term.split("=")
                    params.kwargs[key.strip()] = val.strip()
                else:
                    params.args.append(term.strip())

        return params

    def _column_types_match(
        self, inspector_params: "Params", metadata_params: "Params"
    ) -> bool:
        if inspector_params.token0 == metadata_params.token0:
            return True

        synonyms = [{t.lower() for t in batch} for batch in self.type_synonyms]
        inspector_all_terms = " ".join(
            [inspector_params.token0] + inspector_params.tokens
        )
        metadata_all_terms = " ".join(
            [metadata_params.token0] + metadata_params.tokens
        )

        for batch in synonyms:
            if {inspector_all_terms, metadata_all_terms}.issubset(batch) or {
                inspector_params.token0,
                metadata_params.token0,
            }.issubset(batch):
                return True
        return False

    def _column_args_match(
        self, inspected_params: "Params", meta_params: "Params"
    ) -> bool:
        """We want to compare column parameters. However, we only want
        to compare parameters that are set. If they both have `collation`,
        we want to make sure they are the same. However, if only one
        specifies it, dont flag it for being less specific
        """

        if (
            len(meta_params.tokens) == len(inspected_params.tokens)
            and meta_params.tokens != inspected_params.tokens
        ):
            return False

        if (
            len(meta_params.args) == len(inspected_params.args)
            and meta_params.args != inspected_params.args
        ):
            return False

        insp = " ".join(inspected_params.tokens).lower()
        meta = " ".join(meta_params.tokens).lower()

        for reg in self.type_arg_extract:
            mi = re.search(reg, insp)
            mm = re.search(reg, meta)

            if mi and mm and mi.group(1) != mm.group(1):
                return False

        return True

    def compare_type(
        self, inspector_column: "Column", metadata_column: "Column"
    ) -> bool:
        """Returns True if there ARE differences between the types of the two
        columns. Takes impl.type_synonyms into account between retrospected
        and metadata types
        """
        inspector_params = self._tokenize_column_type(inspector_column)
        metadata_params = self._tokenize_column_type(metadata_column)

        if not self._column_types_match(inspector_params, metadata_params):
            return True
        if not self._column_args_match(inspector_params, metadata_params):
            return True
        return False

    def compare_server_default(
        self,
        inspector_column,
        metadata_column,
        rendered_metadata_default,
        rendered_inspector_default,
    ):
        return rendered_inspector_default != rendered_metadata_default

    def correct_for_autogen_constraints(
        self,
        conn_uniques: Set["UniqueConstraint"],
        conn_indexes: Set["Index"],
        metadata_unique_constraints: Set["UniqueConstraint"],
        metadata_indexes: Set["Index"],
    ) -> None:
        pass

    def cast_for_batch_migrate(self, existing, existing_transfer, new_type):
        if existing.type._type_affinity is not new_type._type_affinity:
            existing_transfer["expr"] = cast(
                existing_transfer["expr"], new_type
            )

    def render_ddl_sql_expr(
        self, expr: "ClauseElement", is_server_default: bool = False, **kw
    ) -> str:
        """Render a SQL expression that is typically a server default,
        index expression, etc.

        .. versionadded:: 1.0.11

        """

        compile_kw = dict(
            compile_kwargs={"literal_binds": True, "include_table": False}
        )
        return str(expr.compile(dialect=self.dialect, **compile_kw))

    def _compat_autogen_column_reflect(
        self, inspector: "Inspector"
    ) -> Callable:
        return self.autogen_column_reflect

    def correct_for_autogen_foreignkeys(
        self,
        conn_fks: Set["ForeignKeyConstraint"],
        metadata_fks: Set["ForeignKeyConstraint"],
    ) -> None:
        pass

    def autogen_column_reflect(self, inspector, table, column_info):
        """A hook that is attached to the 'column_reflect' event for when
        a Table is reflected from the database during the autogenerate
        process.

        Dialects can elect to modify the information gathered here.

        """

    def start_migrations(self) -> None:
        """A hook called when :meth:`.EnvironmentContext.run_migrations`
        is called.

        Implementations can set up per-migration-run state here.

        """

    def emit_begin(self) -> None:
        """Emit the string ``BEGIN``, or the backend-specific
        equivalent, on the current connection context.

        This is used in offline mode and typically
        via :meth:`.EnvironmentContext.begin_transaction`.

        """
        self.static_output("BEGIN" + self.command_terminator)

    def emit_commit(self) -> None:
        """Emit the string ``COMMIT``, or the backend-specific
        equivalent, on the current connection context.

        This is used in offline mode and typically
        via :meth:`.EnvironmentContext.begin_transaction`.

        """
        self.static_output("COMMIT" + self.command_terminator)

    def render_type(
        self, type_obj: "TypeEngine", autogen_context: "AutogenContext"
    ) -> Union[str, "Literal[False]"]:
        return False

    def _compare_identity_default(self, metadata_identity, inspector_identity):

        # ignored contains the attributes that were not considered
        # because assumed to their default values in the db.
        diff, ignored = _compare_identity_options(
            sqla_compat._identity_attrs,
            metadata_identity,
            inspector_identity,
            sqla_compat.Identity(),
        )

        meta_always = getattr(metadata_identity, "always", None)
        inspector_always = getattr(inspector_identity, "always", None)
        # None and False are the same in this comparison
        if bool(meta_always) != bool(inspector_always):
            diff.add("always")

        diff.difference_update(self.identity_attrs_ignore)

        # returns 3 values:
        return (
            # different identity attributes
            diff,
            # ignored identity attributes
            ignored,
            # if the two identity should be considered different
            bool(diff) or bool(metadata_identity) != bool(inspector_identity),
        )


def _compare_identity_options(
    attributes, metadata_io, inspector_io, default_io
):
    # this can be used for identity or sequence compare.
    # default_io is an instance of IdentityOption with all attributes to the
    # default value.
    diff = set()
    ignored_attr = set()
    for attr in attributes:
        meta_value = getattr(metadata_io, attr, None)
        default_value = getattr(default_io, attr, None)
        conn_value = getattr(inspector_io, attr, None)
        if conn_value != meta_value:
            if meta_value == default_value:
                ignored_attr.add(attr)
            else:
                diff.add(attr)
    return diff, ignored_attr
