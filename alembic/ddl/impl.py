from sqlalchemy import schema, text
from sqlalchemy import types as sqltypes

from ..util.compat import (
    string_types, text_type, with_metaclass
)
from ..util import sqla_compat
from .. import util
from ...operations import ops
from . import base


class ImplMeta(type):

    def __init__(cls, classname, bases, dict_):
        newtype = type.__init__(cls, classname, bases, dict_)
        if '__dialect__' in dict_:
            _impls[dict_['__dialect__']] = cls
        return newtype

_impls = {}


class DefaultEmitToDB(ops.MigrationDispatch):
    def __init__(self, impl):
        self.impl = impl

    def emit_to_db(self, operation):
        self.impl._exec(operation)

    def alter_column(self, operation, **kw):
        if operation.has_nullable:
            self.emit_to_db(
                base.ColumnNullable(
                    operation.table_name, operation.column_name,
                    operation.modify_nullable,
                    schema=operation.schema,
                    existing_type=operation.existing_type,
                    existing_server_default=operation.existing_server_default,
                    existing_nullable=operation.existing_nullable,
                )
            )
        if operation.has_server_default:
            self.emit_to_db(
                base.ColumnServerDefault(
                    operation.table_name, operation.column_name,
                    operation.modify_server_default,
                    schema=operation.schema,
                    existing_type=operation.existing_type,
                    existing_server_default=operation.existing_server_default,
                    existing_nullable=operation.existing_nullable,
                )
            )
        if operation.has_type:
            self.emit_to_db(
                base.ColumnType(
                    operation.table_name, operation.column_name,
                    operation.modify_type,
                    schema=operation.schema,
                    existing_type=operation.existing_type,
                    existing_server_default=operation.existing_server_default,
                    existing_nullable=operation.existing_nullable,
                )
            )
        if operation.has_name:
            self.emit_to_db(
                base.ColumnName(
                    operation.table_name, operation.column_name,
                    operation.modify_name,
                    schema=operation.schema,
                    existing_type=operation.existing_type,
                    existing_server_default=operation.existing_server_default,
                    existing_nullable=operation.existing_nullable,
                )
            )

    def add_column(self, operation, **kw):
        self.emit_to_db(
            base.AddColumn(operation.element)
        )

    def drop_column(self, operation, **kw):
        self.emit_to_db(
            base.DropColumn(operation.element)
        )

    def add_constraint(self, operation, **kw):
        const = operation.element
        if const._create_rule is None or \
                const._create_rule(self):
            self.emit_to_db(base.AddConstraint(operation.element))

    def drop_constraint(self, operation, **kw):
        self.emit_to_db(base.DropConstraint(operation.element))

    def rename_table(self, operation, **kw):
        self.emit_to_db(
            base.RenameTable(
                operation.old_table_name,
                operation.new_table_name,
                schema=operation.schema)
        )

    def create_table(self, operation, **kw):
        table = operation.element
        table.dispatch.before_create(table, self.impl.connection,
                                     checkfirst=False,
                                     _ddl_runner=self.impl)
        self.emit_to_db(
            schema.CreateTable(table)
        )
        table.dispatch.after_create(table, self.impl.connection,
                                    checkfirst=False,
                                    _ddl_runner=self.impl)
        for index in table.indexes:
            self.emit_to_db(schema.CreateIndex(index))

    def drop_table(self, operation, **kw):
        self.emit_to_db(operation)

    def create_index(self, operation, **kw):
        self.emit_to_db(operation)

    def drop_index(self, operation, **kw):
        self.emit_to_db(operation)

    def bulk_insert(self, operation, **kw):
        table, rows, multiinsert = (
            operation.table, operation.rows, operation.multiinsert)

        if not isinstance(rows, list):
            raise TypeError("List expected")
        elif rows and not isinstance(rows[0], dict):
            raise TypeError("List of dictionaries expected")
        if self.as_sql:
            for row in rows:
                self._exec(table.insert(inline=True).values(**dict(
                    (k,
                        sqla_compat._literal_bindparam(
                            k, v, type_=table.c[k].type)
                        if not isinstance(
                            v, sqla_compat._literal_bindparam) else v)
                    for k, v in row.items()
                )))
        else:
            # work around http://www.sqlalchemy.org/trac/ticket/2461
            if not hasattr(table, '_autoincrement_column'):
                table._autoincrement_column = None
            if rows:
                if multiinsert:
                    self._exec(table.insert(inline=True), multiparams=rows)
                else:
                    for row in rows:
                        self._exec(table.insert(inline=True).values(**row))


class DefaultImpl(legacy.LegacyImpl, with_metaclass(ImplMeta)):

    """Provide the entrypoint for major migration operations,
    including database-specific behavioral variances.

    While individual SQL/DDL constructs already provide
    for database-specific implementations, variances here
    allow for entirely different sequences of operations
    to take place for a particular migration, such as
    SQL Server's special 'IDENTITY INSERT' step for
    bulk inserts.

    """
    __dialect__ = 'default'

    transactional_ddl = False
    command_terminator = ";"

    def __init__(self, dialect, connection, as_sql,
                 transactional_ddl, output_buffer,
                 context_opts):
        self.dialect = dialect
        self.connection = connection
        self.as_sql = as_sql
        self.literal_binds = context_opts.get('literal_binds', False)
        if self.literal_binds and not util.sqla_08:
            util.warn("'literal_binds' flag not supported in SQLAlchemy 0.7")
            self.literal_binds = False

        self.output_buffer = output_buffer
        self.memo = {}
        self.context_opts = context_opts
        if transactional_ddl is not None:
            self.transactional_ddl = transactional_ddl

        if self.literal_binds:
            if not self.as_sql:
                raise util.CommandError(
                    "Can't use literal_binds setting without as_sql mode")

    @classmethod
    def get_by_dialect(cls, dialect):
        return _impls[dialect.name]

    def static_output(self, text):
        self.output_buffer.write(text_type(text + "\n\n"))
        self.output_buffer.flush()

    def requires_recreate_in_batch(self, batch_op):
        """Return True if the given :class:`.BatchOperationsImpl`
        would need the table to be recreated and copied in order to
        proceed.

        Normally, only returns True on SQLite when operations other
        than add_column are present.

        """
        return False

    def prep_table_for_batch(self, table):
        """perform any operations needed on a table before a new
        one is created to replace it in batch mode.

        the PG dialect uses this to drop constraints on the table
        before the new one uses those same names.

        """

    @property
    def bind(self):
        return self.connection

    def _exec(self, construct, execution_options=None,
              multiparams=(),
              params=util.immutabledict()):
        if isinstance(construct, string_types):
            construct = text(construct)
        if self.as_sql:
            if multiparams or params:
                # TODO: coverage
                raise Exception("Execution arguments not allowed with as_sql")

            if self.literal_binds and not isinstance(
                    construct, schema.DDLElement):
                compile_kw = dict(compile_kwargs={"literal_binds": True})
            else:
                compile_kw = {}

            self.static_output(text_type(
                construct.compile(dialect=self.dialect, **compile_kw)
            ).replace("\t", "    ").strip() + self.command_terminator)
        else:
            conn = self.connection
            if execution_options:
                conn = conn.execution_options(**execution_options)
            return conn.execute(construct, *multiparams, **params)

    def execute(self, sql, execution_options=None):
        self._exec(sql, execution_options)

    def compare_type(self, inspector_column, metadata_column):

        conn_type = inspector_column.type
        metadata_type = metadata_column.type

        metadata_impl = metadata_type.dialect_impl(self.dialect)

        # work around SQLAlchemy bug "stale value for type affinity"
        # fixed in 0.7.4
        metadata_impl.__dict__.pop('_type_affinity', None)

        if hasattr(metadata_impl, "compare_against_backend"):
            comparison = metadata_impl.compare_against_backend(
                self.dialect, conn_type)
            if comparison is not None:
                return not comparison

        if conn_type._compare_type_affinity(
            metadata_impl
        ):
            comparator = _type_comparators.get(conn_type._type_affinity, None)

            return comparator and comparator(metadata_type, conn_type)
        else:
            return True

    def compare_server_default(self, inspector_column,
                               metadata_column,
                               rendered_metadata_default,
                               rendered_inspector_default):
        return rendered_inspector_default != rendered_metadata_default

    def correct_for_autogen_constraints(self, conn_uniques, conn_indexes,
                                        metadata_unique_constraints,
                                        metadata_indexes):
        pass

    def _compat_autogen_column_reflect(self, inspector):
        if util.sqla_08:
            return self.autogen_column_reflect
        else:
            def adapt(table, column_info):
                return self.autogen_column_reflect(
                    inspector, table, column_info)
            return adapt

    def autogen_column_reflect(self, inspector, table, column_info):
        """A hook that is attached to the 'column_reflect' event for when
        a Table is reflected from the database during the autogenerate
        process.

        Dialects can elect to modify the information gathered here.

        """

    def start_migrations(self):
        """A hook called when :meth:`.EnvironmentContext.run_migrations`
        is called.

        Implementations can set up per-migration-run state here.

        """

    def emit_begin(self):
        """Emit the string ``BEGIN``, or the backend-specific
        equivalent, on the current connection context.

        This is used in offline mode and typically
        via :meth:`.EnvironmentContext.begin_transaction`.

        """
        self.static_output("BEGIN" + self.command_terminator)

    def emit_commit(self):
        """Emit the string ``COMMIT``, or the backend-specific
        equivalent, on the current connection context.

        This is used in offline mode and typically
        via :meth:`.EnvironmentContext.begin_transaction`.

        """
        self.static_output("COMMIT" + self.command_terminator)


def _string_compare(t1, t2):
    return \
        t1.length is not None and \
        t1.length != t2.length


def _numeric_compare(t1, t2):
    return \
        (
            t1.precision is not None and
            t1.precision != t2.precision
        ) or \
        (
            t1.scale is not None and
            t1.scale != t2.scale
        )
_type_comparators = {
    sqltypes.String: _string_compare,
    sqltypes.Numeric: _numeric_compare
}
