from alembic import util
from alembic.context import get_impl, get_context
from sqlalchemy.types import NULLTYPE
from sqlalchemy import schema, sql

util.importlater.resolve_all()

__all__ = sorted([
            'alter_column', 
            'add_column',
            'drop_column',
            'create_foreign_key', 
            'create_table',
            'drop_table',
            'drop_index',
            'create_index',
            'bulk_insert',
            'create_unique_constraint', 
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
    return schema.UniqueConstraint(*t.c, name=name, **kw)

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
        if not rel_t.c.contains_column(cname):
            rel_t.append_column(schema.Column(cname, NULLTYPE))


def alter_column(table_name, column_name, 
                    nullable=None,
                    server_default=False,
                    name=None,
                    type_=None
):
    """Issue an "alter column" instruction using the current change context."""

    get_impl().alter_column(table_name, column_name, 
        nullable=nullable,
        server_default=server_default,
        name=name,
        type_=type_
    )

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
    for constraint in [f.constraint for f in t.foreign_keys]:
        get_impl().add_constraint(constraint)

def drop_column(table_name, column_name):
    """Issue a "drop column" instruction using the current change context.
    
    e.g.::
    
        drop_column('organization', 'account_id')
    
    """

    get_impl().drop_column(
        table_name,
        _column(column_name, NULLTYPE)
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

def bulk_insert(table, rows):
    """Issue a "bulk insert" operation using the current change context.
    
    This provides a means of representing an INSERT of multiple rows
    which works equally well in the context of executing on a live 
    connection as well as that of generating a SQL script.   In the 
    case of a SQL script, the values are rendered inline into the 
    statement.
    
    e.g.::
    
        from myapp.mymodel import accounts_table
        from datetime import date
        
        bulk_insert(accounts_table,
            [
                {'id':1, 'name':'John Smith', 'create_date':date(2010, 10, 5)},
                {'id':2, 'name':'Ed Williams', 'create_date':date(2007, 5, 27)},
                {'id':3, 'name':'Wendy Jones', 'create_date':date(2008, 8, 15)},
            ]
        )
      """
    get_impl().bulk_insert(table, rows)

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
    in offline mode - any kind of UPDATE or DELETE needs to render
    inline expressions.   Due to these limitations, 
    :func:`.execute` is overall not spectacularly useful for migration 
    scripts that wish to run in offline mode.  Consider using the Alembic 
    directives, or if the environment is only meant to run in 
    "online" mode, use the ``get_context().bind``.
    
    :param sql: Any legal SQLAlchemy expression, including:
    
    * a string
    * a :func:`sqlalchemy.sql.expression.text` construct, with the caveat that
      bound parameters won't work correctly in offline mode.
    * a :func:`sqlalchemy.sql.expression.insert` construct.  If working 
      in offline mode, consider using :func:`alembic.op.bulk_insert`
      instead to support parameterization.
    * a :func:`sqlalchemy.sql.expression.update`, :func:`sqlalchemy.sql.expression.insert`, 
      or :func:`sqlalchemy.sql.expression.delete`  construct, with the caveat
      that bound parameters won't work correctly in offline mode.
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