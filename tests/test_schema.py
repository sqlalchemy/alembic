from tests import assert_compiled
from alembic import op
from sqlalchemy.schema import AddConstraint, ForeignKeyConstraint, \
                            CreateTable, Column, ForeignKey,\
                            MetaData, Table
from sqlalchemy import Integer

# TODO: should these all just go to test_op ?

def test_foreign_key():
    fk = op._foreign_key_constraint('fk_test', 't1', 't2', 
                    ['foo', 'bar'], ['bat', 'hoho'])
    assert_compiled(
        AddConstraint(fk),
        "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho)"
    )

def test_unique_constraint():
    uc = op._unique_constraint('uk_test', 't1', ['foo', 'bar'])
    assert_compiled(
        AddConstraint(uc),
        "ALTER TABLE t1 ADD CONSTRAINT uk_test UNIQUE (foo, bar)"
    )


def test_table_schema_fk():
    tb = op._table("some_table", 
        Column('id', Integer, primary_key=True),
        Column('foo_id', Integer, ForeignKey('foo.id')),
        schema='schema'
    )
    assert_compiled(
        CreateTable(tb),
        "CREATE TABLE schema.some_table ("
            "id INTEGER NOT NULL, "
            "foo_id INTEGER, "
            "PRIMARY KEY (id), "
            "FOREIGN KEY(foo_id) REFERENCES foo (id))"
    )

def test_table_two_fk():
    tb = op._table("some_table", 
        Column('id', Integer, primary_key=True),
        Column('foo_id', Integer, ForeignKey('foo.id')),
        Column('foo_bar', Integer, ForeignKey('foo.bar')),
    )
    assert_compiled(
        CreateTable(tb),
        "CREATE TABLE some_table ("
            "id INTEGER NOT NULL, "
            "foo_id INTEGER, "
            "foo_bar INTEGER, "
            "PRIMARY KEY (id), "
            "FOREIGN KEY(foo_id) REFERENCES foo (id), "
            "FOREIGN KEY(foo_bar) REFERENCES foo (bar))"
    )

