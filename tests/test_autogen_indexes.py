import sys
from unittest import TestCase

from sqlalchemy import MetaData, Column, Table, Integer, String, Text, \
    Numeric, DATETIME, INTEGER, \
    TypeDecorator, Unicode, Enum,\
    UniqueConstraint, Boolean, \
    PrimaryKeyConstraint, Index, func, ForeignKeyConstraint,\
    ForeignKey
from sqlalchemy.schema import AddConstraint
from . import sqlite_db, eq_, db_for_dialect

py3k = sys.version_info >= (3, )

from .test_autogenerate import AutogenFixtureTest

class AutogenerateUniqueIndexTest(AutogenFixtureTest, TestCase):
    reports_unique_constraints = True

    def test_index_flag_becomes_named_unique_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('user', m1,
            Column('id', Integer, primary_key=True),
            Column('name', String(50), nullable=False, index=True),
            Column('a1', String(10), server_default="x")
        )

        Table('user', m2,
            Column('id', Integer, primary_key=True),
            Column('name', String(50), nullable=False),
            Column('a1', String(10), server_default="x"),
            UniqueConstraint("name", name="uq_user_name")
        )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            eq_(diffs[0][0], "add_constraint")
            eq_(diffs[0][1].name, "uq_user_name")

            eq_(diffs[1][0], "remove_index")
            eq_(diffs[1][1].name, "ix_user_name")
        else:
            eq_(diffs[0][0], "remove_index")
            eq_(diffs[0][1].name, "ix_user_name")


    def test_add_unique_constraint(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('address', m1,
            Column('id', Integer, primary_key=True),
            Column('email_address', String(100), nullable=False),
            Column('qpr', String(10), index=True),
        )
        Table('address', m2,
            Column('id', Integer, primary_key=True),
            Column('email_address', String(100), nullable=False),
            Column('qpr', String(10), index=True),
            UniqueConstraint("email_address", name="uq_email_address")
        )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            eq_(diffs[0][0], "add_constraint")
            eq_(diffs[0][1].name, "uq_email_address")
        else:
            eq_(diffs, [])


    def test_index_becomes_unique(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('order', m1,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
            UniqueConstraint('order_id', 'user_id',
                name='order_order_id_user_id_unique'
            ),
            Index('order_user_id_amount_idx', 'user_id', 'amount')
        )

        Table('order', m2,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
            UniqueConstraint('order_id', 'user_id',
                name='order_order_id_user_id_unique'
            ),
            Index('order_user_id_amount_idx', 'user_id', 'amount', unique=True),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs[0][0], "remove_index")
        eq_(diffs[0][1].name, "order_user_id_amount_idx")
        eq_(diffs[0][1].unique, False)

        eq_(diffs[1][0], "add_index")
        eq_(diffs[1][1].name, "order_user_id_amount_idx")
        eq_(diffs[1][1].unique, True)



    def test_mismatch_db_named_col_flag(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('item', m1,
                Column('x', Integer),
                UniqueConstraint('x', name="db_generated_name")
            )

        # test mismatch between unique=True and
        # named uq constraint
        Table('item', m2,
                Column('x', Integer, unique=True)
            )

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_new_table_added(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('extra', m2,
                Column('foo', Integer, index=True),
                Column('bar', Integer),
                Index('newtable_idx', 'bar')
            )

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")

        eq_(diffs[1][0], "add_index")
        eq_(diffs[1][1].name, "ix_extra_foo")

        eq_(diffs[2][0], "add_index")
        eq_(diffs[2][1].name, "newtable_idx")


    def test_named_cols_changed(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('col_change', m1,
                Column('x', Integer),
                Column('y', Integer),
                UniqueConstraint('x', name="nochange")
            )
        Table('col_change', m2,
                Column('x', Integer),
                Column('y', Integer),
                UniqueConstraint('x', 'y', name="nochange")
            )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            eq_(diffs[0][0], "remove_constraint")
            eq_(diffs[0][1].name, "nochange")

            eq_(diffs[1][0], "add_constraint")
            eq_(diffs[1][1].name, "nochange")
        else:
            eq_(diffs, [])

    def test_nothing_changed_one(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('nothing_changed', m1,
            Column('x', String(20), unique=True, index=True)
            )

        Table('nothing_changed', m2,
            Column('x', String(20), unique=True, index=True)
            )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])


    def test_nothing_changed_two(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('nothing_changed', m1,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20), unique=True),
            mysql_engine='InnoDB'
            )
        Table('nothing_changed_related', m1,
            Column('id1', Integer),
            Column('id2', Integer),
            ForeignKeyConstraint(['id1', 'id2'],
                    ['nothing_changed.id1', 'nothing_changed.id2']),
            mysql_engine='InnoDB'
            )

        Table('nothing_changed', m2,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20), unique=True),
            mysql_engine='InnoDB'
            )
        Table('nothing_changed_related', m2,
            Column('id1', Integer),
            Column('id2', Integer),
            ForeignKeyConstraint(['id1', 'id2'],
                    ['nothing_changed.id1', 'nothing_changed.id2']),
            mysql_engine='InnoDB'
            )


        diffs = self._fixture(m1, m2)
        eq_(diffs, [])



    def test_nothing_changed_index_named_as_column(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('nothing_changed', m1,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20)),
            Index('x', 'x')
            )

        Table('nothing_changed', m2,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20)),
            Index('x', 'x')
            )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_nothing_changed_implicit_fk_index_named(self):
        m1 = MetaData()
        m2 = MetaData()

        Table("nothing_changed", m1,
                Column('id', Integer, primary_key=True),
                Column('other_id',
                            ForeignKey('nc2.id',
                                name='fk_my_table_other_table'
                                ),
                                nullable=False),
                Column('foo', Integer),
                mysql_engine='InnoDB')
        Table('nc2', m1,
                Column('id', Integer, primary_key=True),
                mysql_engine='InnoDB')

        Table("nothing_changed", m2,
                Column('id', Integer, primary_key=True),
                Column('other_id', ForeignKey('nc2.id',
                                    name='fk_my_table_other_table'),
                                    nullable=False),
                Column('foo', Integer),
                mysql_engine='InnoDB')
        Table('nc2', m2,
                Column('id', Integer, primary_key=True),
                mysql_engine='InnoDB')
        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_new_idx_index_named_as_column(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('new_idx', m1,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20)),
            )

        idx = Index('x', 'x')
        Table('new_idx', m2,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20)),
            idx
            )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [('add_index', idx)])

    def test_removed_idx_index_named_as_column(self):
        m1 = MetaData()
        m2 = MetaData()

        idx = Index('x', 'x')
        Table('new_idx', m1,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20)),
            idx
            )

        Table('new_idx', m2,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20))
            )

        diffs = self._fixture(m1, m2)
        eq_(diffs[0][0], 'remove_index')

    def test_unnamed_cols_changed(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('col_change', m1,
                Column('x', Integer),
                Column('y', Integer),
                UniqueConstraint('x')
            )
        Table('col_change', m2,
                Column('x', Integer),
                Column('y', Integer),
                UniqueConstraint('x', 'y')
            )

        diffs = self._fixture(m1, m2)

        diffs = set((cmd,
                    ('x' in obj.name) if obj.name is not None else False)
                    for cmd, obj in diffs)
        if self.reports_unnamed_constraints:
            assert ("remove_constraint", True) in diffs
            assert ("add_constraint", False) in diffs



    def test_remove_named_unique_index(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('remove_idx', m1,
                Column('x', Integer),
                Index('xidx', 'x', unique=True)
            )
        Table('remove_idx', m2,
                Column('x', Integer),
            )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            diffs = set((cmd, obj.name) for cmd, obj in diffs)
            assert ("remove_index", "xidx") in diffs
        else:
            eq_(diffs, [])


    def test_remove_named_unique_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('remove_idx', m1,
                Column('x', Integer),
                UniqueConstraint('x', name='xidx')
            )
        Table('remove_idx', m2,
                Column('x', Integer),
            )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            diffs = ((cmd, obj.name) for cmd, obj in diffs)
            assert ("remove_constraint", "xidx") in diffs
        else:
            eq_(diffs, [])

    def test_dont_add_uq_on_table_create(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('no_uq', m2, Column('x', String(50), unique=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 1)
        assert UniqueConstraint in set(type(c) for c in diffs[0][1].constraints)

    def test_add_uq_ix_on_table_create(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m2, Column('x', String(50), unique=True, index=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 2)
        assert UniqueConstraint not in set(type(c) for c in diffs[0][1].constraints)
        eq_(diffs[1][0], "add_index")
        eq_(diffs[1][1].unique, True)

    def test_add_ix_on_table_create(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m2, Column('x', String(50), index=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 2)
        assert UniqueConstraint not in set(type(c) for c in diffs[0][1].constraints)
        eq_(diffs[1][0], "add_index")
        eq_(diffs[1][1].unique, False)

    def test_add_idx_non_col(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m1, Column('x', String(50)))
        t2 = Table('add_ix', m2, Column('x', String(50)))
        Index('foo_idx', t2.c.x.desc())
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_index")

    def test_unchanged_idx_non_col(self):
        m1 = MetaData()
        m2 = MetaData()
        t1 = Table('add_ix', m1, Column('x', String(50)))
        Index('foo_idx', t1.c.x.desc())
        t2 = Table('add_ix', m2, Column('x', String(50)))
        Index('foo_idx', t2.c.x.desc())
        diffs = self._fixture(m1, m2)

        eq_(diffs, [])



class PGUniqueIndexTest(AutogenerateUniqueIndexTest):
    reports_unnamed_constraints = True

    @classmethod
    def _get_bind(cls):
        return db_for_dialect('postgresql')

    def test_idx_added_schema(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m1, Column('x', String(50)), schema="test_schema")
        Table('add_ix', m2, Column('x', String(50)),
                Index('ix_1', 'x'), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs[0][0], "add_index")
        eq_(diffs[0][1].name, 'ix_1')

    def test_idx_unchanged_schema(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m1, Column('x', String(50)), Index('ix_1', 'x'),
                    schema="test_schema")
        Table('add_ix', m2, Column('x', String(50)),
                Index('ix_1', 'x'), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs, [])

    def test_uq_added_schema(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_uq', m1, Column('x', String(50)), schema="test_schema")
        Table('add_uq', m2, Column('x', String(50)),
                UniqueConstraint('x', name='ix_1'), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, 'ix_1')

    def test_uq_unchanged_schema(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_uq', m1, Column('x', String(50)),
                    UniqueConstraint('x', name='ix_1'),
                    schema="test_schema")
        Table('add_uq', m2, Column('x', String(50)),
                    UniqueConstraint('x', name='ix_1'),
                schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs, [])

    def test_same_tname_two_schemas(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('add_ix', m1, Column('x', String(50)), Index('ix_1', 'x'))

        Table('add_ix', m2, Column('x', String(50)), Index('ix_1', 'x'))
        Table('add_ix', m2, Column('x', String(50)), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 1)


class MySQLUniqueIndexTest(AutogenerateUniqueIndexTest):
    reports_unnamed_constraints = True

    def test_removed_idx_index_named_as_column(self):
        try:
            super(MySQLUniqueIndexTest,
                                self).test_removed_idx_index_named_as_column()
        except IndexError:
            assert True
        else:
            assert False, "unexpected success"

    @classmethod
    def _get_bind(cls):
        return db_for_dialect('mysql')

class NoUqReflectionIndexTest(AutogenerateUniqueIndexTest):
    reports_unique_constraints = False

    @classmethod
    def _get_bind(cls):
        eng = sqlite_db()

        def unimpl(*arg, **kw):
            raise NotImplementedError()
        eng.dialect.get_unique_constraints = unimpl
        return eng

    def test_unique_not_reported(self):
        m1 = MetaData()
        Table('order', m1,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
            UniqueConstraint('order_id', 'user_id',
                name='order_order_id_user_id_unique'
            )
        )

        diffs = self._fixture(m1, m1)
        eq_(diffs, [])

    def test_remove_unique_index_not_reported(self):
        m1 = MetaData()
        Table('order', m1,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
            Index('oid_ix', 'order_id', 'user_id',
                unique=True
            )
        )
        m2 = MetaData()
        Table('order', m2,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_remove_plain_index_is_reported(self):
        m1 = MetaData()
        Table('order', m1,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
            Index('oid_ix', 'order_id', 'user_id')
        )
        m2 = MetaData()
        Table('order', m2,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True),
            Column('user_id', Integer),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs[0][0], 'remove_index')


class NoUqReportsIndAsUqTest(NoUqReflectionIndexTest):
    """this test suite simulates the condition where:

    a. the dialect doesn't report unique constraints

    b. the dialect returns unique constraints within the indexes list.

    Currently the mssql dialect does this, but here we force this
    condition so that we can test the behavior regardless of if/when
    mssql supports unique constraint reflection.

    """

    @classmethod
    def _get_bind(cls):
        eng = sqlite_db()

        _get_unique_constraints = eng.dialect.get_unique_constraints
        _get_indexes = eng.dialect.get_indexes

        def unimpl(*arg, **kw):
            raise NotImplementedError()

        def get_indexes(self, connection, tablename, **kw):
            indexes = _get_indexes(self, connection, tablename, **kw)
            for uq in _get_unique_constraints(
                            self, connection, tablename, **kw
                            ):
                uq['unique'] = True
                indexes.append(uq)
            return indexes

        eng.dialect.get_unique_constraints = unimpl
        eng.dialect.get_indexes = get_indexes
        return eng

