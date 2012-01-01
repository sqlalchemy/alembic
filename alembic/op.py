from alembic import util
from alembic.ddl import impl
from alembic.context import get_impl, get_context
from sqlalchemy.types import NULLTYPE, Integer
from sqlalchemy import schema, sql

__all__ = sorted([
            'alter_column', 
            'add_column',
            'drop_column',
            'drop_constraint',
            'create_foreign_key', 
            'create_table',
            'drop_table',
            'drop_index',
            'create_index',
            'inline_literal',
            'bulk_insert',
            'rename_table',
            'create_unique_constraint', 
            'create_check_constraint',
            'get_context',
            'get_bind',
            'execute'])

def _foreign_key_constraint(name, source, referent, local_cols, remote_cols):
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

def _unique_constraint(name, source, local_cols, **kw):
    t = schema.Table(source, schema.MetaData(), 
                *[schema.Column(n, NULLTYPE) for n in local_cols])
    kw['name'] = name
    uq = schema.UniqueConstraint(*t.c, **kw)
    # TODO: need event tests to ensure the event
    # is fired off here
    t.append_constraint(uq)
    return uq

def _check_constraint(name, source, condition, **kw):
    t = schema.Table(source, schema.MetaData(), 
                schema.Column('x', Integer))
    ck = schema.CheckConstraint(condition, name=name, **kw)
    t.append_constraint(ck)
    return ck

def _table(name, *columns, **kw):
    m = schema.MetaData()
    t = schema.Table(name, m, *columns, **kw)
    for f in t.foreign_keys:
        _ensure_table_for_fk(m, f)
    return t

def _column(name, type_, **kw):
    return schema.Column(name, type_, **kw)

def _index(name, tablename, columns, **kw):
    t = schema.Table(tablename, schema.MetaData(),
        *[schema.Column(n, NULLTYPE) for n in columns]
    )
    return schema.Index(name, *list(t.c), **kw)

def _ensure_table_for_fk(metadata, fk):
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

def rename_table(old_table_name, new_table_name, schema=None):
    """Emit an ALTER TABLE to rename a table.
    
    :param old_table_name: old name.
    :param new_table_name: new name.
    :param schema: Optional, name of schema to operate within.
    
    """
    get_impl().rename_table(
        old_table_name,
        new_table_name,
        schema=schema
    )

def alter_column(table_name, column_name, 
                    nullable=None,
                    server_default=False,
                    name=None,
                    type_=None,
                    existing_type=None,
                    existing_server_default=False,
                    existing_nullable=None,
):
    """Issue an "alter column" instruction using the 
    current change context.
    
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
    :param column_name: string name of the target column.
    :param nullable: Optional; specify ``True`` or ``False``
     to alter the column's nullability.
    :param server_default: Optional; specify a string 
     SQL expression, :func:`~sqlalchemy.sql.expression.text`,
     or :class:`~sqlalchemy.schema.DefaultClause` to indicate
     an alteration to the column's default value.  
     Set to ``None`` to have the default removed.
    :param name: Optional; specify a string name here to
     indicate a column rename operation.
    :param type_: Optional; a :class:`~sqlalchemy.types.TypeEngine`
     type object to specify a change to the column's type.  
     For SQLAlchemy types that also indicate a constraint (i.e. 
     :class:`~sqlalchemy.types.Boolean`, :class:`~sqlalchemy.types.Enum`), 
     the constraint is also generated.
    :param existing_type: Optional; a :class:`~sqlalchemy.types.TypeEngine`
     type object to specify the previous type.   This
     is required for all MySQL column alter operations that 
     don't otherwise specify a new type, as well as for
     when nullability is being changed on a SQL Server
     column.  It is also used if the type is a so-called 
     SQLlchemy "schema" type which
     may define a constraint (i.e. 
     :class:`~sqlalchemy.types.Boolean`, :class:`~sqlalchemy.types.Enum`), 
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
        t = _table(table_name, schema.Column(column_name, existing_type))
        for constraint in t.constraints:
            if not isinstance(constraint, schema.PrimaryKeyConstraint):
                get_impl().drop_constraint(constraint)

    get_impl().alter_column(table_name, column_name, 
        nullable=nullable,
        server_default=server_default,
        name=name,
        type_=type_,
        existing_type=existing_type,
        existing_server_default=existing_server_default,
        existing_nullable=existing_nullable,
    )

    if type_:
        t = _table(table_name, schema.Column(column_name, type_))
        for constraint in t.constraints:
            if not isinstance(constraint, schema.PrimaryKeyConstraint):
                get_impl().add_constraint(constraint)

def add_column(table_name, column):
    """Issue an "add column" instruction using the current change context.
    
    e.g.::

        from alembic.op import add_column
        from sqlalchemy import Column, String

        add_column('organization', 
            Column('name', String())
        )        

    The provided :class:`~sqlalchemy.schema.Column` object can also
    specify a :class:`~sqlalchemy.schema.ForeignKey`, referencing
    a remote table name.  Alembic will automatically generate a stub
    "referenced" table and emit a second ALTER statement in order
    to add the constraint separately::
    
        from alembic.op import add_column
        from sqlalchemy import Column, INTEGER, ForeignKey

        add_column('organization', 
            Column('account_id', INTEGER, ForeignKey('accounts.id'))
        )        
    
    :param table_name: String name of the parent table.
    :param column: a :class:`sqlalchemy.schema.Column` object
     representing the new column.
     
    """

    t = _table(table_name, column)
    get_impl().add_column(
        table_name,
        column
    )
    for constraint in t.constraints:
        if not isinstance(constraint, schema.PrimaryKeyConstraint):
            get_impl().add_constraint(constraint)

def drop_column(table_name, column_name, **kw):
    """Issue a "drop column" instruction using the current change context.
    
    e.g.::
    
        drop_column('organization', 'account_id')
    
    :param table_name: name of table
    :param column_name: name of column
    :param mssql_drop_check: Optional boolean.  When ``True``, on 
     Microsoft SQL Server only, first 
     drop the CHECK constraint on the column using a SQL-script-compatible
     block that selects into a @variable from sys.check_constraints,
     then exec's a separate DROP CONSTRAINT for that constraint.
    :param mssql_drop_default: Optional boolean.  When ``True``, on 
     Microsoft SQL Server only, first 
     drop the DEFAULT constraint on the column using a SQL-script-compatible
     block that selects into a @variable from sys.default_constraints,
     then exec's a separate DROP CONSTRAINT for that default.
     
    """

    get_impl().drop_column(
        table_name,
        _column(column_name, NULLTYPE),
        **kw
    )


def create_foreign_key(name, source, referent, local_cols, remote_cols):
    """Issue a "create foreign key" instruction using the 
    current change context.

    e.g.::
    
        from alembic.op import create_foreign_key
        create_foreign_key("fk_user_address", "address", "user", ["user_id"], ["id"])

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

    get_impl().add_constraint(
                _foreign_key_constraint(name, source, referent, 
                        local_cols, remote_cols)
            )

def create_unique_constraint(name, source, local_cols, **kw):
    """Issue a "create unique constraint" instruction using the current change context.

    e.g.::
    
        from alembic.op import create_unique_constraint
        create_unique_constraint("uq_user_name", "user", ["name"])

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

    get_impl().add_constraint(
                _unique_constraint(name, source, local_cols, 
                    **kw)
            )

def create_check_constraint(name, source, condition, **kw):
    """Issue a "create check constraint" instruction using the current change context.
    
    e.g.::
    
        from alembic.op import create_check_constraint
        from sqlalchemy.sql import column, func
        
        create_check_constraint(
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
    get_impl().add_constraint(
        _check_constraint(name, source, condition, **kw)
    )

def create_table(name, *columns, **kw):
    """Issue a "create table" instruction using the current change context.
    
    This directive receives an argument list similar to that of the 
    traditional :class:`sqlalchemy.schema.Table` construct, but without the
    metadata::
        
        from sqlalchemy import INTEGER, VARCHAR, NVARCHAR, Column
        from alembic.op import create_table

        create_table(
            'accounts',
            Column('id', INTEGER, primary_key=True),
            Column('name', VARCHAR(50), nullable=False),
            Column('description', NVARCHAR(200))
        )

    :param name: Name of the table
    :param \*columns: collection of :class:`~sqlalchemy.schema.Column` objects within
     the table, as well as optional :class:`~sqlalchemy.schema.Constraint` objects
     and :class:`~.sqlalchemy.schema.Index` objects.
    :param emit_events: if ``True``, emit ``before_create`` and ``after_create``
     events when the table is being created.  In particular, the Postgresql ENUM
     type will emit a CREATE TYPE within these events.
    :param \**kw: Other keyword arguments are passed to the underlying
     :class:`.Table` object created for the command.
     
    """
    get_impl().create_table(
        _table(name, *columns, **kw)
    )

def drop_table(name):
    """Issue a "drop table" instruction using the current change context.
    
    
    e.g.::
    
        drop_table("accounts")
        
    """
    get_impl().drop_table(
        _table(name)
    )

def create_index(name, tablename, *columns, **kw):
    """Issue a "create index" instruction using the current change context.
    
    e.g.::
        
        from alembic.op import create_index
        create_index('ik_test', 't1', ['foo', 'bar'])

    """

    get_impl().create_index(
        _index(name, tablename, *columns, **kw)
    )

def drop_index(name):
    """Issue a "drop index" instruction using the current change context.
    
    
    e.g.::
    
        drop_index("accounts")
        
    """
    get_impl().drop_index(_index(name, 'foo', []))

def drop_constraint(name, tablename):
    """Drop a constraint of the given name"""
    t = _table(tablename)
    const = schema.Constraint(name=name)
    t.append_constraint(const)
    get_impl().drop_constraint(const)

def bulk_insert(table, rows):
    """Issue a "bulk insert" operation using the current change context.
    
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
                {'id':1, 'name':'John Smith', 'create_date':date(2010, 10, 5)},
                {'id':2, 'name':'Ed Williams', 'create_date':date(2007, 5, 27)},
                {'id':3, 'name':'Wendy Jones', 'create_date':date(2008, 8, 15)},
            ]
        )
      """
    get_impl().bulk_insert(table, rows)

def inline_literal(value, type_=None):
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

    See :func:`.op.execute` for an example usage of
    :func:`.inline_literal`.
    
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

def execute(sql):
    """Execute the given SQL using the current change context.
    
    In a SQL script context, the statement is emitted directly to the 
    output stream.   There is *no* return result, however, as this
    function is oriented towards generating a change script
    that can run in "offline" mode.  For full interaction
    with a connected database, use the "bind" available 
    from the context::
    
        from alembic.op import get_bind
        connection = get_bind()
    
    Also note that any parameterized statement here *will not work*
    in offline mode - INSERT, UPDATE and DELETE statements which refer
    to literal values would need to render
    inline expressions.   For simple use cases, the :func:`.inline_literal`
    function can be used for **rudimentary** quoting of string values.
    For "bulk" inserts, consider using :func:`~alembic.op.bulk_insert`.
    
    For example, to emit an UPDATE statement which is equally
    compatible with both online and offline mode::
    
        from sqlalchemy.sql import table, column
        from sqlalchemy import String
        from alembic.op import execute, inline_literal
        
        account = table('account', 
            column('name', String)
        )
        execute(
            account.update().\\
                where(account.c.name==inline_literal('account 1')).\\
                values({'name':inline_literal('account 2')})
                )
    
    Note above we also used the SQLAlchemy :func:`sqlalchemy.sql.expression.table`
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
    * a :func:`sqlalchemy.sql.expression.update`, :func:`sqlalchemy.sql.expression.insert`, 
      or :func:`sqlalchemy.sql.expression.delete`  construct.
    * Pretty much anything that's "executable" as described
      in :ref:`sqlexpression_toplevel`.

    
    """
    get_impl().execute(sql)

def get_bind():
    """Return the current 'bind'.
    
    Under normal circumstances, this is the 
    :class:`sqlalchemy.engine.Connection` currently being used
    to emit SQL to the database.
    
    In a SQL script context, this value is ``None``. [TODO: verify this]
    
    """
    return get_impl().bind