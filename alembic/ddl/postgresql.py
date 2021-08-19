import logging
import re
from typing import Any
from typing import cast
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import TYPE_CHECKING
from typing import Union

from sqlalchemy import Column
from sqlalchemy import Numeric
from sqlalchemy import text
from sqlalchemy import types as sqltypes
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.dialects.postgresql import INTEGER
from sqlalchemy.schema import CreateIndex
from sqlalchemy.sql.elements import ColumnClause
from sqlalchemy.sql.elements import UnaryExpression
from sqlalchemy.types import NULLTYPE

from .base import alter_column
from .base import alter_table
from .base import AlterColumn
from .base import ColumnComment
from .base import compiles
from .base import format_column_name
from .base import format_table_name
from .base import format_type
from .base import IdentityColumnDefault
from .base import RenameTable
from .impl import DefaultImpl
from .. import util
from ..autogenerate import render
from ..operations import ops
from ..operations import schemaobj
from ..operations.base import BatchOperations
from ..operations.base import Operations
from ..util import compat
from ..util import sqla_compat

if TYPE_CHECKING:
    from typing import Literal

    from sqlalchemy.dialects.postgresql.array import ARRAY
    from sqlalchemy.dialects.postgresql.base import PGDDLCompiler
    from sqlalchemy.dialects.postgresql.hstore import HSTORE
    from sqlalchemy.dialects.postgresql.json import JSON
    from sqlalchemy.dialects.postgresql.json import JSONB
    from sqlalchemy.sql.elements import BinaryExpression
    from sqlalchemy.sql.elements import quoted_name
    from sqlalchemy.sql.schema import MetaData
    from sqlalchemy.sql.schema import Table
    from sqlalchemy.sql.type_api import TypeEngine

    from .base import _ServerDefault
    from ..autogenerate.api import AutogenContext
    from ..autogenerate.render import _f_name
    from ..runtime.migration import MigrationContext


log = logging.getLogger(__name__)


class PostgresqlImpl(DefaultImpl):
    __dialect__ = "postgresql"
    transactional_ddl = True
    type_synonyms = DefaultImpl.type_synonyms + (
        {"FLOAT", "DOUBLE PRECISION"},
    )
    identity_attrs_ignore = ("on_null", "order")

    def create_index(self, index):
        # this likely defaults to None if not present, so get()
        # should normally not return the default value.  being
        # defensive in any case
        postgresql_include = index.kwargs.get("postgresql_include", None) or ()
        for col in postgresql_include:
            if col not in index.table.c:
                index.table.append_column(Column(col, sqltypes.NullType))
        self._exec(CreateIndex(index))

    def prep_table_for_batch(self, batch_impl, table):

        for constraint in table.constraints:
            if (
                constraint.name is not None
                and constraint.name in batch_impl.named_constraints
            ):
                self.drop_constraint(constraint)

    def compare_server_default(
        self,
        inspector_column,
        metadata_column,
        rendered_metadata_default,
        rendered_inspector_default,
    ):
        # don't do defaults for SERIAL columns
        if (
            metadata_column.primary_key
            and metadata_column is metadata_column.table._autoincrement_column
        ):
            return False

        conn_col_default = rendered_inspector_default

        defaults_equal = conn_col_default == rendered_metadata_default
        if defaults_equal:
            return False

        if None in (conn_col_default, rendered_metadata_default):
            return not defaults_equal

        # check for unquoted string and quote for PG String types
        if (
            not isinstance(inspector_column.type, Numeric)
            and metadata_column.server_default is not None
            and isinstance(
                metadata_column.server_default.arg, compat.string_types
            )
            and not re.match(r"^'.*'$", rendered_metadata_default)
        ):
            rendered_metadata_default = "'%s'" % rendered_metadata_default

        return not self.connection.scalar(
            text(
                "SELECT %s = %s"
                % (conn_col_default, rendered_metadata_default)
            )
        )

    def alter_column(  # type:ignore[override]
        self,
        table_name: str,
        column_name: str,
        nullable: Optional[bool] = None,
        server_default: Union["_ServerDefault", "Literal[False]"] = False,
        name: Optional[str] = None,
        type_: Optional["TypeEngine"] = None,
        schema: Optional[str] = None,
        autoincrement: Optional[bool] = None,
        existing_type: Optional["TypeEngine"] = None,
        existing_server_default: Optional["_ServerDefault"] = None,
        existing_nullable: Optional[bool] = None,
        existing_autoincrement: Optional[bool] = None,
        **kw: Any
    ) -> None:

        using = kw.pop("postgresql_using", None)

        if using is not None and type_ is None:
            raise util.CommandError(
                "postgresql_using must be used with the type_ parameter"
            )

        if type_ is not None:
            self._exec(
                PostgresqlColumnType(
                    table_name,
                    column_name,
                    type_,
                    schema=schema,
                    using=using,
                    existing_type=existing_type,
                    existing_server_default=existing_server_default,
                    existing_nullable=existing_nullable,
                )
            )

        super(PostgresqlImpl, self).alter_column(
            table_name,
            column_name,
            nullable=nullable,
            server_default=server_default,
            name=name,
            schema=schema,
            autoincrement=autoincrement,
            existing_type=existing_type,
            existing_server_default=existing_server_default,
            existing_nullable=existing_nullable,
            existing_autoincrement=existing_autoincrement,
            **kw
        )

    def autogen_column_reflect(self, inspector, table, column_info):
        if column_info.get("default") and isinstance(
            column_info["type"], (INTEGER, BIGINT)
        ):
            seq_match = re.match(
                r"nextval\('(.+?)'::regclass\)", column_info["default"]
            )
            if seq_match:
                info = sqla_compat._exec_on_inspector(
                    inspector,
                    text(
                        "select c.relname, a.attname "
                        "from pg_class as c join "
                        "pg_depend d on d.objid=c.oid and "
                        "d.classid='pg_class'::regclass and "
                        "d.refclassid='pg_class'::regclass "
                        "join pg_class t on t.oid=d.refobjid "
                        "join pg_attribute a on a.attrelid=t.oid and "
                        "a.attnum=d.refobjsubid "
                        "where c.relkind='S' and c.relname=:seqname"
                    ),
                    seqname=seq_match.group(1),
                ).first()
                if info:
                    seqname, colname = info
                    if colname == column_info["name"]:
                        log.info(
                            "Detected sequence named '%s' as "
                            "owned by integer column '%s(%s)', "
                            "assuming SERIAL and omitting",
                            seqname,
                            table.name,
                            colname,
                        )
                        # sequence, and the owner is this column,
                        # its a SERIAL - whack it!
                        del column_info["default"]

    def correct_for_autogen_constraints(
        self,
        conn_unique_constraints,
        conn_indexes,
        metadata_unique_constraints,
        metadata_indexes,
    ):

        conn_indexes_by_name = dict((c.name, c) for c in conn_indexes)

        doubled_constraints = set(
            index
            for index in conn_indexes
            if index.info.get("duplicates_constraint")
        )

        for ix in doubled_constraints:
            conn_indexes.remove(ix)

        for idx in list(metadata_indexes):
            if idx.name in conn_indexes_by_name:
                continue
            exprs = idx.expressions
            for expr in exprs:
                while isinstance(expr, UnaryExpression):
                    expr = expr.element
                if not isinstance(expr, Column):
                    util.warn(
                        "autogenerate skipping functional index %s; "
                        "not supported by SQLAlchemy reflection" % idx.name
                    )
                    metadata_indexes.discard(idx)

    def render_type(
        self, type_: "TypeEngine", autogen_context: "AutogenContext"
    ) -> Union[str, "Literal[False]"]:
        mod = type(type_).__module__
        if not mod.startswith("sqlalchemy.dialects.postgresql"):
            return False

        if hasattr(self, "_render_%s_type" % type_.__visit_name__):
            meth = getattr(self, "_render_%s_type" % type_.__visit_name__)
            return meth(type_, autogen_context)

        return False

    def _render_HSTORE_type(
        self, type_: "HSTORE", autogen_context: "AutogenContext"
    ) -> str:
        return cast(
            str,
            render._render_type_w_subtype(
                type_, autogen_context, "text_type", r"(.+?\(.*text_type=)"
            ),
        )

    def _render_ARRAY_type(
        self, type_: "ARRAY", autogen_context: "AutogenContext"
    ) -> str:
        return cast(
            str,
            render._render_type_w_subtype(
                type_, autogen_context, "item_type", r"(.+?\()"
            ),
        )

    def _render_JSON_type(
        self, type_: "JSON", autogen_context: "AutogenContext"
    ) -> str:
        return cast(
            str,
            render._render_type_w_subtype(
                type_, autogen_context, "astext_type", r"(.+?\(.*astext_type=)"
            ),
        )

    def _render_JSONB_type(
        self, type_: "JSONB", autogen_context: "AutogenContext"
    ) -> str:
        return cast(
            str,
            render._render_type_w_subtype(
                type_, autogen_context, "astext_type", r"(.+?\(.*astext_type=)"
            ),
        )


class PostgresqlColumnType(AlterColumn):
    def __init__(
        self, name: str, column_name: str, type_: "TypeEngine", **kw
    ) -> None:
        using = kw.pop("using", None)
        super(PostgresqlColumnType, self).__init__(name, column_name, **kw)
        self.type_ = sqltypes.to_instance(type_)
        self.using = using


@compiles(RenameTable, "postgresql")
def visit_rename_table(
    element: RenameTable, compiler: "PGDDLCompiler", **kw
) -> str:
    return "%s RENAME TO %s" % (
        alter_table(compiler, element.table_name, element.schema),
        format_table_name(compiler, element.new_table_name, None),
    )


@compiles(PostgresqlColumnType, "postgresql")
def visit_column_type(
    element: PostgresqlColumnType, compiler: "PGDDLCompiler", **kw
) -> str:
    return "%s %s %s %s" % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
        "TYPE %s" % format_type(compiler, element.type_),
        "USING %s" % element.using if element.using else "",
    )


@compiles(ColumnComment, "postgresql")
def visit_column_comment(
    element: "ColumnComment", compiler: "PGDDLCompiler", **kw
) -> str:
    ddl = "COMMENT ON COLUMN {table_name}.{column_name} IS {comment}"
    comment = (
        compiler.sql_compiler.render_literal_value(
            element.comment, sqltypes.String()
        )
        if element.comment is not None
        else "NULL"
    )

    return ddl.format(
        table_name=format_table_name(
            compiler, element.table_name, element.schema
        ),
        column_name=format_column_name(compiler, element.column_name),
        comment=comment,
    )


@compiles(IdentityColumnDefault, "postgresql")
def visit_identity_column(
    element: "IdentityColumnDefault", compiler: "PGDDLCompiler", **kw
):
    text = "%s %s " % (
        alter_table(compiler, element.table_name, element.schema),
        alter_column(compiler, element.column_name),
    )
    if element.default is None:
        # drop identity
        text += "DROP IDENTITY"
        return text
    elif element.existing_server_default is None:
        # add identity options
        text += "ADD "
        text += compiler.visit_identity_column(element.default)
        return text
    else:
        # alter identity
        diff, _, _ = element.impl._compare_identity_default(
            element.default, element.existing_server_default
        )
        identity = element.default
        for attr in sorted(diff):
            if attr == "always":
                text += "SET GENERATED %s " % (
                    "ALWAYS" if identity.always else "BY DEFAULT"
                )
            else:
                text += "SET %s " % compiler.get_identity_options(
                    sqla_compat.Identity(**{attr: getattr(identity, attr)})
                )
        return text


@Operations.register_operation("create_exclude_constraint")
@BatchOperations.register_operation(
    "create_exclude_constraint", "batch_create_exclude_constraint"
)
@ops.AddConstraintOp.register_add_constraint("exclude_constraint")
class CreateExcludeConstraintOp(ops.AddConstraintOp):
    """Represent a create exclude constraint operation."""

    constraint_type = "exclude"

    def __init__(
        self,
        constraint_name: Optional[str],
        table_name: Union[str, "quoted_name"],
        elements: Union[
            Sequence[Tuple[str, str]],
            Sequence[Tuple["ColumnClause", str]],
        ],
        where: Optional[Union["BinaryExpression", str]] = None,
        schema: Optional[str] = None,
        _orig_constraint: Optional["ExcludeConstraint"] = None,
        **kw
    ) -> None:
        self.constraint_name = constraint_name
        self.table_name = table_name
        self.elements = elements
        self.where = where
        self.schema = schema
        self._orig_constraint = _orig_constraint
        self.kw = kw

    @classmethod
    def from_constraint(  # type:ignore[override]
        cls, constraint: "ExcludeConstraint"
    ) -> "CreateExcludeConstraintOp":
        constraint_table = sqla_compat._table_for_constraint(constraint)

        return cls(
            constraint.name,
            constraint_table.name,
            [
                (expr, op)
                for expr, name, op in constraint._render_exprs  # type:ignore[attr-defined] # noqa
            ],
            where=constraint.where,
            schema=constraint_table.schema,
            _orig_constraint=constraint,
            deferrable=constraint.deferrable,
            initially=constraint.initially,
            using=constraint.using,
        )

    def to_constraint(
        self, migration_context: Optional["MigrationContext"] = None
    ) -> "ExcludeConstraint":
        if self._orig_constraint is not None:
            return self._orig_constraint
        schema_obj = schemaobj.SchemaObjects(migration_context)
        t = schema_obj.table(self.table_name, schema=self.schema)
        excl = ExcludeConstraint(
            *self.elements,
            name=self.constraint_name,
            where=self.where,
            **self.kw
        )
        for (
            expr,
            name,
            oper,
        ) in excl._render_exprs:  # type:ignore[attr-defined]
            t.append_column(Column(name, NULLTYPE))
        t.append_constraint(excl)
        return excl

    @classmethod
    def create_exclude_constraint(
        cls,
        operations: "Operations",
        constraint_name: str,
        table_name: str,
        *elements: Any,
        **kw: Any
    ) -> Optional["Table"]:
        """Issue an alter to create an EXCLUDE constraint using the
        current migration context.

        .. note::  This method is Postgresql specific, and additionally
           requires at least SQLAlchemy 1.0.

        e.g.::

            from alembic import op

            op.create_exclude_constraint(
                "user_excl",
                "user",

                ("period", '&&'),
                ("group", '='),
                where=("group != 'some group'")

            )

        Note that the expressions work the same way as that of
        the ``ExcludeConstraint`` object itself; if plain strings are
        passed, quoting rules must be applied manually.

        :param name: Name of the constraint.
        :param table_name: String name of the source table.
        :param elements: exclude conditions.
        :param where: SQL expression or SQL string with optional WHERE
         clause.
        :param deferrable: optional bool. If set, emit DEFERRABLE or
         NOT DEFERRABLE when issuing DDL for this constraint.
        :param initially: optional string. If set, emit INITIALLY <value>
         when issuing DDL for this constraint.
        :param schema: Optional schema name to operate within.

        """
        op = cls(constraint_name, table_name, elements, **kw)
        return operations.invoke(op)

    @classmethod
    def batch_create_exclude_constraint(
        cls, operations, constraint_name, *elements, **kw
    ):
        """Issue a "create exclude constraint" instruction using the
        current batch migration context.

        .. note::  This method is Postgresql specific, and additionally
           requires at least SQLAlchemy 1.0.

        .. seealso::

            :meth:`.Operations.create_exclude_constraint`

        """
        kw["schema"] = operations.impl.schema
        op = cls(constraint_name, operations.impl.table_name, elements, **kw)
        return operations.invoke(op)


@render.renderers.dispatch_for(CreateExcludeConstraintOp)
def _add_exclude_constraint(
    autogen_context: "AutogenContext", op: "CreateExcludeConstraintOp"
) -> str:
    return _exclude_constraint(op.to_constraint(), autogen_context, alter=True)


@render._constraint_renderers.dispatch_for(ExcludeConstraint)
def _render_inline_exclude_constraint(
    constraint: "ExcludeConstraint",
    autogen_context: "AutogenContext",
    namespace_metadata: "MetaData",
) -> str:
    rendered = render._user_defined_render(
        "exclude", constraint, autogen_context
    )
    if rendered is not False:
        return rendered

    return _exclude_constraint(constraint, autogen_context, False)


def _postgresql_autogenerate_prefix(autogen_context: "AutogenContext") -> str:

    imports = autogen_context.imports
    if imports is not None:
        imports.add("from sqlalchemy.dialects import postgresql")
    return "postgresql."


def _exclude_constraint(
    constraint: "ExcludeConstraint",
    autogen_context: "AutogenContext",
    alter: bool,
) -> str:
    opts: List[Tuple[str, Union[quoted_name, str, _f_name, None]]] = []

    has_batch = autogen_context._has_batch

    if constraint.deferrable:
        opts.append(("deferrable", str(constraint.deferrable)))
    if constraint.initially:
        opts.append(("initially", str(constraint.initially)))
    if constraint.using:
        opts.append(("using", str(constraint.using)))
    if not has_batch and alter and constraint.table.schema:
        opts.append(("schema", render._ident(constraint.table.schema)))
    if not alter and constraint.name:
        opts.append(
            ("name", render._render_gen_name(autogen_context, constraint.name))
        )

    if alter:
        args = [
            repr(render._render_gen_name(autogen_context, constraint.name))
        ]
        if not has_batch:
            args += [repr(render._ident(constraint.table.name))]
        args.extend(
            [
                "(%s, %r)"
                % (
                    _render_potential_column(sqltext, autogen_context),
                    opstring,
                )
                for sqltext, name, opstring in constraint._render_exprs  # type:ignore[attr-defined] # noqa
            ]
        )
        if constraint.where is not None:
            args.append(
                "where=%s"
                % render._render_potential_expr(
                    constraint.where, autogen_context
                )
            )
        args.extend(["%s=%r" % (k, v) for k, v in opts])
        return "%(prefix)screate_exclude_constraint(%(args)s)" % {
            "prefix": render._alembic_autogenerate_prefix(autogen_context),
            "args": ", ".join(args),
        }
    else:
        args = [
            "(%s, %r)"
            % (_render_potential_column(sqltext, autogen_context), opstring)
            for sqltext, name, opstring in constraint._render_exprs  # type:ignore[attr-defined] # noqa
        ]
        if constraint.where is not None:
            args.append(
                "where=%s"
                % render._render_potential_expr(
                    constraint.where, autogen_context
                )
            )
        args.extend(["%s=%r" % (k, v) for k, v in opts])
        return "%(prefix)sExcludeConstraint(%(args)s)" % {
            "prefix": _postgresql_autogenerate_prefix(autogen_context),
            "args": ", ".join(args),
        }


def _render_potential_column(
    value: Union["ColumnClause", "Column"], autogen_context: "AutogenContext"
) -> str:
    if isinstance(value, ColumnClause):
        template = "%(prefix)scolumn(%(name)r)"

        return template % {
            "prefix": render._sqlalchemy_autogenerate_prefix(autogen_context),
            "name": value.name,
        }

    else:
        return render._render_potential_expr(
            value, autogen_context, wrap_in_text=False
        )
