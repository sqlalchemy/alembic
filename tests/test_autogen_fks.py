import sys
from alembic.testing import TestBase, config

from sqlalchemy import MetaData, Column, Table, Integer, String, \
    ForeignKeyConstraint
from alembic.testing import eq_

py3k = sys.version_info >= (3, )

from .test_autogenerate import AutogenFixtureTest


class AutogenerateForeignKeysTest(AutogenFixtureTest, TestBase):
    __backend__ = True

    def test_remove_fk(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('table', m1,
              Column('test', String(10), primary_key=True),
              mysql_engine='InnoDB')

        Table('user', m1,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', String(10), server_default="x"),
              Column('test2', String(10)),
              ForeignKeyConstraint(['test2'], ['table.test']),
              mysql_engine='InnoDB')

        Table('table', m2,
              Column('test', String(10), primary_key=True),
              mysql_engine='InnoDB')

        Table('user', m2,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', String(10), server_default="x"),
              Column('test2', String(10)),
              mysql_engine='InnoDB'
              )

        diffs = self._fixture(m1, m2)

        self._assert_fk_diff(
            diffs[0], "remove_fk",
            "user", ['test2'],
            'table', ['test'],
            conditional_name="servergenerated"
        )

    def test_add_fk(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('table', m1,
              Column('id', Integer, primary_key=True),
              Column('test', String(10)),
              mysql_engine='InnoDB')

        Table('user', m1,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', String(10), server_default="x"),
              Column('test2', String(10)),
              mysql_engine='InnoDB')

        Table('table', m2,
              Column('id', Integer, primary_key=True),
              Column('test', String(10)),
              mysql_engine='InnoDB')

        Table('user', m2,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', String(10), server_default="x"),
              Column('test2', String(10)),
              ForeignKeyConstraint(['test2'], ['table.test']),
              mysql_engine='InnoDB')

        diffs = self._fixture(m1, m2)

        self._assert_fk_diff(
            diffs[0], "add_fk",
            "user", ["test2"],
            "table", ["test"]
        )

    def test_no_change(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('table', m1,
              Column('id', Integer, primary_key=True),
              Column('test', String(10)),
              mysql_engine='InnoDB')

        Table('user', m1,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', String(10), server_default="x"),
              Column('test2', Integer),
              ForeignKeyConstraint(['test2'], ['table.id']),
              mysql_engine='InnoDB')

        Table('table', m2,
              Column('id', Integer, primary_key=True),
              Column('test', String(10)),
              mysql_engine='InnoDB')

        Table('user', m2,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', String(10), server_default="x"),
              Column('test2', Integer),
              ForeignKeyConstraint(['test2'], ['table.id']),
              mysql_engine='InnoDB')

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_no_change_composite_fk(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('table', m1,
              Column('id_1', String(10), primary_key=True),
              Column('id_2', String(10), primary_key=True),
              mysql_engine='InnoDB')

        Table('user', m1,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', String(10), server_default="x"),
              Column('other_id_1', String(10)),
              Column('other_id_2', String(10)),
              ForeignKeyConstraint(['other_id_1', 'other_id_2'],
                                   ['table.id_1', 'table.id_2']),
              mysql_engine='InnoDB')

        Table('table', m2,
              Column('id_1', String(10), primary_key=True),
              Column('id_2', String(10), primary_key=True),
              mysql_engine='InnoDB'
              )

        Table('user', m2,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', String(10), server_default="x"),
              Column('other_id_1', String(10)),
              Column('other_id_2', String(10)),
              ForeignKeyConstraint(['other_id_1', 'other_id_2'],
                                   ['table.id_1', 'table.id_2']),
              mysql_engine='InnoDB')

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_add_composite_fk_with_name(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('table', m1,
              Column('id_1', String(10), primary_key=True),
              Column('id_2', String(10), primary_key=True),
              mysql_engine='InnoDB')

        Table('user', m1,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', String(10), server_default="x"),
              Column('other_id_1', String(10)),
              Column('other_id_2', String(10)),
              mysql_engine='InnoDB')

        Table('table', m2,
              Column('id_1', String(10), primary_key=True),
              Column('id_2', String(10), primary_key=True),
              mysql_engine='InnoDB')

        Table('user', m2,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', String(10), server_default="x"),
              Column('other_id_1', String(10)),
              Column('other_id_2', String(10)),
              ForeignKeyConstraint(['other_id_1', 'other_id_2'],
                                   ['table.id_1', 'table.id_2'],
                                   name='fk_test_name'),
              mysql_engine='InnoDB')

        diffs = self._fixture(m1, m2)

        self._assert_fk_diff(
            diffs[0], "add_fk",
            "user", ['other_id_1', 'other_id_2'],
            'table', ['id_1', 'id_2'],
            name="fk_test_name"
        )

    def test_remove_composite_fk(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('table', m1,
              Column('id_1', String(10), primary_key=True),
              Column('id_2', String(10), primary_key=True),
              mysql_engine='InnoDB')

        Table('user', m1,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', String(10), server_default="x"),
              Column('other_id_1', String(10)),
              Column('other_id_2', String(10)),
              ForeignKeyConstraint(['other_id_1', 'other_id_2'],
                                   ['table.id_1', 'table.id_2'],
                                   name='fk_test_name'),
              mysql_engine='InnoDB')

        Table('table', m2,
              Column('id_1', String(10), primary_key=True),
              Column('id_2', String(10), primary_key=True),
              mysql_engine='InnoDB')

        Table('user', m2,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', String(10), server_default="x"),
              Column('other_id_1', String(10)),
              Column('other_id_2', String(10)),
              mysql_engine='InnoDB')

        diffs = self._fixture(m1, m2)

        self._assert_fk_diff(
            diffs[0], "remove_fk",
            "user", ['other_id_1', 'other_id_2'],
            "table", ['id_1', 'id_2'],
            conditional_name="fk_test_name"
        )

    def test_add_fk_colkeys(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('table', m1,
              Column('id_1', String(10), primary_key=True),
              Column('id_2', String(10), primary_key=True),
              mysql_engine='InnoDB')

        Table('user', m1,
              Column('id', Integer, primary_key=True),
              Column('other_id_1', String(10)),
              Column('other_id_2', String(10)),
              mysql_engine='InnoDB')

        Table('table', m2,
              Column('id_1', String(10), key='tid1', primary_key=True),
              Column('id_2', String(10), key='tid2', primary_key=True),
              mysql_engine='InnoDB')

        Table('user', m2,
              Column('id', Integer, primary_key=True),
              Column('other_id_1', String(10), key='oid1'),
              Column('other_id_2', String(10), key='oid2'),
              ForeignKeyConstraint(['oid1', 'oid2'],
                                   ['table.tid1', 'table.tid2'],
                                   name='fk_test_name'),
              mysql_engine='InnoDB')

        diffs = self._fixture(m1, m2)

        self._assert_fk_diff(
            diffs[0], "add_fk",
            "user", ['other_id_1', 'other_id_2'],
            'table', ['id_1', 'id_2'],
            name="fk_test_name"
        )

    def test_no_change_colkeys(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('table', m1,
              Column('id_1', String(10), primary_key=True),
              Column('id_2', String(10), primary_key=True),
              mysql_engine='InnoDB')

        Table('user', m1,
              Column('id', Integer, primary_key=True),
              Column('other_id_1', String(10)),
              Column('other_id_2', String(10)),
              ForeignKeyConstraint(['other_id_1', 'other_id_2'],
                                   ['table.id_1', 'table.id_2']),
              mysql_engine='InnoDB')

        Table('table', m2,
              Column('id_1', String(10), key='tid1', primary_key=True),
              Column('id_2', String(10), key='tid2', primary_key=True),
              mysql_engine='InnoDB')

        Table('user', m2,
              Column('id', Integer, primary_key=True),
              Column('other_id_1', String(10), key='oid1'),
              Column('other_id_2', String(10), key='oid2'),
              ForeignKeyConstraint(['oid1', 'oid2'],
                                   ['table.tid1', 'table.tid2']),
              mysql_engine='InnoDB')

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])


class IncludeHooksTest(AutogenFixtureTest, TestBase):
    __backend__ = True
    __requires__ = 'fk_names',

    def test_remove_connection_fk(self):
        m1 = MetaData()
        m2 = MetaData()

        ref = Table(
            'ref', m1, Column('id', Integer, primary_key=True),
            mysql_engine='InnoDB')
        t1 = Table(
            't', m1, Column('x', Integer), Column('y', Integer),
            mysql_engine='InnoDB')
        t1.append_constraint(
            ForeignKeyConstraint([t1.c.x], [ref.c.id], name="fk1")
        )
        t1.append_constraint(
            ForeignKeyConstraint([t1.c.y], [ref.c.id], name="fk2")
        )

        ref = Table(
            'ref', m2, Column('id', Integer, primary_key=True),
            mysql_engine='InnoDB')
        Table(
            't', m2, Column('x', Integer), Column('y', Integer),
            mysql_engine='InnoDB')

        def include_object(object_, name, type_, reflected, compare_to):
            return not (
                isinstance(object_, ForeignKeyConstraint) and
                type_ == 'foreign_key_constraint'
                and reflected and name == 'fk1')

        diffs = self._fixture(m1, m2, object_filters=[include_object])

        self._assert_fk_diff(
            diffs[0], "remove_fk",
            't', ['y'], 'ref', ['id'],
            conditional_name='fk2'
        )
        eq_(len(diffs), 1)

    def test_add_metadata_fk(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            'ref', m1,
            Column('id', Integer, primary_key=True), mysql_engine='InnoDB')
        Table(
            't', m1,
            Column('x', Integer), Column('y', Integer), mysql_engine='InnoDB')

        ref = Table(
            'ref', m2, Column('id', Integer, primary_key=True),
            mysql_engine='InnoDB')
        t2 = Table(
            't', m2, Column('x', Integer), Column('y', Integer),
            mysql_engine='InnoDB')
        t2.append_constraint(
            ForeignKeyConstraint([t2.c.x], [ref.c.id], name="fk1")
        )
        t2.append_constraint(
            ForeignKeyConstraint([t2.c.y], [ref.c.id], name="fk2")
        )

        def include_object(object_, name, type_, reflected, compare_to):
            return not (
                isinstance(object_, ForeignKeyConstraint) and
                type_ == 'foreign_key_constraint'
                and not reflected and name == 'fk1')

        diffs = self._fixture(m1, m2, object_filters=[include_object])

        self._assert_fk_diff(
            diffs[0], "add_fk",
            't', ['y'], 'ref', ['id'],
            name='fk2'
        )
        eq_(len(diffs), 1)

    def test_change_fk(self):
        m1 = MetaData()
        m2 = MetaData()

        r1a = Table(
            'ref_a', m1,
            Column('a', Integer, primary_key=True),
            mysql_engine='InnoDB'
        )
        Table(
            'ref_b', m1,
            Column('a', Integer, primary_key=True),
            Column('b', Integer, primary_key=True),
            mysql_engine='InnoDB'
        )
        t1 = Table(
            't', m1, Column('x', Integer),
            Column('y', Integer), Column('z', Integer),
            mysql_engine='InnoDB')
        t1.append_constraint(
            ForeignKeyConstraint([t1.c.x], [r1a.c.a], name="fk1")
        )
        t1.append_constraint(
            ForeignKeyConstraint([t1.c.y], [r1a.c.a], name="fk2")
        )

        Table(
            'ref_a', m2,
            Column('a', Integer, primary_key=True),
            mysql_engine='InnoDB'
        )
        r2b = Table(
            'ref_b', m2,
            Column('a', Integer, primary_key=True),
            Column('b', Integer, primary_key=True),
            mysql_engine='InnoDB'
        )
        t2 = Table(
            't', m2, Column('x', Integer),
            Column('y', Integer), Column('z', Integer),
            mysql_engine='InnoDB')
        t2.append_constraint(
            ForeignKeyConstraint(
                [t2.c.x, t2.c.z], [r2b.c.a, r2b.c.b], name="fk1")
        )
        t2.append_constraint(
            ForeignKeyConstraint(
                [t2.c.y, t2.c.z], [r2b.c.a, r2b.c.b], name="fk2")
        )

        def include_object(object_, name, type_, reflected, compare_to):
            return not (
                isinstance(object_, ForeignKeyConstraint) and
                type_ == 'foreign_key_constraint'
                and name == 'fk1'
            )

        diffs = self._fixture(m1, m2, object_filters=[include_object])

        self._assert_fk_diff(
            diffs[0], "remove_fk",
            't', ['y'], 'ref_a', ['a'],
            name='fk2'
        )
        self._assert_fk_diff(
            diffs[1], "add_fk",
            't', ['y', 'z'], 'ref_b', ['a', 'b'],
            name='fk2'
        )
        eq_(len(diffs), 2)
