"""Test op functions against MSSQL."""

from tests import _op_fixture
from alembic import op
from sqlalchemy import Integer, Column, ForeignKey, \
            UniqueConstraint, Table, MetaData, String
from sqlalchemy.sql import table

def test_add_column():
    context = _op_fixture('mssql')
    op.add_column('t1', Column('c1', Integer, nullable=False))
    context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL")

def test_add_column_with_default():
    context = _op_fixture("mssql")
    op.add_column('t1', Column('c1', Integer, nullable=False, server_default="12"))
    context.assert_("ALTER TABLE t1 ADD c1 INTEGER NOT NULL DEFAULT '12'")

def test_alter_column_rename_mssql():
    context = _op_fixture('mssql')
    op.alter_column("t", "c", name="x")
    context.assert_(
        "EXEC sp_rename 't.c', 'x', 'COLUMN'"
    )

# TODO: when we add schema support
#def test_alter_column_rename_mssql_schema():
#    context = _op_fixture('mssql')
#    op.alter_column("t", "c", name="x", schema="y")
#    context.assert_(
#        "EXEC sp_rename 'y.t.c', 'x', 'COLUMN'"
#    )

