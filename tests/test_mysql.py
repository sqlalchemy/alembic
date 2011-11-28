from tests import op_fixture, assert_raises_message
from alembic import op, util
from sqlalchemy import Integer, Column, ForeignKey, \
            UniqueConstraint, Table, MetaData, String
from sqlalchemy.sql import table

def test_rename_column():
    context = op_fixture('mysql')
    op.alter_column('t1', 'c1', name="c2", existing_type=Integer)
    context.assert_(
        'ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL'
    )

def test_rename_column_serv_default():
    context = op_fixture('mysql')
    op.alter_column('t1', 'c1', name="c2", existing_type=Integer, existing_server_default="q")
    context.assert_(
        "ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL DEFAULT 'q'"
    )

def test_col_nullable():
    context = op_fixture('mysql')
    op.alter_column('t1', 'c1', nullable=False, existing_type=Integer)
    context.assert_(
        'ALTER TABLE t1 CHANGE c1 c1 INTEGER NOT NULL'
    )

def test_col_multi_alter():
    context = op_fixture('mysql')
    op.alter_column('t1', 'c1', nullable=False, server_default="q", type_=Integer)
    context.assert_(
        "ALTER TABLE t1 CHANGE c1 c1 INTEGER NOT NULL DEFAULT 'q'"
    )


def test_col_alter_type_required():
    context = op_fixture('mysql')
    assert_raises_message(
        util.CommandError,
        "All MySQL ALTER COLUMN operations require the existing type.",
        op.alter_column, 't1', 'c1', nullable=False, server_default="q"
    )
