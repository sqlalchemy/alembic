from alembic import util
from alembic.context import get_context
from sqlalchemy.types import NULLTYPE
from sqlalchemy import schema

__all__ = [
            'alter_column', 
            'create_foreign_key', 
            'create_table',
            'drop_table',
            'create_unique_constraint', 
            'get_context',
            'get_bind',
            'execute']

def alter_column(table_name, column_name, 
                    nullable=util.NO_VALUE,
                    server_default=util.NO_VALUE,
                    name=util.NO_VALUE,
                    type_=util.NO_VALUE
):
    """Issue ALTER COLUMN using the current change context."""

    context.alter_column(table_name, column_name, 
        nullable=nullable,
        server_default=server_default,
        name=name,
        type_=type_
    )


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

def create_foreign_key(name, source, referent, local_cols, remote_cols):
    get_context().add_constraint(
                _foreign_key_constraint(source, referent, 
                        local_cols, remote_cols)
            )

def create_unique_constraint(name, source, local_cols):
    get_context().add_constraint(
                _unique_constraint(name, source, local_cols)
            )

def create_table(name, *columns, **kw):
    get_context().create_table(
        _table(name, *columns, **kw)
    )

def drop_table(name, *columns, **kw):
    get_context().drop_table(
        _table(name, *columns, **kw)
    )

def execute(sql):
    get_context().execute(sql)

def get_bind():
    return get_context().bind