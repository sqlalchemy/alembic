from contextlib import contextmanager

from sqlalchemy.types import NULLTYPE, Integer
from sqlalchemy import schema as sa_schema

from . import util
from .compat import string_types
from .ddl import impl

__all__ = ('Operations',)

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
    def __init__(self, migration_context):
        """Construct a new :class:`.Operations`

        :param migration_context: a :class:`.MigrationContext`
         instance.

        """
        self.migration_context = migration_context
        self.impl = migration_context.impl

    @classmethod
    @contextmanager
    def context(cls, migration_context):
        from .op import _install_proxy, _remove_proxy
        op = Operations(migration_context)
        _install_proxy(op)
        yield op
        _remove_proxy()


    def _primary_key_constraint(self, name, table_name, cols, schema=None):
        m = self._metadata()
        columns = [sa_schema.Column(n, NULLTYPE) for n in cols]
        t1 = sa_schema.Table(table_name, m,
                *columns,
                schema=schema)
        p = sa_schema.PrimaryKeyConstraint(*columns, name=name)
        t1.append_constraint(p)
        return p

    def _foreign_key_constraint(self, name, source, referent,
                                    local_cols, remote_cols,
                                    onupdate=None, ondelete=None,
                                    deferrable=None, source_schema=None,
                                    referent_schema=None, initially=None,
                                    match=None, **dialect_kw):
        m = self._metadata()
        if source == referent:
            t1_cols = local_cols + remote_cols
        else:
            t1_cols = local_cols
            sa_schema.Table(referent, m,
                    *[sa_schema.Column(n, NULLTYPE) for n in remote_cols],
                    schema=referent_schema)

        t1 = sa_schema.Table(source, m,
                *[sa_schema.Column(n, NULLTYPE) for n in t1_cols],
                schema=source_schema)

        tname = "%s.%s" % (referent_schema, referent) if referent_schema \
                else referent
        f = sa_schema.ForeignKeyConstraint(local_cols,
                                            ["%s.%s" % (tname, n)
                                            for n in remote_cols],
                                            name=name,
                                            onupdate=onupdate,
                                            ondelete=ondelete,
                                            deferrable=deferrable,
                                            initially=initially,
                                            match=match,
                                            **dialect_kw
                                            )
        t1.append_constraint(f)

        return f

    def _unique_constraint(self, name, source, local_cols, schema=None, **kw):
        t = sa_schema.Table(source, self._metadata(),
                    *[sa_schema.Column(n, NULLTYPE) for n in local_cols],
                    schema=schema)
        kw['name'] = name
        uq = sa_schema.UniqueConstraint(*[t.c[n] for n in local_cols], **kw)
        # TODO: need event tests to ensure the event
        # is fired off here
        t.append_constraint(uq)
        return uq

    def _check_constraint(self, name, source, condition, schema=None, **kw):
        t = sa_schema.Table(source, self._metadata(),
                    sa_schema.Column('x', Integer), schema=schema)
        ck = sa_schema.CheckConstraint(condition, name=name, **kw)
        t.append_constraint(ck)
        return ck

    def _metadata(self):
        kw = {}
        if 'target_metadata' in self.migration_context.opts:
            mt = self.migration_context.opts['target_metadata']
            if hasattr(mt, 'naming_convention'):
                kw['naming_convention'] = mt.naming_convention
        return sa_schema.MetaData(**kw)

    def _table(self, name, *columns, **kw):
        m = self._metadata()
        t = sa_schema.Table(name, m, *columns, **kw)
        for f in t.foreign_keys:
            self._ensure_table_for_fk(m, f)
        return t

    def _column(self, name, type_, **kw):
        return sa_schema.Column(name, type_, **kw)

    def _index(self, name, tablename, columns, schema=None, **kw):
        t = sa_schema.Table(tablename or 'no_table', self._metadata(),
            *[sa_schema.Column(n, NULLTYPE) for n in columns],
            schema=schema
        )
        return sa_schema.Index(name, *[t.c[n] for n in columns], **kw)

    def _parse_table_key(self, table_key):
        if '.' in table_key:
            tokens = table_key.split('.')
            sname = ".".join(tokens[0:-1])
            tname = tokens[-1]
        else:
            tname = table_key
            sname = None
        return (sname, tname)

    def _ensure_table_for_fk(self, metadata, fk):
        """create a placeholder Table object for the referent of a
        ForeignKey.

        """
        if isinstance(fk._colspec, string_types):
            table_key, cname = fk._colspec.rsplit('.', 1)
            sname, tname = self._parse_table_key(table_key)
            if table_key not in metadata.tables:
                rel_t = sa_schema.Table(tname, metadata, schema=sname)
            else:
                rel_t = metadata.tables[table_key]
            if cname not in rel_t.c:
                rel_t.append_column(sa_schema.Column(cname, NULLTYPE))

    def get_context(self):
        """Return the :class:`.MigrationContext` object that's
        currently in use.

        """

        return self.migration_context

    def rename_table(self, old_table_name, new_table_name, schema=None):
        """Emit an ALTER TABLE to rename a table.

        :param old_table_name: old name.
        :param new_table_name: new name.
        :param schema: Optional schema name to operate within.

        """
        self.impl.rename_table(
            old_table_name,
            new_table_name,
            schema=schema
        )

    @util._with_legacy_names([('name', 'new_column_name')])
    def alter_column(self, table_name, column_name,
                        nullable=None,
                        server_default=False,
                        new_column_name=None,
                        type_=None,
                        autoincrement=None,
                        existing_type=None,
                        existing_server_default=False,
                        existing_nullable=None,
                        existing_autoincrement=None,
                        schema=None
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

         .. versionchanged:: 0.5.0
            The ``name`` parameter is now named ``new_column_name``.
            The old name will continue to function for backwards
            compatibility.

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
        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        """

        compiler = self.impl.dialect.statement_compiler(
                            self.impl.dialect,
                            None
                        )
        def _count_constraint(constraint):
            return not isinstance(constraint, sa_schema.PrimaryKeyConstraint) and \
                (not constraint._create_rule or
                    constraint._create_rule(compiler))

        if existing_type and type_:
            t = self._table(table_name,
                        sa_schema.Column(column_name, existing_type),
                        schema=schema
                    )
            for constraint in t.constraints:
                if _count_constraint(constraint):
                    self.impl.drop_constraint(constraint)

        self.impl.alter_column(table_name, column_name,
            nullable=nullable,
            server_default=server_default,
            name=new_column_name,
            type_=type_,
            schema=schema,
            autoincrement=autoincrement,
            existing_type=existing_type,
            existing_server_default=existing_server_default,
            existing_nullable=existing_nullable,
            existing_autoincrement=existing_autoincrement
        )

        if type_:
            t = self._table(table_name,
                        sa_schema.Column(column_name, type_),
                        schema=schema
                    )
            for constraint in t.constraints:
                if _count_constraint(constraint):
                    self.impl.add_constraint(constraint)

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

        Above, the CHECK constraint generated will have the name ``ck_bool_t_x``
        regardless of whether or not a naming convention is in use.

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
        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        """

        t = self._table(table_name, column, schema=schema)
        self.impl.add_column(
            table_name,
            column,
            schema=schema
        )
        for constraint in t.constraints:
            if not isinstance(constraint, sa_schema.PrimaryKeyConstraint):
                self.impl.add_constraint(constraint)

    def drop_column(self, table_name, column_name, **kw):
        """Issue a "drop column" instruction using the current
        migration context.

        e.g.::

            drop_column('organization', 'account_id')

        :param table_name: name of table
        :param column_name: name of column
        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

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

        self.impl.drop_column(
            table_name,
            self._column(column_name, NULLTYPE),
            **kw
        )


    def create_primary_key(self, name, table_name, cols, schema=None):
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
        object which it then associates with the :class:`~sqlalchemy.schema.Table`.
        Any event listeners associated with this action will be fired
        off normally.   The :class:`~sqlalchemy.schema.AddConstraint`
        construct is ultimately used to generate the ALTER statement.

        .. versionadded:: 0.5.0

        :param name: Name of the primary key constraint.  The name is necessary
         so that an ALTER statement can be emitted.  For setups that
         use an automated naming scheme such as that described at
         `NamingConventions <http://www.sqlalchemy.org/trac/wiki/UsageRecipes/NamingConventions>`_,
         ``name`` here can be ``None``, as the event listener will
         apply the name to the constraint object when it is associated
         with the table.
        :param table_name: String name of the target table.
        :param cols: a list of string column names to be applied to the
         primary key constraint.
        :param schema: Optional schema name of the table.

        """
        self.impl.add_constraint(
                    self._primary_key_constraint(name, table_name, cols,
                                schema)
                )


    def create_foreign_key(self, name, source, referent, local_cols,
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
        object which it then associates with the :class:`~sqlalchemy.schema.Table`.
        Any event listeners associated with this action will be fired
        off normally.   The :class:`~sqlalchemy.schema.AddConstraint`
        construct is ultimately used to generate the ALTER statement.

        :param name: Name of the foreign key constraint.  The name is necessary
         so that an ALTER statement can be emitted.  For setups that
         use an automated naming scheme such as that described at
         `NamingConventions <http://www.sqlalchemy.org/trac/wiki/UsageRecipes/NamingConventions>`_,
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
                    self._foreign_key_constraint(name, source, referent,
                            local_cols, remote_cols,
                            onupdate=onupdate, ondelete=ondelete,
                            deferrable=deferrable, source_schema=source_schema,
                            referent_schema=referent_schema,
                            initially=initially, match=match, **dialect_kw)
                )

    def create_unique_constraint(self, name, source, local_cols,
                                 schema=None, **kw):
        """Issue a "create unique constraint" instruction using the
        current migration context.

        e.g.::

            from alembic import op
            op.create_unique_constraint("uq_user_name", "user", ["name"])

        This internally generates a :class:`~sqlalchemy.schema.Table` object
        containing the necessary columns, then generates a new
        :class:`~sqlalchemy.schema.UniqueConstraint`
        object which it then associates with the :class:`~sqlalchemy.schema.Table`.
        Any event listeners associated with this action will be fired
        off normally.   The :class:`~sqlalchemy.schema.AddConstraint`
        construct is ultimately used to generate the ALTER statement.

        :param name: Name of the unique constraint.  The name is necessary
         so that an ALTER statement can be emitted.  For setups that
         use an automated naming scheme such as that described at
         `NamingConventions <http://www.sqlalchemy.org/trac/wiki/UsageRecipes/NamingConventions>`_,
         ``name`` here can be ``None``, as the event listener will
         apply the name to the constraint object when it is associated
         with the table.
        :param source: String name of the source table. Dotted schema names are
         supported.
        :param local_cols: a list of string column names in the
         source table.
        :param deferrable: optional bool. If set, emit DEFERRABLE or NOT DEFERRABLE when
         issuing DDL for this constraint.
        :param initially: optional string. If set, emit INITIALLY <value> when issuing DDL
         for this constraint.
        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        """

        self.impl.add_constraint(
                    self._unique_constraint(name, source, local_cols,
                        schema=schema, **kw)
                )

    def create_check_constraint(self, name, source, condition,
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
         `NamingConventions <http://www.sqlalchemy.org/trac/wiki/UsageRecipes/NamingConventions>`_,
         ``name`` here can be ``None``, as the event listener will
         apply the name to the constraint object when it is associated
         with the table.
        :param source: String name of the source table.
        :param condition: SQL expression that's the condition of the constraint.
         Can be a string or SQLAlchemy expression language structure.
        :param deferrable: optional bool. If set, emit DEFERRABLE or NOT DEFERRABLE when
         issuing DDL for this constraint.
        :param initially: optional string. If set, emit INITIALLY <value> when issuing DDL
         for this constraint.
        :param schema: Optional schema name to operate within.

         ..versionadded:: 0.4.0

        """
        self.impl.add_constraint(
            self._check_constraint(name, source, condition, schema=schema, **kw)
        )

    def create_table(self, name, *columns, **kw):
        """Issue a "create table" instruction using the current migration context.

        This directive receives an argument list similar to that of the
        traditional :class:`sqlalchemy.schema.Table` construct, but without the
        metadata::

            from sqlalchemy import INTEGER, VARCHAR, NVARCHAR, Column
            from alembic import op

            op.create_table(
                'account',
                Column('id', INTEGER, primary_key=True),
                Column('name', VARCHAR(50), nullable=False),
                Column('description', NVARCHAR(200))
                Column('timestamp', TIMESTAMP, server_default=func.now())
            )

        Note that :meth:`.create_table` accepts :class:`~sqlalchemy.schema.Column`
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

        :param name: Name of the table
        :param \*columns: collection of :class:`~sqlalchemy.schema.Column`
         objects within
         the table, as well as optional :class:`~sqlalchemy.schema.Constraint`
         objects
         and :class:`~.sqlalchemy.schema.Index` objects.
        :param schema: Optional schema name to operate within.
        :param \**kw: Other keyword arguments are passed to the underlying
         :class:`sqlalchemy.schema.Table` object created for the command.

        """
        self.impl.create_table(
            self._table(name, *columns, **kw)
        )

    def drop_table(self, name, **kw):
        """Issue a "drop table" instruction using the current
        migration context.


        e.g.::

            drop_table("accounts")

        :param name: Name of the table
        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        :param \**kw: Other keyword arguments are passed to the underlying
         :class:`sqlalchemy.schema.Table` object created for the command.

        """
        self.impl.drop_table(
            self._table(name, **kw)
        )

    def create_index(self, name, table_name, columns, schema=None, **kw):
        """Issue a "create index" instruction using the current
        migration context.

        e.g.::

            from alembic import op
            op.create_index('ik_test', 't1', ['foo', 'bar'])

        :param name: name of the index.
        :param table_name: name of the owning table.

         .. versionchanged:: 0.5.0
            The ``tablename`` parameter is now named ``table_name``.
            As this is a positional argument, the old name is no
            longer present.

        :param columns: a list of string column names in the
         table.
        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        """

        self.impl.create_index(
            self._index(name, table_name, columns, schema=schema, **kw)
        )

    @util._with_legacy_names([('tablename', 'table_name')])
    def drop_index(self, name, table_name=None, schema=None):
        """Issue a "drop index" instruction using the current
        migration context.

        e.g.::

            drop_index("accounts")

        :param name: name of the index.
        :param table_name: name of the owning table.  Some
         backends such as Microsoft SQL Server require this.

         .. versionchanged:: 0.5.0
            The ``tablename`` parameter is now named ``table_name``.
            The old name will continue to function for backwards
            compatibility.

        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        """
        # need a dummy column name here since SQLAlchemy
        # 0.7.6 and further raises on Index with no columns
        self.impl.drop_index(
            self._index(name, table_name, ['x'], schema=schema)
        )

    @util._with_legacy_names([("type", "type_")])
    def drop_constraint(self, name, table_name, type_=None, schema=None):
        """Drop a constraint of the given name, typically via DROP CONSTRAINT.

        :param name: name of the constraint.
        :param table_name: table name.

         .. versionchanged:: 0.5.0
            The ``tablename`` parameter is now named ``table_name``.
            As this is a positional argument, the old name is no
            longer present.

        :param ``type_``: optional, required on MySQL.  can be
         'foreignkey', 'primary', 'unique', or 'check'.

         .. versionchanged:: 0.5.0
            The ``type`` parameter is now named ``type_``.  The old name
            ``type`` will remain for backwards compatibility.

         .. versionadded:: 0.3.6 'primary' qualfier to enable
            dropping of MySQL primary key constraints.

        :param schema: Optional schema name to operate within.

         .. versionadded:: 0.4.0

        """

        t = self._table(table_name, schema=schema)
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

        When using --sql mode, some datatypes may not render inline automatically,
        such as dates and other special types.   When this issue is present,
        :meth:`.Operations.inline_literal` may be used::

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
           "executemany()" style, where all elements in the list of dictionaries
           are passed as bound parameters in a single list.   Setting this
           to False results in individual INSERT statements being emitted
           per parameter set, and is needed in those cases where non-literal
           values are present in the parameter sets.

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

        :param value: The value to render.  Strings, integers, and simple
         numerics should be supported.   Other types like boolean,
         dates, etc. may or may not be supported yet by various
         backends.
        :param ``type_``: optional - a :class:`sqlalchemy.types.TypeEngine`
         subclass stating the type of this value.  In SQLAlchemy
         expressions, this is usually derived automatically
         from the Python type of the value itself, as well as
         based on the context in which the value is used.

        """
        return impl._literal_bindparam(None, value, type_=type_)

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
        and :func:`sqlalchemy.sql.expression.column` constructs to make a brief,
        ad-hoc table construct just for our UPDATE statement.  A full
        :class:`~sqlalchemy.schema.Table` construct of course works perfectly
        fine as well, though note it's a recommended practice to at least ensure
        the definition of a table is self-contained within the migration script,
        rather than imported from a module that may break compatibility with
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
        self.migration_context.impl.execute(sql,
                    execution_options=execution_options)

    def get_bind(self):
        """Return the current 'bind'.

        Under normal circumstances, this is the
        :class:`~sqlalchemy.engine.Connection` currently being used
        to emit SQL to the database.

        In a SQL script context, this value is ``None``. [TODO: verify this]

        """
        return self.migration_context.impl.bind

