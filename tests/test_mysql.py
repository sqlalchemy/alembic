from tests import _op_fixture
from alembic import op
from sqlalchemy import Integer, Column, ForeignKey, \
            UniqueConstraint, Table, MetaData, String
from sqlalchemy.sql import table

def test_rename_column():
    context = _op_fixture('mysql')
    op.alter_column('t1', 'c1', name="c2", existing_type=Integer)
    context.assert_(
        'ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL'
    )

def test_rename_column_serv_default():
    context = _op_fixture('mysql')
    op.alter_column('t1', 'c1', name="c2", existing_type=Integer, existing_server_default="q")
    context.assert_(
        "ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL DEFAULT 'q'"
    )

def test_col_nullable():
    context = _op_fixture('mysql')
    op.alter_column('t1', 'c1', nullable=False, existing_type=Integer)
    context.assert_(
        'ALTER TABLE t1 CHANGE c1 c1 INTEGER NOT NULL'
    )

