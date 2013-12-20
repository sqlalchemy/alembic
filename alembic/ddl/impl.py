from sqlalchemy.sql.expression import _BindParamClause
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import schema, text
from sqlalchemy import types as sqltypes

from ..compat import string_types, text_type, with_metaclass
from .. import util
from . import base

class ImplMeta(type):
    def __init__(cls, classname, bases, dict_):
        newtype = type.__init__(cls, classname, bases, dict_)
        if '__dialect__' in dict_:
            _impls[dict_['__dialect__']] = cls
        return newtype

_impls = {}

class DefaultImpl(with_metaclass(ImplMeta)):
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
        self.output_buffer = output_buffer
        self.memo = {}
        self.context_opts = context_opts
        if transactional_ddl is not None:
            self.transactional_ddl = transactional_ddl

    @classmethod
    def get_by_dialect(cls, dialect):
        return _impls[dialect.name]

    def static_output(self, text):
        self.output_buffer.write(text_type(text + "\n\n"))
        self.output_buffer.flush()

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
            self.static_output(text_type(
                    construct.compile(dialect=self.dialect)
                    ).replace("\t", "    ").strip() + self.command_terminator)
        else:
            conn = self.connection
            if execution_options:
                conn = conn.execution_options(**execution_options)
            conn.execute(construct, *multiparams, **params)

    def execute(self, sql, execution_options=None):
        self._exec(sql, execution_options)

    def alter_column(self, table_name, column_name,
                        nullable=None,
                        server_default=False,
                        name=None,
                        type_=None,
                        schema=None,
                        autoincrement=None,
                        existing_type=None,
                        existing_server_default=None,
                        existing_nullable=None,
                        existing_autoincrement=None
                    ):
        if autoincrement is not None or existing_autoincrement is not None:
            util.warn("nautoincrement and existing_autoincrement only make sense for MySQL")
        if nullable is not None:
            self._exec(base.ColumnNullable(table_name, column_name,
                                nullable, schema=schema,
                                existing_type=existing_type,
                                existing_server_default=existing_server_default,
                                existing_nullable=existing_nullable,
                                ))
        if server_default is not False:
            self._exec(base.ColumnDefault(
                                table_name, column_name, server_default,
                                schema=schema,
                                existing_type=existing_type,
                                existing_server_default=existing_server_default,
                                existing_nullable=existing_nullable,
                            ))
        if type_ is not None:
            self._exec(base.ColumnType(
                                table_name, column_name, type_, schema=schema,
                                existing_type=existing_type,
                                existing_server_default=existing_server_default,
                                existing_nullable=existing_nullable,
                            ))
        # do the new name last ;)
        if name is not None:
            self._exec(base.ColumnName(
                                table_name, column_name, name, schema=schema,
                                existing_type=existing_type,
                                existing_server_default=existing_server_default,
                                existing_nullable=existing_nullable,
                            ))

    def add_column(self, table_name, column, schema=None):
        self._exec(base.AddColumn(table_name, column, schema=schema))

    def drop_column(self, table_name, column, schema=None, **kw):
        self._exec(base.DropColumn(table_name, column, schema=schema))

    def add_constraint(self, const):
        if const._create_rule is None or \
            const._create_rule(self):
            self._exec(schema.AddConstraint(const))

    def drop_constraint(self, const):
        self._exec(schema.DropConstraint(const))

    def rename_table(self, old_table_name, new_table_name, schema=None):
        self._exec(base.RenameTable(old_table_name,
                    new_table_name, schema=schema))

    def create_table(self, table):
        if util.sqla_07:
            table.dispatch.before_create(table, self.connection,
                                        checkfirst=False,
                                            _ddl_runner=self)
        self._exec(schema.CreateTable(table))
        if util.sqla_07:
            table.dispatch.after_create(table, self.connection,
                                        checkfirst=False,
                                            _ddl_runner=self)
        for index in table.indexes:
            self._exec(schema.CreateIndex(index))

    def drop_table(self, table):
        self._exec(schema.DropTable(table))

    def create_index(self, index):
        self._exec(schema.CreateIndex(index))

    def drop_index(self, index):
        self._exec(schema.DropIndex(index))

    def bulk_insert(self, table, rows):
        if not isinstance(rows, list):
            raise TypeError("List expected")
        elif rows and not isinstance(rows[0], dict):
            raise TypeError("List of dictionaries expected")
        if self.as_sql:
            for row in rows:
                self._exec(table.insert(inline=True).values(**dict(
                    (k, _literal_bindparam(k, v, type_=table.c[k].type))
                    for k, v in row.items()
                )))
        else:
            # work around http://www.sqlalchemy.org/trac/ticket/2461
            if not hasattr(table, '_autoincrement_column'):
                table._autoincrement_column = None
            self._exec(table.insert(inline=True), multiparams=rows)

    def compare_type(self, inspector_column, metadata_column):

        conn_type = inspector_column.type
        metadata_type = metadata_column.type

        metadata_impl = metadata_type.dialect_impl(self.dialect)

        # work around SQLAlchemy bug "stale value for type affinity"
        # fixed in 0.7.4
        metadata_impl.__dict__.pop('_type_affinity', None)

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

class _literal_bindparam(_BindParamClause):
    pass

@compiles(_literal_bindparam)
def _render_literal_bindparam(element, compiler, **kw):
    return compiler.render_literal_bindparam(element, **kw)


def _string_compare(t1, t2):
    return \
        t1.length is not None and \
        t1.length != t2.length

def _numeric_compare(t1, t2):
    return \
        (
            t1.precision is not None and \
            t1.precision != t2.precision
        ) or \
        (
            t1.scale is not None and \
            t1.scale != t2.scale
        )
_type_comparators = {
    sqltypes.String:_string_compare,
    sqltypes.Numeric:_numeric_compare
}




