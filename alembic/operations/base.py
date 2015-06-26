from contextlib import contextmanager

from sqlalchemy import schema as sa_schema

from .. import util
from ..util import sqla_compat
from . import batch
from . import schemaobj
from . import ops
from . import toimpl

__all__ = ('Operations', 'BatchOperations')

try:
    from sqlalchemy.sql.naming import conv
except:
    conv = None


class Operations(object):

    """Define high level migration operations.

    Each operation corresponds to some schema migration operation,
    executed against a particular :class:`.MigrationContext`
    which in turn represents connectivity to a database,
    or a file output stream.

    While :class:`.Operations` is normally configured as
    part of the :meth:`.EnvironmentContext.run_migrations`
    method called from an ``env.py`` script, a standalone
    :class:`.Operations` instance can be
    made for use cases external to regular Alembic
    migrations by passing in a :class:`.MigrationContext`::

        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        conn = myengine.connect()
        ctx = MigrationContext.configure(conn)
        op = Operations(ctx)

        op.alter_column("t", "c", nullable=True)

    """

    def __init__(self, migration_context, impl=None):
        """Construct a new :class:`.Operations`

        :param migration_context: a :class:`.MigrationContext`
         instance.

        """
        self.migration_context = migration_context
        if impl is None:
            self.impl = migration_context.impl
        else:
            self.impl = impl

        self.schema_obj = schemaobj.SchemaObjects(migration_context)

    @classmethod
    @contextmanager
    def context(cls, migration_context):
        from ..op import _install_proxy, _remove_proxy
        op = Operations(migration_context)
        _install_proxy(op)
        yield op
        _remove_proxy()

    @contextmanager
    def batch_alter_table(
            self, table_name, schema=None, recreate="auto", copy_from=None,
            table_args=(), table_kwargs=util.immutabledict(),
            reflect_args=(), reflect_kwargs=util.immutabledict(),
            naming_convention=None):
        """Invoke a series of per-table migrations in batch.

        Batch mode allows a series of operations specific to a table
        to be syntactically grouped together, and allows for alternate
        modes of table migration, in particular the "recreate" style of
        migration required by SQLite.

        "recreate" style is as follows:

        1. A new table is created with the new specification, based on the
           migration directives within the batch, using a temporary name.

        2. the data copied from the existing table to the new table.

        3. the existing table is dropped.

        4. the new table is renamed to the existing table name.

        The directive by default will only use "recreate" style on the
        SQLite backend, and only if directives are present which require
        this form, e.g. anything other than ``add_column()``.   The batch
        operation on other backends will proceed using standard ALTER TABLE
        operations.

        The method is used as a context manager, which returns an instance
        of :class:`.BatchOperations`; this object is the same as
        :class:`.Operations` except that table names and schema names
        are omitted.  E.g.::

            with op.batch_alter_table("some_table") as batch_op:
                batch_op.add_column(Column('foo', Integer))
                batch_op.drop_column('bar')

        The operations within the context manager are invoked at once
        when the context is ended.   When run against SQLite, if the
        migrations include operations not supported by SQLite's ALTER TABLE,
        the entire table will be copied to a new one with the new
        specification, moving all data across as well.

        The copy operation by default uses reflection to retrieve the current
        structure of the table, and therefore :meth:`.batch_alter_table`
        in this mode requires that the migration is run in "online" mode.
        The ``copy_from`` parameter may be passed which refers to an existing
        :class:`.Table` object, which will bypass this reflection step.

        .. note::  The table copy operation will currently not copy
           CHECK constraints, and may not copy UNIQUE constraints that are
           unnamed, as is possible on SQLite.   See the section
           :ref:`sqlite_batch_constraints` for workarounds.

        :param table_name: name of table
        :param schema: optional schema name.
        :param recreate: under what circumstances the table should be
         recreated. At its default of ``"auto"``, the SQLite dialect will
         recreate the table if any operations other than ``add_column()``,
         ``create_index()``, or ``drop_index()`` are
         present. Other options include ``"always"`` and ``"never"``.
        :param copy_from: optional :class:`~sqlalchemy.schema.Table` object
         that will act as the structure of the table being copied.  If omitted,
         table reflection is used to retrieve the structure of the table.

         .. versionadded:: 0.7.6 Fully implemented the
            :paramref:`~.Operations.batch_alter_table.copy_from`
            parameter.

         .. seealso::

            :ref:`batch_offline_mode`

            :paramref:`~.Operations.batch_alter_table.reflect_args`

            :paramref:`~.Operations.batch_alter_table.reflect_kwargs`

        :param reflect_args: a sequence of additional positional arguments that
         will be applied to the table structure being reflected / copied;
         this may be used to pass column and constraint overrides to the
         table that will be reflected, in lieu of passing the whole
         :class:`~sqlalchemy.schema.Table` using
         :paramref:`~.Operations.batch_alter_table.copy_from`.

         .. versionadded:: 0.7.1

        :param reflect_kwargs: a dictionary of additional keyword arguments
         that will be applied to the table structure being copied; this may be
         used to pass additional table and reflection options to the table that
         will be reflected, in lieu of passing the whole
         :class:`~sqlalchemy.schema.Table` using
         :paramref:`~.Operations.batch_alter_table.copy_from`.

         .. versionadded:: 0.7.1

        :param table_args: a sequence of additional positional arguments that
         will be applied to the new :class:`~sqlalchemy.schema.Table` when
         created, in addition to those copied from the source table.
         This may be used to provide additional constraints such as CHECK
         constraints that may not be reflected.
        :param table_kwargs: a dictionary of additional keyword arguments
         that will be applied to the new :class:`~sqlalchemy.schema.Table`
         when created, in addition to those copied from the source table.
         This may be used to provide for additional table options that may
         not be reflected.

        .. versionadded:: 0.7.0

        :param naming_convention: a naming convention dictionary of the form
         described at :ref:`autogen_naming_conventions` which will be applied
         to the :class:`~sqlalchemy.schema.MetaData` during the reflection
         process.  This is typically required if one wants to drop SQLite
         constraints, as these constraints will not have names when
         reflected on this backend.  Requires SQLAlchemy **0.9.4** or greater.

         .. seealso::

            :ref:`dropping_sqlite_foreign_keys`

         .. versionadded:: 0.7.1

        .. note:: batch mode requires SQLAlchemy 0.8 or above.

        .. seealso::

            :ref:`batch_migrations`

        """
        impl = batch.BatchOperationsImpl(
            self, table_name, schema, recreate,
            copy_from, table_args, table_kwargs, reflect_args,
            reflect_kwargs, naming_convention)
        batch_op = BatchOperations(self.migration_context, impl=impl)
        yield batch_op
        impl.flush()

    def get_context(self):
        """Return the :class:`.MigrationContext` object that's
        currently in use.

        """

        return self.migration_context

    def rename_table(self, old_table_name, new_table_name, schema=None):
        """Emit an ALTER TABLE to rename a table.

        :param old_table_name: old name.
        :param new_table_name: new name.
        :param schema: Optional schema name to operate within.  To control
         quoting of the schema outside of the default behavior, use
         the SQLAlchemy construct
         :class:`~sqlalchemy.sql.elements.quoted_name`.

         .. versionadded:: 0.7.0 'schema' can now accept a
            :class:`~sqlalchemy.sql.elements.quoted_name` construct.

        """
        self.impl.rename_table(
            old_table_name,
            new_table_name,
            schema=schema
        )

    @util._with_legacy_names([('name', 'new_column_name')])
    def alter_column(
        self, table_name, column_name,
        nullable=None,
        server_default=False,
        new_column_name=None,
        type_=None,
        existing_type=None,
        existing_server_default=False,
        existing_nullable=None,
        schema=None, **kw
    ):
        """Issue an "alter column" instruction using the
        current migration context.

        Generally, only that aspect of the column which
        is being changed, i.e. name, type, nullability,
        default, needs to be specified.  Multiple changes
        can also be specified at once and the backend should
        "do the right thing", emitting each change either
        separately or together as the backend allows.

        MySQL has special requirements here, since MySQL
        cannot ALTER a column without a full specification.
        When producing MySQL-compatible migration files,
        it is recommended that the ``existing_type``,
        ``existing_server_default``, and ``existing_nullable``
        parameters be present, if not being altered.

        Type changes which are against the SQLAlchemy
        "schema" types :class:`~sqlalchemy.types.Boolean`
        and  :class:`~sqlalchemy.types.Enum` may also
        add or drop constraints which accompany those
        types on backends that don't support them natively.
        The ``existing_server_default`` argument is
        used in this case as well to remove a previous
        constraint.

        :param table_name: string name of the target table.
        :param column_name: string name of the target column,
         as it exists before the operation begins.
        :param nullable: Optional; specify ``True`` or ``False``
         to alter the column's nullability.
        :param server_default: Optional; specify a string
         SQL expression, :func:`~sqlalchemy.sql.expression.text`,
         or :class:`~sqlalchemy.schema.DefaultClause` to indicate
         an alteration to the column's default value.
         Set to ``None`` to have the default removed.
        :param new_column_name: Optional; specify a string name here to
         indicate the new name within a column rename operation.
        :param ``type_``: Optional; a :class:`~sqlalchemy.types.TypeEngine`
         type object to specify a change to the column's type.
         For SQLAlchemy types that also indicate a constraint (i.e.
         :class:`~sqlalchemy.types.Boolean`, :class:`~sqlalchemy.types.Enum`),
         the constraint is also generated.
        :param autoincrement: set the ``AUTO_INCREMENT`` flag of the column;
         currently understood by the MySQL dialect.
        :param existing_type: Optional; a
         :class:`~sqlalchemy.types.TypeEngine`
         type object to specify the previous type.   This
         is required for all MySQL column alter operations that
         don't otherwise specify a new type, as well as for
         when nullability is being changed on a SQL Server
         column.  It is also used if the type is a so-called
         SQLlchemy "schema" type which may define a constraint (i.e.
         :class:`~sqlalchemy.types.Boolean`,
         :class:`~sqlalchemy.types.Enum`),
         so that the constraint can be dropped.
        :param existing_server_default: Optional; The existing
         default value of the column.   Required on MySQL if
         an existing default is not being changed; else MySQL
         removes the default.
        :param existing_nullable: Optional; the existing nullability
         of the column.  Required on MySQL if the existing nullability
         is not being changed; else MySQL sets this to NULL.
        :param existing_autoincrement: Optional; the existing autoincrement
         of the column.  Used for MySQL's system of altering a column
         that specifies ``AUTO_INCREMENT``.
        :param schema: Optional schema name to operate within.  To control
         quoting of the schema outside of the default behavior, use
         the SQLAlchemy construct
         :class:`~sqlalchemy.sql.elements.quoted_name`.

         .. versionadded:: 0.7.0 'schema' can now accept a
            :class:`~sqlalchemy.sql.elements.quoted_name` construct.

        """

        alt = ops.AlterColumnOp(
            table_name, column_name, schema=schema,
            existing_type=existing_type,
            existing_server_default=existing_server_default,
            existing_nullable=existing_nullable,
            modify_name=new_column_name,
            modify_type=type_,
            modify_server_default=server_default,
            modify_nullable=nullable,
            **kw
        )

        return self.invoke(alt)

    def invoke(self, operation):
        fn = ops.to_impl.dispatch(
            operation, self.migration_context.impl.__dialect__)
        return fn(self, operation)

    def f(self, name):
        """Indicate a string name that has already had a naming convention
        applied to it.

        This feature combines with the SQLAlchemy ``naming_convention`` feature
        to disambiguate constraint names that have already had naming
        conventions applied to them, versus those that have not.  This is
        necessary in the case that the ``"%(constraint_name)s"`` token
        is used within a naming convention, so that it can be identified
        that this particular name should remain fixed.

        If the :meth:`.Operations.f` is used on a constraint, the naming
        convention will not take effect::

            op.add_column('t', 'x', Boolean(name=op.f('ck_bool_t_x')))

        Above, the CHECK constraint generated will have the name
        ``ck_bool_t_x`` regardless of whether or not a naming convention is
        in use.

        Alternatively, if a naming convention is in use, and 'f' is not used,
        names will be converted along conventions.  If the ``target_metadata``
        contains the naming convention
        ``{"ck": "ck_bool_%(table_name)s_%(constraint_name)s"}``, then the
        output of the following:

            op.add_column('t', 'x', Boolean(name='x'))

        will be::

            CONSTRAINT ck_bool_t_x CHECK (x in (1, 0)))

        The function is rendered in the output of autogenerate when
        a particular constraint name is already converted, for SQLAlchemy
        version **0.9.4 and greater only**.   Even though ``naming_convention``
        was introduced in 0.9.2, the string disambiguation service is new
        as of 0.9.4.

        .. versionadded:: 0.6.4

        """
        if conv:
            return conv(name)
        else:
            raise NotImplementedError(
                "op.f() feature requires SQLAlchemy 0.9.4 or greater.")

    def add_column(self, table_name, column, schema=None):
        """Issue an "add column" instruction using the current
        migration context.

        e.g.::

            from alembic import op
            from sqlalchemy import Column, String

            op.add_column('organization',
                Column('name', String())
            )

        The provided :class:`~sqlalchemy.schema.Column` object can also
        specify a :class:`~sqlalchemy.schema.ForeignKey`, referencing
        a remote table name.  Alembic will automatically generate a stub
        "referenced" table and emit a second ALTER statement in order
        to add the constraint separately::

            from alembic import op
            from sqlalchemy import Column, INTEGER, ForeignKey

            op.add_column('organization',
                Column('account_id', INTEGER, ForeignKey('accounts.id'))
            )

        Note that this statement uses the :class:`~sqlalchemy.schema.Column`
        construct as is from the SQLAlchemy library.  In particular,
        default values to be created on the database side are
        specified using the ``server_default`` parameter, and not
        ``default`` which only specifies Python-side defaults::

            from alembic import op
            from sqlalchemy import Column, TIMESTAMP, func

            # specify "DEFAULT NOW" along with the column add
            op.add_column('account',
                Column('timestamp', TIMESTAMP, server_default=func.now())
            )

        :param table_name: String name of the parent table.
        :param column: a :class:`sqlalchemy.schema.Column` object
         representing the new column.
        :param schema: Optional schema name to operate within.  To control
         quoting of the schema outside of the default behavior, use
         the SQLAlchemy construct
         :class:`~sqlalchemy.sql.elements.quoted_name`.

         .. versionadded:: 0.7.0 'schema' can now accept a
            :class:`~sqlalchemy.sql.elements.quoted_name` construct.


        """

        t = self.schema_obj.table(table_name, column, schema=schema)
        self.impl.add_column(
            table_name,
            column,
            schema=schema
        )
        for constraint in t.constraints:
            if not isinstance(constraint, sa_schema.PrimaryKeyConstraint):
                self.impl.add_constraint(constraint)
        for index in t.indexes:
            self.impl._exec(sa_schema.CreateIndex(index))

    def drop_column(self, table_name, column_name, schema=None, **kw):
        """Issue a "drop column" instruction using the current
        migration context.

        e.g.::

            drop_column('organization', 'account_id')

        :param table_name: name of table
        :param column_name: name of column
        :param schema: Optional schema name to operate within.  To control
         quoting of the schema outside of the default behavior, use
         the SQLAlchemy construct
         :class:`~sqlalchemy.sql.elements.quoted_name`.

         .. versionadded:: 0.7.0 'schema' can now accept a
            :class:`~sqlalchemy.sql.elements.quoted_name` construct.

        :param mssql_drop_check: Optional boolean.  When ``True``, on
         Microsoft SQL Server only, first
         drop the CHECK constraint on the column using a
         SQL-script-compatible
         block that selects into a @variable from sys.check_constraints,
         then exec's a separate DROP CONSTRAINT for that constraint.
        :param mssql_drop_default: Optional boolean.  When ``True``, on
         Microsoft SQL Server only, first
         drop the DEFAULT constraint on the column using a
         SQL-script-compatible
         block that selects into a @variable from sys.default_constraints,
         then exec's a separate DROP CONSTRAINT for that default.
        :param mssql_drop_foreign_key: Optional boolean.  When ``True``, on
         Microsoft SQL Server only, first
         drop a single FOREIGN KEY constraint on the column using a
         SQL-script-compatible
         block that selects into a @variable from
         sys.foreign_keys/sys.foreign_key_columns,
         then exec's a separate DROP CONSTRAINT for that default.  Only
         works if the column has exactly one FK constraint which refers to
         it, at the moment.

         .. versionadded:: 0.6.2

        """

        op = ops.DropColumnOp(table_name, column_name, schema=schema)
        return self.invoke(op)

    @util._with_legacy_names([('name', 'constraint_name')])
    def create_primary_key(
            self, constraint_name, table_name, columns, schema=None):
        """Issue a "create primary key" instruction using the current
        migration context.

        e.g.::

            from alembic import op
            op.create_primary_key(
                        "pk_my_table", "my_table",
                        ["id", "version"]
                    )

        This internally generates a :class:`~sqlalchemy.schema.Table` object
        containing the necessary columns, then generates a new
        :class:`~sqlalchemy.schema.PrimaryKeyConstraint`
        object which it then associates with the
        :class:`~sqlalchemy.schema.Table`.
        Any event listeners associated with this action will be fired
        off normally.   The :class:`~sqlalchemy.schema.AddConstraint`
        construct is ultimately used to generate the ALTER statement.

        :param name: Name of the primary key constraint.  The name is necessary
         so that an ALTER statement can be emitted.  For setups that
         use an automated naming scheme such as that described at
         :ref:`sqla:constraint_naming_conventions`
         ``name`` here can be ``None``, as the event listener will
         apply the name to the constraint object when it is associated
         with the table.
        :param table_name: String name of the target table.
        :param columns: a list of string column names to be applied to the
         primary key constraint.
        :param schema: Optional schema name to operate within.  To control
         quoting of the schema outside of the default behavior, use
         the SQLAlchemy construct
         :class:`~sqlalchemy.sql.elements.quoted_name`.

         .. versionadded:: 0.7.0 'schema' can now accept a
            :class:`~sqlalchemy.sql.elements.quoted_name` construct.

        """
        self.impl.add_constraint(
            self.schema_obj.primary_key_constraint(
                constraint_name, table_name, columns, schema)
        )

    @util._with_legacy_names([('name', 'constraint_name')])
    def create_foreign_key(self, constraint_name, source, referent, local_cols,
                           remote_cols, onupdate=None, ondelete=None,
                           deferrable=None, initially=None, match=None,
                           source_schema=None, referent_schema=None,
                           **dialect_kw):
        """Issue a "create foreign key" instruction using the
        current migration context.

        e.g.::

            from alembic import op
            op.create_foreign_key(
                        "fk_user_address", "address",
                        "user", ["user_id"], ["id"])

        This internally generates a :class:`~sqlalchemy.schema.Table` object
        containing the necessary columns, then generates a new
        :class:`~sqlalchemy.schema.ForeignKeyConstraint`
        object which it then associates with the
        :class:`~sqlalchemy.schema.Table`.
        Any event listeners associated with this action will be fired
        off normally.   The :class:`~sqlalchemy.schema.AddConstraint`
        construct is ultimately used to generate the ALTER statement.

        :param name: Name of the foreign key constraint.  The name is necessary
         so that an ALTER statement can be emitted.  For setups that
         use an automated naming scheme such as that described at
         :ref:`sqla:constraint_naming_conventions`,
         ``name`` here can be ``None``, as the event listener will
         apply the name to the constraint object when it is associated
         with the table.
        :param source: String name of the source table.
        :param referent: String name of the destination table.
        :param local_cols: a list of string column names in the
         source table.
        :param remote_cols: a list of string column names in the
         remote table.
        :param onupdate: Optional string. If set, emit ON UPDATE <value> when
         issuing DDL for this constraint. Typical values include CASCADE,
         DELETE and RESTRICT.
        :param ondelete: Optional string. If set, emit ON DELETE <value> when
         issuing DDL for this constraint. Typical values include CASCADE,
         DELETE and RESTRICT.
        :param deferrable: optional bool. If set, emit DEFERRABLE or NOT
         DEFERRABLE when issuing DDL for this constraint.
        :param source_schema: Optional schema name of the source table.
        :param referent_schema: Optional schema name of the destination table.

        """

        self.impl.add_constraint(
            self.schema_obj.foreign_key_constraint(
                constraint_name, source, referent,
                local_cols, remote_cols,
                onupdate=onupdate, ondelete=ondelete,
                deferrable=deferrable,
                source_schema=source_schema,
                referent_schema=referent_schema,
                initially=initially, match=match,
                **dialect_kw)
        )

    @util._with_legacy_names([
        ('name', 'constraint_name'),
        ('source', 'table_name')
    ])
    def create_unique_constraint(self, constraint_name, table_name, columns,
                                 schema=None, **kw):
        """Issue a "create unique constraint" instruction using the
        current migration context.

        e.g.::

            from alembic import op
            op.create_unique_constraint("uq_user_name", "user", ["name"])

        This internally generates a :class:`~sqlalchemy.schema.Table` object
        containing the necessary columns, then generates a new
        :class:`~sqlalchemy.schema.UniqueConstraint`
        object which it then associates with the
        :class:`~sqlalchemy.schema.Table`.
        Any event listeners associated with this action will be fired
        off normally.   The :class:`~sqlalchemy.schema.AddConstraint`
        construct is ultimately used to generate the ALTER statement.

        :param name: Name of the unique constraint.  The name is necessary
         so that an ALTER statement can be emitted.  For setups that
         use an automated naming scheme such as that described at
         :ref:`sqla:constraint_naming_conventions`,
         ``name`` here can be ``None``, as the event listener will
         apply the name to the constraint object when it is associated
         with the table.
        :param table_name: String name of the source table.
        :param columns: a list of string column names in the
         source table.
        :param deferrable: optional bool. If set, emit DEFERRABLE or
         NOT DEFERRABLE when issuing DDL for this constraint.
        :param initially: optional string. If set, emit INITIALLY <value>
         when issuing DDL for this constraint.
        :param schema: Optional schema name to operate within.  To control
         quoting of the schema outside of the default behavior, use
         the SQLAlchemy construct
         :class:`~sqlalchemy.sql.elements.quoted_name`.

         .. versionadded:: 0.7.0 'schema' can now accept a
            :class:`~sqlalchemy.sql.elements.quoted_name` construct.

        """

        self.impl.add_constraint(
            self.schema_obj.unique_constraint(
                constraint_name, table_name, columns,
                schema=schema, **kw)
        )

    @util._with_legacy_names([
        ('name', 'constraint_name'),
        ('source', 'table_name')
    ])
    def create_check_constraint(self, constraint_name, table_name, condition,
                                schema=None, **kw):
        """Issue a "create check constraint" instruction using the
        current migration context.

        e.g.::

            from alembic import op
            from sqlalchemy.sql import column, func

            op.create_check_constraint(
                "ck_user_name_len",
                "user",
                func.len(column('name')) > 5
            )

        CHECK constraints are usually against a SQL expression, so ad-hoc
        table metadata is usually needed.   The function will convert the given
        arguments into a :class:`sqlalchemy.schema.CheckConstraint` bound
        to an anonymous table in order to emit the CREATE statement.

        :param name: Name of the check constraint.  The name is necessary
         so that an ALTER statement can be emitted.  For setups that
         use an automated naming scheme such as that described at
         :ref:`sqla:constraint_naming_conventions`,
         ``name`` here can be ``None``, as the event listener will
         apply the name to the constraint object when it is associated
         with the table.
        :param table_name: String name of the source table.
        :param condition: SQL expression that's the condition of the
         constraint. Can be a string or SQLAlchemy expression language
         structure.
        :param deferrable: optional bool. If set, emit DEFERRABLE or
         NOT DEFERRABLE when issuing DDL for this constraint.
        :param initially: optional string. If set, emit INITIALLY <value>
         when issuing DDL for this constraint.
        :param schema: Optional schema name to operate within.  To control
         quoting of the schema outside of the default behavior, use
         the SQLAlchemy construct
         :class:`~sqlalchemy.sql.elements.quoted_name`.

         .. versionadded:: 0.7.0 'schema' can now accept a
            :class:`~sqlalchemy.sql.elements.quoted_name` construct.

        """
        self.impl.add_constraint(
            self.schema_obj.check_constraint(
                constraint_name, table_name, condition, schema=schema, **kw)
        )

    @util._with_legacy_names([('name', 'table_name')])
    def create_table(self, table_name, *columns, **kw):
        """Issue a "create table" instruction using the current migration
        context.

        This directive receives an argument list similar to that of the
        traditional :class:`sqlalchemy.schema.Table` construct, but without the
        metadata::

            from sqlalchemy import INTEGER, VARCHAR, NVARCHAR, Column
            from alembic import op

            op.create_table(
                'account',
                Column('id', INTEGER, primary_key=True),
                Column('name', VARCHAR(50), nullable=False),
                Column('description', NVARCHAR(200)),
                Column('timestamp', TIMESTAMP, server_default=func.now())
            )

        Note that :meth:`.create_table` accepts
        :class:`~sqlalchemy.schema.Column`
        constructs directly from the SQLAlchemy library.  In particular,
        default values to be created on the database side are
        specified using the ``server_default`` parameter, and not
        ``default`` which only specifies Python-side defaults::

            from alembic import op
            from sqlalchemy import Column, TIMESTAMP, func

            # specify "DEFAULT NOW" along with the "timestamp" column
            op.create_table('account',
                Column('id', INTEGER, primary_key=True),
                Column('timestamp', TIMESTAMP, server_default=func.now())
            )

        The function also returns a newly created
        :class:`~sqlalchemy.schema.Table` object, corresponding to the table
        specification given, which is suitable for
        immediate SQL operations, in particular
        :meth:`.Operations.bulk_insert`::

            from sqlalchemy import INTEGER, VARCHAR, NVARCHAR, Column
            from alembic import op

            account_table = op.create_table(
                'account',
                Column('id', INTEGER, primary_key=True),
                Column('name', VARCHAR(50), nullable=False),
                Column('description', NVARCHAR(200)),
                Column('timestamp', TIMESTAMP, server_default=func.now())
            )

            op.bulk_insert(
                account_table,
                [
                    {"name": "A1", "description": "account 1"},
                    {"name": "A2", "description": "account 2"},
                ]
            )

        .. versionadded:: 0.7.0

        :param table_name: Name of the table
        :param \*columns: collection of :class:`~sqlalchemy.schema.Column`
         objects within
         the table, as well as optional :class:`~sqlalchemy.schema.Constraint`
         objects
         and :class:`~.sqlalchemy.schema.Index` objects.
        :param schema: Optional schema name to operate within.  To control
         quoting of the schema outside of the default behavior, use
         the SQLAlchemy construct
         :class:`~sqlalchemy.sql.elements.quoted_name`.

         .. versionadded:: 0.7.0 'schema' can now accept a
            :class:`~sqlalchemy.sql.elements.quoted_name` construct.
        :param \**kw: Other keyword arguments are passed to the underlying
         :class:`sqlalchemy.schema.Table` object created for the command.

        :return: the :class:`~sqlalchemy.schema.Table` object corresponding
         to the parameters given.

         .. versionadded:: 0.7.0 - the :class:`~sqlalchemy.schema.Table`
            object is returned.

        """
        table = self.schema_obj.table(table_name, *columns, **kw)
        self.impl.create_table(table)
        return table

    @util._with_legacy_names([('name', 'table_name')])
    def drop_table(self, table_name, schema=None, **kw):
        """Issue a "drop table" instruction using the current
        migration context.


        e.g.::

            drop_table("accounts")

        :param table_name: Name of the table
        :param schema: Optional schema name to operate within.  To control
         quoting of the schema outside of the default behavior, use
         the SQLAlchemy construct
         :class:`~sqlalchemy.sql.elements.quoted_name`.

         .. versionadded:: 0.7.0 'schema' can now accept a
            :class:`~sqlalchemy.sql.elements.quoted_name` construct.

        :param \**kw: Other keyword arguments are passed to the underlying
         :class:`sqlalchemy.schema.Table` object created for the command.

        """
        op = ops.DropTableOp(
            table_name, schema=schema, table_kw=kw
        )
        self.invoke(op)

    @util._with_legacy_names([('name', 'index_name')])
    def create_index(self, index_name, table_name, columns, schema=None,
                     unique=False, quote=None, **kw):
        """Issue a "create index" instruction using the current
        migration context.

        e.g.::

            from alembic import op
            op.create_index('ik_test', 't1', ['foo', 'bar'])

        Functional indexes can be produced by using the
        :func:`sqlalchemy.sql.expression.text` construct::

            from alembic import op
            from sqlalchemy import text
            op.create_index('ik_test', 't1', [text('lower(foo)')])

        .. versionadded:: 0.6.7 support for making use of the
           :func:`~sqlalchemy.sql.expression.text` construct in
           conjunction with
           :meth:`.Operations.create_index` in
           order to produce functional expressions within CREATE INDEX.

        :param index_name: name of the index.
        :param table_name: name of the owning table.
        :param columns: a list consisting of string column names and/or
         :func:`~sqlalchemy.sql.expression.text` constructs.
        :param schema: Optional schema name to operate within.  To control
         quoting of the schema outside of the default behavior, use
         the SQLAlchemy construct
         :class:`~sqlalchemy.sql.elements.quoted_name`.

         .. versionadded:: 0.7.0 'schema' can now accept a
            :class:`~sqlalchemy.sql.elements.quoted_name` construct.

        :param unique: If True, create a unique index.

        :param quote:
            Force quoting of this column's name on or off, corresponding
            to ``True`` or ``False``. When left at its default
            of ``None``, the column identifier will be quoted according to
            whether the name is case sensitive (identifiers with at least one
            upper case character are treated as case sensitive), or if it's a
            reserved word. This flag is only needed to force quoting of a
            reserved word which is not known by the SQLAlchemy dialect.

        :param \**kw: Additional keyword arguments not mentioned above are
            dialect specific, and passed in the form ``<dialectname>_<argname>``.
            See the documentation regarding an individual dialect at
            :ref:`dialect_toplevel` for detail on documented arguments.
        """
        op = ops.CreateIndex(
            index_name, table_name, columns, schema=schema,
            unique=unique, quote=quote, **kw
        )
        return self.invoke(op)

    @util._with_legacy_names([('tablename', 'table_name')])
    @util._with_legacy_names([('name', 'index_name')])
    def drop_index(self, index_name, table_name=None, schema=None):
        """Issue a "drop index" instruction using the current
        migration context.

        e.g.::

            drop_index("accounts")

        :param index_name: name of the index.
        :param table_name: name of the owning table.  Some
         backends such as Microsoft SQL Server require this.
        :param schema: Optional schema name to operate within.  To control
         quoting of the schema outside of the default behavior, use
         the SQLAlchemy construct
         :class:`~sqlalchemy.sql.elements.quoted_name`.

         .. versionadded:: 0.7.0 'schema' can now accept a
            :class:`~sqlalchemy.sql.elements.quoted_name` construct.

        """
        # need a dummy column name here since SQLAlchemy
        # 0.7.6 and further raises on Index with no columns
        self.impl.drop_index(
            self.schema_obj.index(index_name, table_name, ['x'], schema=schema)
        )

    @util._with_legacy_names([("type", "type_")])
    def drop_constraint(self, name, table_name, type_=None, schema=None):
        """Drop a constraint of the given name, typically via DROP CONSTRAINT.

        :param name: name of the constraint.
        :param table_name: table name.
        :param ``type_``: optional, required on MySQL.  can be
         'foreignkey', 'primary', 'unique', or 'check'.
        :param schema: Optional schema name to operate within.  To control
         quoting of the schema outside of the default behavior, use
         the SQLAlchemy construct
         :class:`~sqlalchemy.sql.elements.quoted_name`.

         .. versionadded:: 0.7.0 'schema' can now accept a
            :class:`~sqlalchemy.sql.elements.quoted_name` construct.

        """

        t = self.schema_obj.table(table_name, schema=schema)
        types = {
            'foreignkey': lambda name: sa_schema.ForeignKeyConstraint(
                [], [], name=name),
            'primary': sa_schema.PrimaryKeyConstraint,
            'unique': sa_schema.UniqueConstraint,
            'check': lambda name: sa_schema.CheckConstraint("", name=name),
            None: sa_schema.Constraint
        }
        try:
            const = types[type_]
        except KeyError:
            raise TypeError("'type' can be one of %s" %
                            ", ".join(sorted(repr(x) for x in types)))

        const = const(name=name)
        t.append_constraint(const)
        self.impl.drop_constraint(const)

    def bulk_insert(self, table, rows, multiinsert=True):
        """Issue a "bulk insert" operation using the current
        migration context.

        This provides a means of representing an INSERT of multiple rows
        which works equally well in the context of executing on a live
        connection as well as that of generating a SQL script.   In the
        case of a SQL script, the values are rendered inline into the
        statement.

        e.g.::

            from alembic import op
            from datetime import date
            from sqlalchemy.sql import table, column
            from sqlalchemy import String, Integer, Date

            # Create an ad-hoc table to use for the insert statement.
            accounts_table = table('account',
                column('id', Integer),
                column('name', String),
                column('create_date', Date)
            )

            op.bulk_insert(accounts_table,
                [
                    {'id':1, 'name':'John Smith',
                            'create_date':date(2010, 10, 5)},
                    {'id':2, 'name':'Ed Williams',
                            'create_date':date(2007, 5, 27)},
                    {'id':3, 'name':'Wendy Jones',
                            'create_date':date(2008, 8, 15)},
                ]
            )

        When using --sql mode, some datatypes may not render inline
        automatically, such as dates and other special types.   When this
        issue is present, :meth:`.Operations.inline_literal` may be used::

            op.bulk_insert(accounts_table,
                [
                    {'id':1, 'name':'John Smith',
                            'create_date':op.inline_literal("2010-10-05")},
                    {'id':2, 'name':'Ed Williams',
                            'create_date':op.inline_literal("2007-05-27")},
                    {'id':3, 'name':'Wendy Jones',
                            'create_date':op.inline_literal("2008-08-15")},
                ],
                multiinsert=False
            )

        When using :meth:`.Operations.inline_literal` in conjunction with
        :meth:`.Operations.bulk_insert`, in order for the statement to work
        in "online" (e.g. non --sql) mode, the
        :paramref:`~.Operations.bulk_insert.multiinsert`
        flag should be set to ``False``, which will have the effect of
        individual INSERT statements being emitted to the database, each
        with a distinct VALUES clause, so that the "inline" values can
        still be rendered, rather than attempting to pass the values
        as bound parameters.

        .. versionadded:: 0.6.4 :meth:`.Operations.inline_literal` can now
           be used with :meth:`.Operations.bulk_insert`, and the
           :paramref:`~.Operations.bulk_insert.multiinsert` flag has
           been added to assist in this usage when running in "online"
           mode.

        :param table: a table object which represents the target of the INSERT.

        :param rows: a list of dictionaries indicating rows.

        :param multiinsert: when at its default of True and --sql mode is not
           enabled, the INSERT statement will be executed using
           "executemany()" style, where all elements in the list of
           dictionaries are passed as bound parameters in a single
           list.   Setting this to False results in individual INSERT
           statements being emitted per parameter set, and is needed
           in those cases where non-literal values are present in the
           parameter sets.

           .. versionadded:: 0.6.4

          """
        self.impl.bulk_insert(table, rows, multiinsert=multiinsert)

    def inline_literal(self, value, type_=None):
        """Produce an 'inline literal' expression, suitable for
        using in an INSERT, UPDATE, or DELETE statement.

        When using Alembic in "offline" mode, CRUD operations
        aren't compatible with SQLAlchemy's default behavior surrounding
        literal values,
        which is that they are converted into bound values and passed
        separately into the ``execute()`` method of the DBAPI cursor.
        An offline SQL
        script needs to have these rendered inline.  While it should
        always be noted that inline literal values are an **enormous**
        security hole in an application that handles untrusted input,
        a schema migration is not run in this context, so
        literals are safe to render inline, with the caveat that
        advanced types like dates may not be supported directly
        by SQLAlchemy.

        See :meth:`.execute` for an example usage of
        :meth:`.inline_literal`.

        The environment can also be configured to attempt to render
        "literal" values inline automatically, for those simple types
        that are supported by the dialect; see
        :paramref:`.EnvironmentContext.configure.literal_binds` for this
        more recently added feature.

        :param value: The value to render.  Strings, integers, and simple
         numerics should be supported.   Other types like boolean,
         dates, etc. may or may not be supported yet by various
         backends.
        :param ``type_``: optional - a :class:`sqlalchemy.types.TypeEngine`
         subclass stating the type of this value.  In SQLAlchemy
         expressions, this is usually derived automatically
         from the Python type of the value itself, as well as
         based on the context in which the value is used.

        .. seealso::

            :paramref:`.EnvironmentContext.configure.literal_binds`

        """
        return sqla_compat._literal_bindparam(None, value, type_=type_)

    def execute(self, sql, execution_options=None):
        """Execute the given SQL using the current migration context.

        In a SQL script context, the statement is emitted directly to the
        output stream.   There is *no* return result, however, as this
        function is oriented towards generating a change script
        that can run in "offline" mode.  For full interaction
        with a connected database, use the "bind" available
        from the context::

            from alembic import op
            connection = op.get_bind()

        Also note that any parameterized statement here *will not work*
        in offline mode - INSERT, UPDATE and DELETE statements which refer
        to literal values would need to render
        inline expressions.   For simple use cases, the
        :meth:`.inline_literal` function can be used for **rudimentary**
        quoting of string values.  For "bulk" inserts, consider using
        :meth:`.bulk_insert`.

        For example, to emit an UPDATE statement which is equally
        compatible with both online and offline mode::

            from sqlalchemy.sql import table, column
            from sqlalchemy import String
            from alembic import op

            account = table('account',
                column('name', String)
            )
            op.execute(
                account.update().\\
                    where(account.c.name==op.inline_literal('account 1')).\\
                    values({'name':op.inline_literal('account 2')})
                    )

        Note above we also used the SQLAlchemy
        :func:`sqlalchemy.sql.expression.table`
        and :func:`sqlalchemy.sql.expression.column` constructs to
        make a brief, ad-hoc table construct just for our UPDATE
        statement.  A full :class:`~sqlalchemy.schema.Table` construct
        of course works perfectly fine as well, though note it's a
        recommended practice to at least ensure the definition of a
        table is self-contained within the migration script, rather
        than imported from a module that may break compatibility with
        older migrations.

        :param sql: Any legal SQLAlchemy expression, including:

        * a string
        * a :func:`sqlalchemy.sql.expression.text` construct.
        * a :func:`sqlalchemy.sql.expression.insert` construct.
        * a :func:`sqlalchemy.sql.expression.update`,
          :func:`sqlalchemy.sql.expression.insert`,
          or :func:`sqlalchemy.sql.expression.delete`  construct.
        * Pretty much anything that's "executable" as described
          in :ref:`sqlexpression_toplevel`.

        :param execution_options: Optional dictionary of
         execution options, will be passed to
         :meth:`sqlalchemy.engine.Connection.execution_options`.
        """
        self.migration_context.impl.execute(
            sql,
            execution_options=execution_options)

    def get_bind(self):
        """Return the current 'bind'.

        Under normal circumstances, this is the
        :class:`~sqlalchemy.engine.Connection` currently being used
        to emit SQL to the database.

        In a SQL script context, this value is ``None``. [TODO: verify this]

        """
        return self.migration_context.impl.bind


class BatchOperations(Operations):
    """Modifies the interface :class:`.Operations` for batch mode.

    This basically omits the ``table_name`` and ``schema`` parameters
    from associated methods, as these are a given when running under batch
    mode.

    .. seealso::

        :meth:`.Operations.batch_alter_table`

    """

    def _noop(self, operation):
        raise NotImplementedError(
            "The %s method does not apply to a batch table alter operation."
            % operation)

    def add_column(self, column):
        """Issue an "add column" instruction using the current
        batch migration context.

        .. seealso::

            :meth:`.Operations.add_column`

        """

        return super(BatchOperations, self).add_column(
            self.impl.table_name, column, schema=self.impl.schema)

    def alter_column(self, column_name, **kw):
        """Issue an "alter column" instruction using the current
        batch migration context.

        .. seealso::

            :meth:`.Operations.add_column`

        """
        kw['schema'] = self.impl.schema
        return super(BatchOperations, self).alter_column(
            self.impl.table_name, column_name, **kw)

    def drop_column(self, column_name):
        """Issue a "drop column" instruction using the current
        batch migration context.

        .. seealso::

            :meth:`.Operations.drop_column`

        """
        return super(BatchOperations, self).drop_column(
            self.impl.table_name, column_name, schema=self.impl.schema)

    def create_primary_key(self, constraint_name, columns):
        """Issue a "create primary key" instruction using the
        current batch migration context.

        The batch form of this call omits the ``table_name`` and ``schema``
        arguments from the call.

        .. seealso::

            :meth:`.Operations.create_primary_key`

        """
        raise NotImplementedError("not yet implemented")

    @util._with_legacy_names([('name', 'constraint_name')])
    def create_foreign_key(
            self, constraint_name, referent, local_cols, remote_cols, **kw):
        """Issue a "create foreign key" instruction using the
        current batch migration context.

        The batch form of this call omits the ``source`` and ``source_schema``
        arguments from the call.

        e.g.::

            with batch_alter_table("address") as batch_op:
                batch_op.create_foreign_key(
                            "fk_user_address",
                            "user", ["user_id"], ["id"])

        .. seealso::

            :meth:`.Operations.create_foreign_key`

        """
        return super(BatchOperations, self).create_foreign_key(
            constraint_name, self.impl.table_name, referent,
            local_cols, remote_cols,
            source_schema=self.impl.schema, **kw)

    @util._with_legacy_names([('name', 'constraint_name')])
    def create_unique_constraint(self, constraint_name, local_cols, **kw):
        """Issue a "create unique constraint" instruction using the
        current batch migration context.

        The batch form of this call omits the ``source`` and ``schema``
        arguments from the call.

        .. seealso::

            :meth:`.Operations.create_unique_constraint`

        """
        kw['schema'] = self.impl.schema
        return super(BatchOperations, self).create_unique_constraint(
            constraint_name, self.impl.table_name, local_cols, **kw)

    @util._with_legacy_names([('name', 'constraint_name')])
    def create_check_constraint(self, constraint_name, condition, **kw):
        """Issue a "create check constraint" instruction using the
        current batch migration context.

        The batch form of this call omits the ``source`` and ``schema``
        arguments from the call.

        .. seealso::

            :meth:`.Operations.create_check_constraint`

        """
        raise NotImplementedError("not yet implemented")

    def drop_constraint(self, name, type_=None):
        """Issue a "drop constraint" instruction using the
        current batch migration context.

        The batch form of this call omits the ``table_name`` and ``schema``
        arguments from the call.

        .. seealso::

            :meth:`.Operations.drop_constraint`

        """
        return super(BatchOperations, self).drop_constraint(
            name, self.impl.table_name, type_=type_,
            schema=self.impl.schema)

    def create_index(self, index_name, columns, **kw):
        """Issue a "create index" instruction using the
        current batch migration context."""

        kw['schema'] = self.impl.schema

        return super(BatchOperations, self).create_index(
            index_name, self.impl.table_name, columns, **kw)

    def drop_index(self, name, **kw):
        """Issue a "drop index" instruction using the
        current batch migration context."""

        kw['schema'] = self.impl.schema

        return super(BatchOperations, self).drop_index(
            name, self.impl.table_name, **kw)
