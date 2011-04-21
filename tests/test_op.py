"""Test against the builders in the op.* module."""

from tests import _op_fixture
from alembic import op
from sqlalchemy import Integer

def test_add_column():
    context = _op_fixture()
    op.add_column('t1', 'c1', Integer, nullable=False)
    context.assert_("ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL")


def test_drop_column():
    context = _op_fixture()
    op.drop_column('t1', 'c1')
    context.assert_("ALTER TABLE t1 DROP COLUMN c1")
