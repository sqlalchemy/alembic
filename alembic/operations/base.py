from contextlib import contextmanager

from .. import util
from ..util import sqla_compat
from . import batch
from . import schemaobj
from ..util.compat import exec_
import textwrap
import inspect

__all__ = ('Operations', 'BatchOperations')

try:
    from sqlalchemy.sql.naming import conv
except:
    conv = None


class Operations(util.ModuleClsProxy):

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

    _to_impl = util.Dispatcher()

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
    def register_operation(cls, name):
        def register(op_cls):

            fn = getattr(op_cls, name)

            spec = inspect.getargspec(fn)

            name_args = spec[0]
            assert name_args[0:2] == ['cls', 'operations']

            name_args[0:2] = ['self']

            args = inspect.formatargspec(*spec)
            num_defaults = len(spec[3]) if spec[3] else 0
            if num_defaults:
                defaulted_vals = name_args[0 - num_defaults:]
            else:
                defaulted_vals = ()

            apply_kw = inspect.formatargspec(
                name_args, spec[1], spec[2],
                defaulted_vals,
                formatvalue=lambda x: '=' + x)

            func_text = textwrap.dedent("""\
            def %(name)s%(args)s:
                %(doc)r
                return op_cls.%(name)s%(apply_kw)s
            """ % {
                'name': name,
                'args': args,
                'apply_kw': apply_kw,
                'doc': fn.__doc__,
                'meth': fn.__name__
            })
            globals_ = {'op_cls': op_cls}
            lcl = {}
            exec_(func_text, globals_, lcl)
            setattr(cls, name, lcl[name])
            return op_cls
        return register

    @classmethod
    def implementation_for(cls, op_cls):
        def decorate(fn):
            cls._to_impl.dispatch_for(op_cls)(fn)
            return fn
        return decorate

    @classmethod
    @contextmanager
    def context(cls, migration_context):
        op = Operations(migration_context)
        op._install_proxy()
        yield op
        op._remove_proxy()

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

    def invoke(self, operation):
        fn = self._to_impl.dispatch(
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

    def execute(self, sqltext, execution_options=None):
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
            sqltext,
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
