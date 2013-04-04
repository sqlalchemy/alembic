from tests import op_fixture, assert_raises_message
from alembic import op
from sqlalchemy import Integer, Column,  Boolean
from sqlalchemy.sql import column

def test_add_column():
    context = op_fixture('sqlite')
    op.add_column('t1', Column('c1', Integer))
    context.assert_(
        'ALTER TABLE t1 ADD COLUMN c1 INTEGER'
    )

def test_add_column_implicit_constraint():
    context = op_fixture('sqlite')
    op.add_column('t1', Column('c1', Boolean))
    context.assert_(
        'ALTER TABLE t1 ADD COLUMN c1 BOOLEAN'
    )

def test_add_explicit_constraint():
    context = op_fixture('sqlite')
    assert_raises_message(
        NotImplementedError,
        "No support for ALTER of constraints in SQLite dialect",
        op.create_check_constraint,
        "foo",
        "sometable",
        column('name') > 5
    )

def test_drop_explicit_constraint():
    context = op_fixture('sqlite')
    assert_raises_message(
        NotImplementedError,
        "No support for ALTER of constraints in SQLite dialect",
        op.drop_constraint,
        "foo",
        "sometable",
    )

