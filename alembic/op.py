from alembic import util
from alembic.context import get_context
from sqlalchemy.types import NULLTYPE
from sqlalchemy import schema

__all__ = [
            'alter_column', 
            'create_foreign_key', 
            'create_unique_constraint', 
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
                                        ["%s.%s" % (referent, name) 
                                        for name in remote_cols],
                                        name=name
                                        )
    t1.append_constraint(f)
    return f

def _unique_constraint(name, source, local_cols):
    t = schema.Table(source, schema.MetaData(), 
                *[schema.Column(n, NULLTYPE) for n in local_cols])
    return schema.UniqueConstraint(*t.c, name=name)
    
def create_foreign_key(name, source, referent, local_cols, remote_cols):
    get_context().add_constraint(
                _foreign_key_constraint(source, referent, local_cols, remote_cols)
            )

def create_unique_constraint(name, source, local_cols):
    get_context().add_constraint(
                _unique_constraint(name, source, local_cols)
            )

def execute(sql):
    get_context().execute(sql)