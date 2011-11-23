"""Test against the builders in the op.* module."""

from tests import _op_fixture
from alembic import op
from sqlalchemy import Integer, Column, ForeignKey, \
            UniqueConstraint, Table, MetaData, String
from sqlalchemy.sql import table

def test_add_column():
    context = _op_fixture()
    op.add_column('t1', Column('c1', Integer, nullable=False))
    context.assert_("ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL")

def test_add_column_with_default():
    context = _op_fixture()
    op.add_column('t1', Column('c1', Integer, nullable=False, server_default="12"))
    context.assert_("ALTER TABLE t1 ADD COLUMN c1 INTEGER DEFAULT '12' NOT NULL")

def test_add_column_fk():
    context = _op_fixture()
    op.add_column('t1', Column('c1', Integer, ForeignKey('c2.id'), nullable=False))
    context.assert_(
        "ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL",
        "ALTER TABLE t1 ADD FOREIGN KEY(c1) REFERENCES c2 (id)"
    )

def test_add_column_fk_self_referential():
    context = _op_fixture()
    op.add_column('t1', Column('c1', Integer, ForeignKey('t1.c2'), nullable=False))
    context.assert_(
        "ALTER TABLE t1 ADD COLUMN c1 INTEGER NOT NULL",
        "ALTER TABLE t1 ADD FOREIGN KEY(c1) REFERENCES t1 (c2)"
    )

def test_drop_column():
    context = _op_fixture()
    op.drop_column('t1', 'c1')
    context.assert_("ALTER TABLE t1 DROP COLUMN c1")

def test_alter_column_nullable():
    context = _op_fixture()
    op.alter_column("t", "c", nullable=True)
    context.assert_(
        # TODO: not sure if this is supposed to be SET NULL
        "ALTER TABLE t ALTER COLUMN c NULL"
    )

def test_alter_column_not_nullable():
    context = _op_fixture()
    op.alter_column("t", "c", nullable=False)
    context.assert_(
        # TODO: not sure if this is PG only or standard 
        # SQL
        "ALTER TABLE t ALTER COLUMN c SET NOT NULL"
    )

def test_alter_column_rename():
    context = _op_fixture()
    op.alter_column("t", "c", name="x")
    context.assert_(
        "ALTER TABLE t RENAME c TO x"
    )

def test_add_foreign_key():
    context = _op_fixture()
    op.create_foreign_key('fk_test', 't1', 't2', 
                    ['foo', 'bar'], ['bat', 'hoho'])
    context.assert_(
        "ALTER TABLE t1 ADD CONSTRAINT fk_test FOREIGN KEY(foo, bar) "
            "REFERENCES t2 (bat, hoho)"
    )

def test_add_unique_constraint():
    context = _op_fixture()
    op.create_unique_constraint('uk_test', 't1', ['foo', 'bar'])
    context.assert_(
        "ALTER TABLE t1 ADD CONSTRAINT uk_test UNIQUE (foo, bar)"
    )

def test_create_index():
    context = _op_fixture()
    op.create_index('ik_test', 't1', ['foo', 'bar'])
    context.assert_(
        "CREATE INDEX ik_test ON t1 (foo, bar)"
    )


def test_drop_index():
    context = _op_fixture()
    op.drop_index('ik_test')
    context.assert_(
        "DROP INDEX ik_test"
    )

def test_drop_table():
    context = _op_fixture()
    op.drop_table('tb_test')
    context.assert_(
        "DROP TABLE tb_test"
    )

def test_create_table_fk_and_schema():
    context = _op_fixture()
    op.create_table(
        "some_table", 
        Column('id', Integer, primary_key=True),
        Column('foo_id', Integer, ForeignKey('foo.id')),
        schema='schema'
    )
    context.assert_(
        "CREATE TABLE schema.some_table ("
            "id INTEGER NOT NULL, "
            "foo_id INTEGER, "
            "PRIMARY KEY (id), "
            "FOREIGN KEY(foo_id) REFERENCES foo (id))"
    )

def test_create_table_two_fk():
    context = _op_fixture()
    op.create_table(
        "some_table", 
        Column('id', Integer, primary_key=True),
        Column('foo_id', Integer, ForeignKey('foo.id')),
        Column('foo_bar', Integer, ForeignKey('foo.bar')),
    )
    context.assert_(
        "CREATE TABLE some_table ("
            "id INTEGER NOT NULL, "
            "foo_id INTEGER, "
            "foo_bar INTEGER, "
            "PRIMARY KEY (id), "
            "FOREIGN KEY(foo_id) REFERENCES foo (id), "
            "FOREIGN KEY(foo_bar) REFERENCES foo (bar))"
    )

def test_inline_literal():
    context = _op_fixture()
    from sqlalchemy.sql import table, column
    from sqlalchemy import String, Integer

    account = table('account', 
        column('name', String),
        column('id', Integer)
    )
    op.execute(
        account.update().\
            where(account.c.name==op.inline_literal('account 1')).\
            values({'name':op.inline_literal('account 2')})
            )
    op.execute(
        account.update().\
            where(account.c.id==op.inline_literal(1)).\
            values({'id':op.inline_literal(2)})
            )
    context.assert_(
        "UPDATE account SET name='account 2' WHERE account.name = 'account 1'",
        "UPDATE account SET id=2 WHERE account.id = 1"
    )
