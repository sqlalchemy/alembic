from alembic import util
from alembic.ddl import impl
from sqlalchemy.types import NULLTYPE, Integer
from sqlalchemy import schema, sql
from contextlib import contextmanager
import alembic

__all__ = ('Operations',)

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
        op = Operations(migration_context)
        alembic.op._install_proxy(op)
        yield op
        alembic.op._remove_proxy()

    def _foreign_key_constraint(self, name, source, referent, 
                                    local_cols, remote_cols):
        m = schema.MetaData()
        t1 = schema.Table(source, m, 
                *[schema.Column(n, NULLTYPE) for n in local_cols])
        t2 = schema.Table(referent, m, 
                *[schema.Column(n, NULLTYPE) for n in remote_cols])

        f = schema.ForeignKeyConstraint(local_cols, 
                                            ["%s.%s" % (referent, n) 
                                            for n in remote_cols],
                                            name=name
                                            )
        t1.append_constraint(f)

        return f

    def _unique_constraint(self, name, source, local_cols, **kw):
        t = schema.Table(source, schema.MetaData(), 
                    *[schema.Column(n, NULLTYPE) for n in local_cols])
        kw['name'] = name
        uq = schema.UniqueConstraint(*t.c, **kw)
        # TODO: need event tests to ensure the event
        # is fired off here
        t.append_constraint(uq)
        return uq

    def _check_constraint(self, name, source, condition, **kw):
        t = schema.Table(source, schema.MetaData(), 
                    schema.Column('x', Integer))
        ck = schema.CheckConstraint(condition, name=name, **kw)
        t.append_constraint(ck)
        return ck

    def _table(self, name, *columns, **kw):
        m = schema.MetaData()
        t = schema.Table(name, m, *columns, **kw)
        for f in t.foreign_keys:
            self._ensure_table_for_fk(m, f)
        return t

    def _column(self, name, type_, **kw):
        return schema.Column(name, type_, **kw)

    def _index(self, name, tablename, columns, **kw):
        t = schema.Table(tablename, schema.MetaData(),
            *[schema.Column(n, NULLTYPE) for n in columns]
        )
        return schema.Index(name, *list(t.c), **kw)

    def _ensure_table_for_fk(self, metadata, fk):
        """create a placeholder Table object for the referent of a
        ForeignKey.

        """
        if isinstance(fk._colspec, basestring):
            table_key, cname = fk._colspec.split('.')
            if '.' in table_key:
                tokens = tname.split('.')
                sname = ".".join(tokens[0:-1])
                tname = tokens[-1]
            else:
                tname = table_key
                sname = None
            if table_key not in metadata.tables:
                rel_t = schema.Table(tname, metadata, schema=sname)
            else:
                rel_t = metadata.tables[table_key]
            if cname not in rel_t.c:
                rel_t.append_column(schema.Column(cname, NULLTYPE))

    def get_context(self):
        """Return the :class:`.MigrationContext` object that's
        currently in use.

        """

        return self.migration_context

    def rename_table(self, old_table_name, new_table_name, schema=None):
        """Emit an ALTER TABLE to rename a table.

        :param old_table_name: old name.
        :param new_table_name: new name.
        :param schema: Optional, name of schema to operate within.

        """
        self.impl.rename_table(
            old_table_name,
            new_table_name,
            schema=schema
        )

    def alter_column(self, table_name, column_name, 
                        nullable=None,
                        server_default=False,
                        name=None,
                        type_=None,
                        existing_type=None,
                        existing_server_default=False,
                        existing_nullable=None,
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
        :param name: Optional; specify a string name here to
         indicate the new name within a column rename operation.
        :param type_: Optional; a :class:`~sqlalchemy.types.TypeEngine`
         type object to specify a change to the column's type.
         For SQLAlchemy types that also indicate a constraint (i.e. 
         :class:`~sqlalchemy.types.Boolean`, 
         :class:`~sqlalchemy.types.Enum`), 
         the constraint is also generated.
        :param existing_type: Optional; a 
         :class:`~sqlalchemy.types.TypeEngine`
         type object to specify the previous type.   This
         is required for all MySQL column alter operations that 
         don't otherwise specify a new type, as well as for
         when nullability is being changed on a SQL Server
         column.  It is also used if the type is a so-called 
         SQLlchemy "schema" type which
         may define a constraint (i.e. 
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
        """

        if existing_type:
            t = self._table(table_name, 
                        schema.Column(column_name, existing_type)
                    )
            for constraint in t.constraints:
                if not isinstance(constraint, schema.PrimaryKeyConstraint):
                    self.impl.drop_constraint(constraint)

        self.impl.alter_column(table_name, column_name, 
            nullable=nullable,
            server_default=server_default,
            name=name,
            type_=type_,
            existing_type=existing_type,
            existing_server_default=existing_server_default,
            existing_nullable=existing_nullable,
        )

        if type_:
            t = self._table(table_name, schema.Column(column_name, type_))
            for constraint in t.constraints:
                if not isinstance(constraint, schema.PrimaryKeyConstraint):
                    self.impl.add_constraint(constraint)

    def add_column(self, table_name, column):
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

        :param table_name: String name of the parent table.
        :param column: a :class:`sqlalchemy.schema.Column` object
         representing the new column.

        """

        t = self._table(table_name, column)
        self.impl.add_column(
            table_name,
            column
        )
        for constraint in t.constraints:
            if not isinstance(constraint, schema.PrimaryKeyConstraint):
                self.impl.add_constraint(constraint)

    def drop_column(self, table_name, column_name, **kw):
        """Issue a "drop column" instruction using the current 
        migration context.

        e.g.::

            drop_column('organization', 'account_id')

        :param table_name: name of table
        :param column_name: name of column
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

        """

        self.impl.drop_column(
            table_name,
            self._column(column_name, NULLTYPE),
            **kw
        )


    def create_foreign_key(self, name, source, referent, local_cols, 
                                    remote_cols):
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
        :param source: String name of the source table.  Currently
         there is no support for dotted schema names.
        :param referent: String name of the destination table. Currently
         there is no support for dotted schema names.
        :param local_cols: a list of string column names in the 
         source table.
        :param remote_cols: a list of string column names in the
         remote table.

        """

        self.impl.add_constraint(
                    self._foreign_key_constraint(name, source, referent, 
                            local_cols, remote_cols)
                )

    def create_unique_constraint(self, name, source, local_cols, **kw):
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
        :param source: String name of the source table.  Currently
         there is no support for dotted schema names.
        :param local_cols: a list of string column names in the 
         source table.
        :param deferrable: optional bool. If set, emit DEFERRABLE or NOT DEFERRABLE when
         issuing DDL for this constraint.
        :param initially: optional string. If set, emit INITIALLY <value> when issuing DDL
         for this constraint.

        """

        self.impl.add_constraint(
                    self._unique_constraint(name, source, local_cols, 
                        **kw)
                )

    def create_check_constraint(self, name, source, condition, **kw):
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
        :param source: String name of the source table.  Currently
         there is no support for dotted schema names.
        :param condition: SQL expression that's the condition of the constraint.
         Can be a string or SQLAlchemy expression language structure.
        :param deferrable: optional bool. If set, emit DEFERRABLE or NOT DEFERRABLE when
         issuing DDL for this constraint.
        :param initially: optional string. If set, emit INITIALLY <value> when issuing DDL
         for this constraint.

        """
        self.impl.add_constraint(
            self._check_constraint(name, source, condition, **kw)
        )

    def create_table(self, name, *columns, **kw):
        """Issue a "create table" instruction using the current migration context.

        This directive receives an argument list similar to that of the 
        traditional :class:`sqlalchemy.schema.Table` construct, but without the
        metadata::

            from sqlalchemy import INTEGER, VARCHAR, NVARCHAR, Column
            from alembic import op

            op.create_table(
                'accounts',
                Column('id', INTEGER, primary_key=True),
                Column('name', VARCHAR(50), nullable=False),
                Column('description', NVARCHAR(200))
            )

        :param name: Name of the table
        :param \*columns: collection of :class:`~sqlalchemy.schema.Column` 
         objects within
         the table, as well as optional :class:`~sqlalchemy.schema.Constraint` 
         objects
         and :class:`~.sqlalchemy.schema.Index` objects.
        :param emit_events: if ``True``, emit ``before_create`` and 
         ``after_create`` events when the table is being created.  In 
         particular, the Postgresql ENUM type will emit a CREATE TYPE within 
         these events.
        :param \**kw: Other keyword arguments are passed to the underlying
         :class:`.Table` object created for the command.

        """
        self.impl.create_table(
            self._table(name, *columns, **kw)
        )

    def drop_table(self, name):
        """Issue a "drop table" instruction using the current 
        migration context.


        e.g.::

            drop_table("accounts")

        """
        self.impl.drop_table(
            self._table(name)
        )

    def create_index(self, name, tablename, *columns, **kw):
        """Issue a "create index" instruction using the current 
        migration context.

        e.g.::

            from alembic import op
            op.create_index('ik_test', 't1', ['foo', 'bar'])

        """

        self.impl.create_index(
            self._index(name, tablename, *columns, **kw)
        )

    def drop_index(self, name):
        """Issue a "drop index" instruction using the current 
        migration context.


        e.g.::

            drop_index("accounts")

        """
        self.impl.drop_index(self._index(name, 'foo', []))

    def drop_constraint(self, name, tablename):
        """Drop a constraint of the given name"""
        t = self._table(tablename)
        const = schema.Constraint(name=name)
        t.append_constraint(const)
        self.impl.drop_constraint(const)

    def bulk_insert(self, table, rows):
        """Issue a "bulk insert" operation using the current 
        migration context.

        This provides a means of representing an INSERT of multiple rows
        which works equally well in the context of executing on a live 
        connection as well as that of generating a SQL script.   In the 
        case of a SQL script, the values are rendered inline into the 
        statement.

        e.g.::

            from datetime import date
            from sqlalchemy.sql import table, column
            from sqlalchemy import String, Integer, Date

            # Create an ad-hoc table to use for the insert statement.
            accounts_table = table('account',
                column('id', Integer),
                column('name', String),
                column('create_date', Date)
            )

            bulk_insert(accounts_table,
                [
                    {'id':1, 'name':'John Smith', 
                            'create_date':date(2010, 10, 5)},
                    {'id':2, 'name':'Ed Williams', 
                            'create_date':date(2007, 5, 27)},
                    {'id':3, 'name':'Wendy Jones', 
                            'create_date':date(2008, 8, 15)},
                ]
            )
          """
        self.impl.bulk_insert(table, rows)

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
        :param type_: optional - a :class:`sqlalchemy.types.TypeEngine` 
         subclass stating the type of this value.  In SQLAlchemy 
         expressions, this is usually derived automatically
         from the Python type of the value itself, as well as
         based on the context in which the value is used.

        """
        return impl._literal_bindparam(None, value, type_=type_)

    def execute(self, sql):
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


        """
        self.migration_context.impl.execute(sql)

    def get_bind(self):
        """Return the current 'bind'.

        Under normal circumstances, this is the 
        :class:`~sqlalchemy.engine.base.Connection` currently being used
        to emit SQL to the database.

        In a SQL script context, this value is ``None``. [TODO: verify this]

        """
        return self.migration_context.impl.bind

