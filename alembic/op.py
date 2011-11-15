from alembic import util
from alembic.context import get_impl, get_context
from sqlalchemy.types import NULLTYPE
from sqlalchemy import schema, sql

util.importlater.resolve_all()

__all__ = [
            'alter_column', 
            'add_column',
            'drop_column',
            'add_constraint',
            'create_foreign_key', 
            'create_table',
            'drop_table',
            'bulk_insert',
            'create_unique_constraint', 
            'get_context',
            'get_bind',
            'execute']

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

def _ensure_table_for_constraint(name, constraint):
    if getattr(constraint, 'parent', None) is not None:
        return
    if isinstance(constraint, schema.UniqueConstraint):
        # TODO: what if constraint has Column objects already
        columns = [schema.Column(n, NULLTYPE) for n in 
                        constraint._pending_colargs]
    else:
        columns = []
    return schema.Table(name, schema.MetaData(), *(columns + [constraint]) )

def _unique_constraint(name, source, local_cols):
    t = schema.Table(source, schema.MetaData(), 
                *[schema.Column(n, NULLTYPE) for n in local_cols])
    return schema.UniqueConstraint(*t.c, name=name)

def _table(name, *columns, **kw):
    m = schema.MetaData()
    t = schema.Table(name, m, *columns, **kw)
    for f in t.foreign_keys:
        _ensure_table_for_fk(m, f)
    return t

def _column(name, type_, **kw):
    return schema.Column(name, type_, **kw)

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
    
        add_column('organization', 
            Column('account_id', INTEGER, ForeignKey('accounts.id'))
        )        
    
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

def add_constraint(table_name, constraint):
    """Issue an "add constraint" instruction using the current change context."""

    _ensure_table_for_constraint(table_name, constraint)
    get_impl().add_constraint(
        constraint
    )

def create_foreign_key(name, source, referent, local_cols, remote_cols):
    """Issue a "create foreign key" instruction using the current change context."""

    get_impl().add_constraint(
                _foreign_key_constraint(name, source, referent, 
                        local_cols, remote_cols)
            )

def create_unique_constraint(name, source, local_cols):
    """Issue a "create unique constraint" instruction using the current change context."""

    get_impl().add_constraint(
                _unique_constraint(name, source, local_cols)
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

def drop_table(name, *columns, **kw):
    """Issue a "drop table" instruction using the current change context.
    
    
    e.g.::
    
        drop_table("accounts")
        
    """
    get_impl().drop_table(
        _table(name, *columns, **kw)
    )

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
    output stream.
    
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