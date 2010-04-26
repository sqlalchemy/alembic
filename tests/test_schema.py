from tests import assert_compiled
from alembic import op
from sqlalchemy.schema import AddConstraint, ForeignKeyConstraint

def test_foreign_key():
    fk = op._foreign_key_constraint('fk_test', 't1', 't2', ['foo', 'bar'], ['bat', 'hoho'])
    assert_compiled(
        AddConstraint(fk),
        "ALTER TABLE t1 ADD CONSTRAINT hoho FOREIGN KEY(foo, bar) REFERENCES t2 (bat, hoho)"
    )
    
def test_unique_constraint():
    uc = op._unique_constraint('uk_test', 't1', ['foo', 'bar'])
    assert_compiled(
        AddConstraint(uc),
        "ALTER TABLE t1 ADD CONSTRAINT uk_test UNIQUE (foo, bar)"
    )
    