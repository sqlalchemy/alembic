import sys
from alembic.testing import TestBase
from alembic.testing import config
from alembic.testing import assertions

from sqlalchemy import MetaData, Column, Table, Integer, String, \
    Numeric, UniqueConstraint, Index, ForeignKeyConstraint,\
    ForeignKey, func
from alembic.testing import engines
from alembic.testing import eq_
from alembic.testing.env import staging_env

py3k = sys.version_info >= (3, )

from ._autogen_fixtures import AutogenFixtureTest


class NoUqReflection(object):
    __requires__ = ()

    def setUp(self):
        staging_env()
        self.bind = eng = engines.testing_engine()

        def unimpl(*arg, **kw):
            raise NotImplementedError()
        eng.dialect.get_unique_constraints = unimpl

    @config.requirements.fail_before_sqla_083
    def test_add_ix_on_table_create(self):
        return super(NoUqReflection, self).test_add_ix_on_table_create()

    @config.requirements.fail_before_sqla_080
    def test_add_idx_non_col(self):
        return super(NoUqReflection, self).test_add_idx_non_col()


class AutogenerateUniqueIndexTest(AutogenFixtureTest, TestBase):
    reports_unique_constraints = True
    reports_unique_constraints_as_indexes = False

    __requires__ = ('unique_constraint_reflection', )
    __only_on__ = 'sqlite'

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

    def test_unique_flag_nothing_changed(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('unq_idx', m1,
              Column('id', Integer, primary_key=True),
              Column('x', String(20)),
              Index('x', 'x', unique=True)
              )

        Table('unq_idx', m2,
              Column('id', Integer, primary_key=True),
              Column('x', String(20)),
              Index('x', 'x', unique=True)
              )

        diffs = self._fixture(m1, m2)
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
              Index(
                  'order_user_id_amount_idx', 'user_id',
                  'amount', unique=True),
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
              ForeignKeyConstraint(
                  ['id1', 'id2'],
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
              ForeignKeyConstraint(
                  ['id1', 'id2'],
                  ['nothing_changed.id1', 'nothing_changed.id2']),
              mysql_engine='InnoDB'
              )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_nothing_changed_unique_w_colkeys(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('nothing_changed', m1,
              Column('x', String(20), key='nx'),
              UniqueConstraint('nx')
              )

        Table('nothing_changed', m2,
              Column('x', String(20), key='nx'),
              UniqueConstraint('nx')
              )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_nothing_changed_index_w_colkeys(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('nothing_changed', m1,
              Column('x', String(20), key='nx'),
              Index('foobar', 'nx')
              )

        Table('nothing_changed', m2,
              Column('x', String(20), key='nx'),
              Index('foobar', 'nx')
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

    def test_nothing_changed_implicit_composite_fk_index_named(self):
        m1 = MetaData()
        m2 = MetaData()

        Table("nothing_changed", m1,
              Column('id', Integer, primary_key=True),
              Column('other_id_1', Integer),
              Column('other_id_2', Integer),
              Column('foo', Integer),
              ForeignKeyConstraint(
                  ['other_id_1', 'other_id_2'], ['nc2.id1', 'nc2.id2'],
                  name='fk_my_table_other_table'
              ),
              mysql_engine='InnoDB')
        Table('nc2', m1,
              Column('id1', Integer, primary_key=True),
              Column('id2', Integer, primary_key=True),
              mysql_engine='InnoDB')

        Table("nothing_changed", m2,
              Column('id', Integer, primary_key=True),
              Column('other_id_1', Integer),
              Column('other_id_2', Integer),
              Column('foo', Integer),
              ForeignKeyConstraint(
                  ['other_id_1', 'other_id_2'], ['nc2.id1', 'nc2.id2'],
                  name='fk_my_table_other_table'
              ),
              mysql_engine='InnoDB')
        Table('nc2', m2,
              Column('id1', Integer, primary_key=True),
              Column('id2', Integer, primary_key=True),
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

    def test_drop_table_w_indexes(self):
        m1 = MetaData()
        m2 = MetaData()

        t = Table(
            'some_table', m1,
            Column('id', Integer, primary_key=True),
            Column('x', String(20)),
            Column('y', String(20)),
        )
        Index('xy_idx', t.c.x, t.c.y)
        Index('y_idx', t.c.y)

        diffs = self._fixture(m1, m2)
        eq_(diffs[0][0], 'remove_index')
        eq_(diffs[1][0], 'remove_index')
        eq_(diffs[2][0], 'remove_table')

        eq_(
            set([diffs[0][1].name, diffs[1][1].name]),
            set(['xy_idx', 'y_idx'])
        )

    # this simply doesn't fully work before we had
    # effective deduping of indexes/uniques.
    @config.requirements.sqlalchemy_100
    def test_drop_table_w_uq_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            'some_table', m1,
            Column('id', Integer, primary_key=True),
            Column('x', String(20)),
            Column('y', String(20)),
            UniqueConstraint('y', name='uq_y')
        )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints_as_indexes:
            # for MySQL this UQ will look like an index, so
            # make sure it at least sets it up correctly
            eq_(diffs[0][0], 'remove_index')
            eq_(diffs[1][0], 'remove_table')
            eq_(len(diffs), 2)

            constraints = [c for c in diffs[1][1].constraints
                           if isinstance(c, UniqueConstraint)]
            eq_(len(constraints), 0)
        else:
            eq_(diffs[0][0], 'remove_table')
            eq_(len(diffs), 1)

            constraints = [c for c in diffs[0][1].constraints
                           if isinstance(c, UniqueConstraint)]
            if self.reports_unique_constraints:
                eq_(len(constraints), 1)

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
            if self.reports_unique_constraints_as_indexes:
                eq_(
                    diffs,
                    set([("remove_index", True), ("add_constraint", False)])
                )
            else:
                eq_(
                    diffs,
                    set([("remove_constraint", True),
                         ("add_constraint", False)])
                )

    def test_remove_named_unique_index(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('remove_idx', m1,
              Column('x', Integer),
              Index('xidx', 'x', unique=True)
              )
        Table('remove_idx', m2,
              Column('x', Integer)
              )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            diffs = set((cmd, obj.name) for cmd, obj in diffs)
            eq_(diffs, set([("remove_index", "xidx")]))
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
            diffs = set((cmd, obj.name) for cmd, obj in diffs)
            if self.reports_unique_constraints_as_indexes:
                eq_(diffs, set([("remove_index", "xidx")]))
            else:
                eq_(diffs, set([("remove_constraint", "xidx")]))
        else:
            eq_(diffs, [])

    def test_dont_add_uq_on_table_create(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('no_uq', m2, Column('x', String(50), unique=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 1)
        assert UniqueConstraint in set(
            type(c) for c in diffs[0][1].constraints)

    def test_add_uq_ix_on_table_create(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m2, Column('x', String(50), unique=True, index=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 2)
        assert UniqueConstraint not in set(
            type(c) for c in diffs[0][1].constraints)
        eq_(diffs[1][0], "add_index")
        eq_(diffs[1][1].unique, True)

    def test_add_ix_on_table_create(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m2, Column('x', String(50), index=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 2)
        assert UniqueConstraint not in set(
            type(c) for c in diffs[0][1].constraints)
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

    # fails in the 0.8 series where we have truncation rules,
    # but no control over quoting. passes in 0.7.9 where we don't have
    # truncation rules either.    dropping these ancient versions
    # is long overdue.

    @config.requirements.sqlalchemy_09
    def test_unchanged_case_sensitive_implicit_idx(self):
        m1 = MetaData()
        m2 = MetaData()
        Table('add_ix', m1, Column('regNumber', String(50), index=True))
        Table('add_ix', m2, Column('regNumber', String(50), index=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    @config.requirements.sqlalchemy_09
    def test_unchanged_case_sensitive_explicit_idx(self):
        m1 = MetaData()
        m2 = MetaData()
        t1 = Table('add_ix', m1, Column('reg_number', String(50)))
        Index('regNumber_idx', t1.c.reg_number)
        t2 = Table('add_ix', m2, Column('reg_number', String(50)))
        Index('regNumber_idx', t2.c.reg_number)

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])


class PGUniqueIndexTest(AutogenerateUniqueIndexTest):
    reports_unnamed_constraints = True
    __only_on__ = "postgresql"
    __backend__ = True

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

    @config.requirements.sqlalchemy_100
    @config.requirements.btree_gist
    def test_exclude_const_unchanged(self):
        from sqlalchemy.dialects.postgresql import TSRANGE, ExcludeConstraint

        m1 = MetaData()
        m2 = MetaData()

        Table(
            'add_excl', m1,
            Column('id', Integer, primary_key=True),
            Column('period', TSRANGE),
            ExcludeConstraint(('period', '&&'), name='quarters_period_excl')
        )

        Table(
            'add_excl', m2,
            Column('id', Integer, primary_key=True),
            Column('period', TSRANGE),
            ExcludeConstraint(('period', '&&'), name='quarters_period_excl')
        )

        diffs = self._fixture(m1, m2)
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

    def test_uq_dropped(self):
        m1 = MetaData()
        m2 = MetaData()
        Table(
            'add_uq', m1,
            Column('id', Integer, primary_key=True),
            Column('name', String),
            UniqueConstraint('name', name='uq_name')
        )
        Table(
            'add_uq', m2,
            Column('id', Integer, primary_key=True),
            Column('name', String),
        )
        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs[0][0], "remove_constraint")
        eq_(diffs[0][1].name, "uq_name")
        eq_(len(diffs), 1)

    def test_functional_ix_one(self):
        m1 = MetaData()
        m2 = MetaData()

        t1 = Table(
            'foo', m1,
            Column('id', Integer, primary_key=True),
            Column('email', String(50))
        )
        Index("email_idx", func.lower(t1.c.email), unique=True)

        t2 = Table(
            'foo', m2,
            Column('id', Integer, primary_key=True),
            Column('email', String(50))
        )
        Index("email_idx", func.lower(t2.c.email), unique=True)

        with assertions.expect_warnings(
                "Skipped unsupported reflection",
                "autogenerate skipping functional index"
        ):
            diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_functional_ix_two(self):
        m1 = MetaData()
        m2 = MetaData()

        t1 = Table(
            'foo', m1,
            Column('id', Integer, primary_key=True),
            Column('email', String(50)),
            Column('name', String(50))
        )
        Index(
            "email_idx",
            func.coalesce(t1.c.email, t1.c.name).desc(), unique=True)

        t2 = Table(
            'foo', m2,
            Column('id', Integer, primary_key=True),
            Column('email', String(50)),
            Column('name', String(50))
        )
        Index(
            "email_idx",
            func.coalesce(t2.c.email, t2.c.name).desc(), unique=True)

        with assertions.expect_warnings(
                "Skipped unsupported reflection",
                "autogenerate skipping functional index"
        ):
            diffs = self._fixture(m1, m2)
        eq_(diffs, [])


class MySQLUniqueIndexTest(AutogenerateUniqueIndexTest):
    reports_unnamed_constraints = True
    reports_unique_constraints_as_indexes = True
    __only_on__ = 'mysql'
    __backend__ = True

    def test_removed_idx_index_named_as_column(self):
        try:
            super(MySQLUniqueIndexTest,
                  self).test_removed_idx_index_named_as_column()
        except IndexError:
            assert True
        else:
            assert False, "unexpected success"


class OracleUniqueIndexTest(AutogenerateUniqueIndexTest):
    reports_unnamed_constraints = True
    reports_unique_constraints_as_indexes = True
    __only_on__ = "oracle"
    __backend__ = True

class NoUqReflectionIndexTest(NoUqReflection, AutogenerateUniqueIndexTest):
    reports_unique_constraints = False
    __only_on__ = 'sqlite'

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

    __only_on__ = 'sqlite'

    @classmethod
    def _get_bind(cls):
        eng = config.db

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


class IncludeHooksTest(AutogenFixtureTest, TestBase):
    __backend__ = True

    def test_remove_connection_index(self):
        m1 = MetaData()
        m2 = MetaData()

        t1 = Table('t', m1, Column('x', Integer), Column('y', Integer))
        Index('ix1', t1.c.x)
        Index('ix2', t1.c.y)

        Table('t', m2, Column('x', Integer), Column('y', Integer))

        def include_object(object_, name, type_, reflected, compare_to):
            if type_ == 'unique_constraint':
                return False
            return not (
                isinstance(object_, Index) and
                type_ == 'index' and reflected and name == 'ix1')

        diffs = self._fixture(m1, m2, object_filters=include_object)

        eq_(diffs[0][0], 'remove_index')
        eq_(diffs[0][1].name, 'ix2')
        eq_(len(diffs), 1)

    @config.requirements.unique_constraint_reflection
    @config.requirements.reflects_unique_constraints_unambiguously
    def test_remove_connection_uq(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            't', m1, Column('x', Integer), Column('y', Integer),
            UniqueConstraint('x', name='uq1'),
            UniqueConstraint('y', name='uq2'),
        )

        Table('t', m2, Column('x', Integer), Column('y', Integer))

        def include_object(object_, name, type_, reflected, compare_to):
            if type_ == 'index':
                return False
            return not (
                isinstance(object_, UniqueConstraint) and
                type_ == 'unique_constraint' and reflected and name == 'uq1')

        diffs = self._fixture(m1, m2, object_filters=include_object)

        eq_(diffs[0][0], 'remove_constraint')
        eq_(diffs[0][1].name, 'uq2')
        eq_(len(diffs), 1)

    def test_add_metadata_index(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('t', m1, Column('x', Integer))

        t2 = Table('t', m2, Column('x', Integer))
        Index('ix1', t2.c.x)
        Index('ix2', t2.c.x)

        def include_object(object_, name, type_, reflected, compare_to):
            return not (
                isinstance(object_, Index) and
                type_ == 'index' and not reflected and name == 'ix1')

        diffs = self._fixture(m1, m2, object_filters=include_object)

        eq_(diffs[0][0], 'add_index')
        eq_(diffs[0][1].name, 'ix2')
        eq_(len(diffs), 1)

    @config.requirements.unique_constraint_reflection
    def test_add_metadata_unique(self):
        m1 = MetaData()
        m2 = MetaData()

        Table('t', m1, Column('x', Integer))

        Table(
            't', m2, Column('x', Integer),
            UniqueConstraint('x', name='uq1'),
            UniqueConstraint('x', name='uq2')
        )

        def include_object(object_, name, type_, reflected, compare_to):
            return not (
                isinstance(object_, UniqueConstraint) and
                type_ == 'unique_constraint' and
                not reflected and name == 'uq1')

        diffs = self._fixture(m1, m2, object_filters=include_object)

        eq_(diffs[0][0], 'add_constraint')
        eq_(diffs[0][1].name, 'uq2')
        eq_(len(diffs), 1)

    def test_change_index(self):
        m1 = MetaData()
        m2 = MetaData()

        t1 = Table(
            't', m1, Column('x', Integer),
            Column('y', Integer), Column('z', Integer))
        Index('ix1', t1.c.x)
        Index('ix2', t1.c.y)

        t2 = Table(
            't', m2, Column('x', Integer),
            Column('y', Integer), Column('z', Integer))
        Index('ix1', t2.c.x, t2.c.y)
        Index('ix2', t2.c.x, t2.c.z)

        def include_object(object_, name, type_, reflected, compare_to):
            return not (
                isinstance(object_, Index) and
                type_ == 'index' and not reflected and name == 'ix1'
                and isinstance(compare_to, Index))

        diffs = self._fixture(m1, m2, object_filters=include_object)

        eq_(diffs[0][0], 'remove_index')
        eq_(diffs[0][1].name, 'ix2')
        eq_(diffs[1][0], 'add_index')
        eq_(diffs[1][1].name, 'ix2')
        eq_(len(diffs), 2)

    @config.requirements.unique_constraint_reflection
    def test_change_unique(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            't', m1, Column('x', Integer),
            Column('y', Integer), Column('z', Integer),
            UniqueConstraint('x', name='uq1'),
            UniqueConstraint('y', name='uq2')
        )

        Table(
            't', m2, Column('x', Integer), Column('y', Integer),
            Column('z', Integer),
            UniqueConstraint('x', 'z', name='uq1'),
            UniqueConstraint('y', 'z', name='uq2')
        )

        def include_object(object_, name, type_, reflected, compare_to):
            if type_ == 'index':
                return False
            return not (
                isinstance(object_, UniqueConstraint) and
                type_ == 'unique_constraint' and
                not reflected and name == 'uq1'
                and isinstance(compare_to, UniqueConstraint))

        diffs = self._fixture(m1, m2, object_filters=include_object)

        eq_(diffs[0][0], 'remove_constraint')
        eq_(diffs[0][1].name, 'uq2')
        eq_(diffs[1][0], 'add_constraint')
        eq_(diffs[1][1].name, 'uq2')
        eq_(len(diffs), 2)


class TruncatedIdxTest(AutogenFixtureTest, TestBase):
    __requires__ = ('sqlalchemy_09', )

    def setUp(self):
        self.bind = engines.testing_engine()
        self.bind.dialect.max_identifier_length = 30

    def test_idx_matches_long(self):
        from alembic.operations.base import conv

        m1 = MetaData()
        Table(
            'q', m1,
            Column('id', Integer, primary_key=True),
            Column('data', Integer),
            Index(
                conv("idx_q_table_this_is_more_than_thirty_characters"),
                "data")
        )

        diffs = self._fixture(m1, m1)
        eq_(diffs, [])
