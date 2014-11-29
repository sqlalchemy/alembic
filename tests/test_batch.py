from contextlib import contextmanager
import re

from alembic.testing import exclusions
from alembic.testing import TestBase, eq_, config
from alembic.testing.fixtures import op_fixture
from alembic.testing import mock
from alembic.operations import Operations
from alembic.batch import ApplyBatchImpl
from alembic.migration import MigrationContext

from sqlalchemy import Integer, Table, Column, String, MetaData, ForeignKey, \
    UniqueConstraint, ForeignKeyConstraint, Index, Boolean, CheckConstraint, \
    Enum
from sqlalchemy.sql import column
from sqlalchemy.schema import CreateTable, CreateIndex


class BatchApplyTest(TestBase):
    __requires__ = ('sqlalchemy_08', )

    def setUp(self):
        self.op = Operations(mock.Mock(opts={}))

    def _simple_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('x', String(10)),
            Column('y', Integer)
        )
        return ApplyBatchImpl(t, table_args, table_kwargs)

    def _uq_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('x', String()),
            Column('y', Integer),
            UniqueConstraint('y', name='uq1')
        )
        return ApplyBatchImpl(t, table_args, table_kwargs)

    def _ix_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('x', String()),
            Column('y', Integer),
            Index('ix1', 'y')
        )
        return ApplyBatchImpl(t, table_args, table_kwargs)

    def _literal_ck_fixture(
            self, copy_from=None, table_args=(), table_kwargs={}):
        m = MetaData()
        if copy_from is not None:
            t = copy_from
        else:
            t = Table(
                'tname', m,
                Column('id', Integer, primary_key=True),
                Column('email', String()),
                CheckConstraint("email LIKE '%@%'")
            )
        return ApplyBatchImpl(t, table_args, table_kwargs)

    def _sql_ck_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('email', String())
        )
        t.append_constraint(CheckConstraint(t.c.email.like('%@%')))
        return ApplyBatchImpl(t, table_args, table_kwargs)

    def _fk_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('email', String()),
            Column('user_id', Integer, ForeignKey('user.id'))
        )
        return ApplyBatchImpl(t, table_args, table_kwargs)

    def _named_fk_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('email', String()),
            Column('user_id', Integer, ForeignKey('user.id', name='ufk'))
        )
        return ApplyBatchImpl(t, table_args, table_kwargs)

    def _selfref_fk_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('parent_id', Integer, ForeignKey('tname.id')),
            Column('data', String)
        )
        return ApplyBatchImpl(t, table_args, table_kwargs)

    def _boolean_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('flag', Boolean)
        )
        return ApplyBatchImpl(t, table_args, table_kwargs)

    def _boolean_no_ck_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('flag', Boolean(create_constraint=False))
        )
        return ApplyBatchImpl(t, table_args, table_kwargs)

    def _enum_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('thing', Enum('a', 'b', 'c'))
        )
        return ApplyBatchImpl(t, table_args, table_kwargs)

    def _assert_impl(self, impl, colnames=None,
                     ddl_contains=None, ddl_not_contains=None,
                     dialect='default'):
        context = op_fixture(dialect=dialect)

        impl._create(context.impl)

        if colnames is None:
            colnames = ['id', 'x', 'y']
        eq_(impl.new_table.c.keys(), colnames)

        pk_cols = [col for col in impl.new_table.c if col.primary_key]
        eq_(list(impl.new_table.primary_key), pk_cols)

        create_stmt = str(
            CreateTable(impl.new_table).compile(dialect=context.dialect))
        create_stmt = re.sub(r'[\n\t]', '', create_stmt)

        idx_stmt = ""
        for idx in impl.new_table.indexes:
            idx_stmt += str(CreateIndex(idx).compile(dialect=context.dialect))
        idx_stmt = re.sub(r'[\n\t]', '', idx_stmt)

        if ddl_contains:
            assert ddl_contains in create_stmt + idx_stmt
        if ddl_not_contains:
            assert ddl_not_contains not in create_stmt + idx_stmt

        expected = [
            create_stmt,
        ]
        if impl.new_table.indexes:
            expected.append(idx_stmt)

        expected.extend([
            'INSERT INTO _alembic_batch_temp (%(colnames)s) '
            'SELECT %(tname_colnames)s FROM tname' % {
                "colnames": ", ".join([
                    impl.new_table.c[name].name
                    for name in colnames
                    if name in impl.table.c]),
                "tname_colnames":
                ", ".join(
                    "CAST(tname.%s AS %s) AS anon_1" % (
                        name, impl.new_table.c[name].type)
                    if (
                        impl.new_table.c[name].type._type_affinity
                        is not impl.table.c[name].type._type_affinity)
                    else "tname.%s" % name
                    for name in colnames if name in impl.table.c
                )
            },
            'DROP TABLE tname',
            'ALTER TABLE _alembic_batch_temp RENAME TO tname'
        ])
        context.assert_(*expected)
        return impl.new_table

    def test_change_type(self):
        impl = self._simple_fixture()
        impl.alter_column('tname', 'x', type_=Integer)
        new_table = self._assert_impl(impl)
        assert new_table.c.x.type._type_affinity is Integer

    def test_rename_col(self):
        impl = self._simple_fixture()
        impl.alter_column('tname', 'x', name='q')
        new_table = self._assert_impl(impl)
        eq_(new_table.c.x.name, 'q')

    def test_rename_col_boolean(self):
        impl = self._boolean_fixture()
        impl.alter_column('tname', 'flag', name='bflag')
        new_table = self._assert_impl(
            impl, ddl_contains="CHECK (bflag IN (0, 1)",
            colnames=["id", "flag"])
        eq_(new_table.c.flag.name, 'bflag')
        eq_(
            len([
                const for const
                in new_table.constraints
                if isinstance(const, CheckConstraint)]),
            1)

    def test_rename_col_boolean_no_ck(self):
        impl = self._boolean_no_ck_fixture()
        impl.alter_column('tname', 'flag', name='bflag')
        new_table = self._assert_impl(
            impl, ddl_not_contains="CHECK",
            colnames=["id", "flag"])
        eq_(new_table.c.flag.name, 'bflag')
        eq_(
            len([
                const for const
                in new_table.constraints
                if isinstance(const, CheckConstraint)]),
            0)

    def test_rename_col_enum(self):
        impl = self._enum_fixture()
        impl.alter_column('tname', 'thing', name='thang')
        new_table = self._assert_impl(
            impl, ddl_contains="CHECK (thang IN ('a', 'b', 'c')",
            colnames=["id", "thing"])
        eq_(new_table.c.thing.name, 'thang')
        eq_(
            len([
                const for const
                in new_table.constraints
                if isinstance(const, CheckConstraint)]),
            1)

    def test_rename_col_literal_ck(self):
        impl = self._literal_ck_fixture()
        impl.alter_column('tname', 'email', name='emol')
        new_table = self._assert_impl(
            # note this is wrong, we don't dig into the SQL
            impl, ddl_contains="CHECK (email LIKE '%@%')",
            colnames=["id", "email"])
        eq_(
            len([c for c in new_table.constraints
                if isinstance(c, CheckConstraint)]), 1)

        eq_(new_table.c.email.name, 'emol')

    def test_rename_col_literal_ck_workaround(self):
        impl = self._literal_ck_fixture(
            copy_from=Table(
                'tname', MetaData(),
                Column('id', Integer, primary_key=True),
                Column('email', String),
            ),
            table_args=[CheckConstraint("emol LIKE '%@%'")])

        impl.alter_column('tname', 'email', name='emol')
        new_table = self._assert_impl(
            impl, ddl_contains="CHECK (emol LIKE '%@%')",
            colnames=["id", "email"])
        eq_(
            len([c for c in new_table.constraints
                if isinstance(c, CheckConstraint)]), 1)
        eq_(new_table.c.email.name, 'emol')

    def test_rename_col_sql_ck(self):
        impl = self._sql_ck_fixture()

        impl.alter_column('tname', 'email', name='emol')
        new_table = self._assert_impl(
            impl, ddl_contains="CHECK (emol LIKE '%@%')",
            colnames=["id", "email"])
        eq_(
            len([c for c in new_table.constraints
                if isinstance(c, CheckConstraint)]), 1)

        eq_(new_table.c.email.name, 'emol')

    def test_add_col(self):
        impl = self._simple_fixture()
        col = Column('g', Integer)
        # operations.add_column produces a table
        t = self.op._table('tname', col)  # noqa
        impl.add_column('tname', col)
        new_table = self._assert_impl(impl, colnames=['id', 'x', 'y', 'g'])
        eq_(new_table.c.g.name, 'g')

    def test_rename_col_pk(self):
        impl = self._simple_fixture()
        impl.alter_column('tname', 'id', name='foobar')
        new_table = self._assert_impl(
            impl, ddl_contains="PRIMARY KEY (foobar)")
        eq_(new_table.c.id.name, 'foobar')
        eq_(list(new_table.primary_key), [new_table.c.id])

    def test_rename_col_fk(self):
        impl = self._fk_fixture()
        impl.alter_column('tname', 'user_id', name='foobar')
        new_table = self._assert_impl(
            impl, colnames=['id', 'email', 'user_id'],
            ddl_contains='FOREIGN KEY(foobar) REFERENCES "user" (id)')
        eq_(new_table.c.user_id.name, 'foobar')
        eq_(
            list(new_table.c.user_id.foreign_keys)[0]._get_colspec(),
            "user.id"
        )

    def test_drop_col(self):
        impl = self._simple_fixture()
        impl.drop_column('tname', column('x'))
        new_table = self._assert_impl(impl, colnames=['id', 'y'])
        assert 'y' in new_table.c
        assert 'x' not in new_table.c

    def test_drop_col_remove_pk(self):
        impl = self._simple_fixture()
        impl.drop_column('tname', column('id'))
        new_table = self._assert_impl(
            impl, colnames=['x', 'y'], ddl_not_contains="PRIMARY KEY")
        assert 'y' in new_table.c
        assert 'id' not in new_table.c
        assert not new_table.primary_key

    def test_drop_col_remove_fk(self):
        impl = self._fk_fixture()
        impl.drop_column('tname', column('user_id'))
        new_table = self._assert_impl(
            impl, colnames=['id', 'email'], ddl_not_contains="FOREIGN KEY")
        assert 'user_id' not in new_table.c
        assert not new_table.foreign_keys

    def test_drop_col_retain_fk(self):
        impl = self._fk_fixture()
        impl.drop_column('tname', column('email'))
        new_table = self._assert_impl(
            impl, colnames=['id', 'user_id'],
            ddl_contains='FOREIGN KEY(user_id) REFERENCES "user" (id)')
        assert 'email' not in new_table.c
        assert new_table.c.user_id.foreign_keys

    def test_drop_col_retain_fk_selfref(self):
        impl = self._selfref_fk_fixture()
        impl.drop_column('tname', column('data'))
        new_table = self._assert_impl(impl, colnames=['id', 'parent_id'])
        assert 'data' not in new_table.c
        assert new_table.c.parent_id.foreign_keys

    def test_add_fk(self):
        impl = self._simple_fixture()
        impl.add_column('tname', Column('user_id', Integer))
        fk = self.op._foreign_key_constraint(
            'fk1', 'tname', 'user',
            ['user_id'], ['id'])
        impl.add_constraint(fk)
        new_table = self._assert_impl(
            impl, colnames=['id', 'x', 'y', 'user_id'],
            ddl_contains='CONSTRAINT fk1 FOREIGN KEY(user_id) '
            'REFERENCES "user" (id)')
        eq_(
            list(new_table.c.user_id.foreign_keys)[0]._get_colspec(),
            'user.id'
        )

    def test_drop_fk(self):
        impl = self._named_fk_fixture()
        fk = ForeignKeyConstraint([], [], name='ufk')
        impl.drop_constraint(fk)
        new_table = self._assert_impl(
            impl, colnames=['id', 'email', 'user_id'],
            ddl_not_contains="CONSTRANT fk1")
        eq_(
            list(new_table.foreign_keys),
            []
        )

    def test_add_uq(self):
        impl = self._simple_fixture()
        uq = self.op._unique_constraint(
            'uq1', 'tname', ['y']
        )

        impl.add_constraint(uq)
        self._assert_impl(
            impl, colnames=['id', 'x', 'y'],
            ddl_contains="CONSTRAINT uq1 UNIQUE")

    def test_drop_uq(self):
        impl = self._uq_fixture()

        uq = self.op._unique_constraint(
            'uq1', 'tname', ['y']
        )
        impl.drop_constraint(uq)
        self._assert_impl(
            impl, colnames=['id', 'x', 'y'],
            ddl_not_contains="CONSTRAINT uq1 UNIQUE")

    def test_add_index(self):
        impl = self._simple_fixture()
        ix = self.op._index('ix1', 'tname', ['y'])

        impl.add_index(ix)
        self._assert_impl(
            impl, colnames=['id', 'x', 'y'],
            ddl_contains="CREATE INDEX ix1")

    def test_drop_index(self):
        impl = self._ix_fixture()

        ix = self.op._index('ix1', 'tname', ['y'])
        impl.drop_index(ix)
        self._assert_impl(
            impl, colnames=['id', 'x', 'y'],
            ddl_not_contains="CONSTRAINT uq1 UNIQUE")

    def test_add_table_opts(self):
        impl = self._simple_fixture(table_kwargs={'mysql_engine': 'InnoDB'})
        self._assert_impl(
            impl, ddl_contains="ENGINE=InnoDB",
            dialect='mysql'
        )


class BatchAPITest(TestBase):
    __requires__ = ('sqlalchemy_08', )

    @contextmanager
    def _fixture(self):
        migration_context = mock.Mock(opts={})
        op = Operations(migration_context)
        batch = op.batch_alter_table('tname', recreate='never').__enter__()

        with mock.patch("alembic.operations.sa_schema") as mock_schema:
            yield batch
        batch.impl.flush()
        self.mock_schema = mock_schema

    def test_drop_col(self):
        with self._fixture() as batch:
            batch.drop_column('q')

        eq_(
            batch.impl.operations.impl.mock_calls,
            [mock.call.drop_column(
                'tname', self.mock_schema.Column(), schema=None)]
        )

    def test_add_col(self):
        column = Column('w', String(50))

        with self._fixture() as batch:
            batch.add_column(column)

        eq_(
            batch.impl.operations.impl.mock_calls,
            [mock.call.add_column(
                'tname', column, schema=None)]
        )

    def test_create_fk(self):
        with self._fixture() as batch:
            batch.create_foreign_key('myfk', 'user', ['x'], ['y'])

        eq_(
            self.mock_schema.ForeignKeyConstraint.mock_calls,
            [
                mock.call(
                    ['x'], ['user.y'],
                    onupdate=None, ondelete=None, name='myfk',
                    initially=None, deferrable=None, match=None,
                    schema=None)
            ]
        )
        eq_(
            batch.impl.operations.impl.mock_calls,
            [mock.call.add_constraint(
                self.mock_schema.ForeignKeyConstraint())]
        )

    def test_create_uq(self):
        with self._fixture() as batch:
            batch.create_unique_constraint('uq1', ['a', 'b'])

        eq_(
            self.mock_schema.Table().c.__getitem__.mock_calls,
            [mock.call('a'), mock.call('b')]
        )

        eq_(
            self.mock_schema.UniqueConstraint.mock_calls,
            [
                mock.call(
                    self.mock_schema.Table().c.__getitem__(),
                    self.mock_schema.Table().c.__getitem__(),
                    name='uq1'
                )
            ]
        )
        eq_(
            batch.impl.operations.impl.mock_calls,
            [mock.call.add_constraint(
                self.mock_schema.UniqueConstraint())]
        )

    def test_drop_constraint(self):
        with self._fixture() as batch:
            batch.drop_constraint('uq1')

        eq_(
            self.mock_schema.Constraint.mock_calls,
            [
                mock.call(name='uq1')
            ]
        )
        eq_(
            batch.impl.operations.impl.mock_calls,
            [mock.call.drop_constraint(self.mock_schema.Constraint())]
        )


class BatchRoundTripTest(TestBase):
    __requires__ = ('sqlalchemy_08', )
    __only_on__ = "sqlite"

    def setUp(self):
        self.conn = config.db.connect()
        self.metadata = MetaData()
        t1 = Table(
            'foo', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('data', String(50)),
            Column('x', Integer),
            mysql_engine='InnoDB'
        )
        t1.create(self.conn)

        self.conn.execute(
            t1.insert(),
            [
                {"id": 1, "data": "d1", "x": 5},
                {"id": 2, "data": "22", "x": 6},
                {"id": 3, "data": "8.5", "x": 7},
                {"id": 4, "data": "9.46", "x": 8},
                {"id": 5, "data": "d5", "x": 9}
            ]
        )
        context = MigrationContext.configure(self.conn)
        self.op = Operations(context)

    def tearDown(self):
        self.metadata.drop_all(self.conn)
        self.conn.close()

    def _assert_data(self, data, tablename='foo'):
        eq_(
            [dict(row) for row
             in self.conn.execute("select * from %s" % tablename)],
            data
        )

    def test_fk_points_to_me_auto(self):
        self._test_fk_points_to_me("auto")

    # in particular, this tests that the failures
    # on PG and MySQL result in recovery of the batch system,
    # e.g. that the _alembic_batch_temp table is dropped
    @config.requirements.no_referential_integrity
    def test_fk_points_to_me_recreate(self):
        self._test_fk_points_to_me("always")

    def _test_fk_points_to_me(self, recreate):
        bar = Table(
            'bar', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('foo_id', Integer, ForeignKey('foo.id')),
            mysql_engine='InnoDB'
        )
        bar.create(self.conn)
        self.conn.execute(bar.insert(), {'id': 1, 'foo_id': 3})

        with self.op.batch_alter_table("foo", recreate=recreate) as batch_op:
            batch_op.alter_column(
                'data', new_column_name='newdata', existing_type=String(50))

    def test_change_type(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.alter_column('data', type_=Integer)

        self._assert_data([
            {"id": 1, "data": 0, "x": 5},
            {"id": 2, "data": 22, "x": 6},
            {"id": 3, "data": 8, "x": 7},
            {"id": 4, "data": 9, "x": 8},
            {"id": 5, "data": 0, "x": 9}
        ])

    def test_drop_column(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.drop_column('data')

        self._assert_data([
            {"id": 1, "x": 5},
            {"id": 2, "x": 6},
            {"id": 3, "x": 7},
            {"id": 4, "x": 8},
            {"id": 5, "x": 9}
        ])

    def test_drop_column_fk_recreate(self):
        with self.op.batch_alter_table("foo", recreate='always') as batch_op:
            batch_op.drop_column('data')

        self._assert_data([
            {"id": 1, "x": 5},
            {"id": 2, "x": 6},
            {"id": 3, "x": 7},
            {"id": 4, "x": 8},
            {"id": 5, "x": 9}
        ])

    def test_rename_column(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.alter_column('x', new_column_name='y')

        self._assert_data([
            {"id": 1, "data": "d1", "y": 5},
            {"id": 2, "data": "22", "y": 6},
            {"id": 3, "data": "8.5", "y": 7},
            {"id": 4, "data": "9.46", "y": 8},
            {"id": 5, "data": "d5", "y": 9}
        ])

    def test_rename_column_boolean(self):
        bar = Table(
            'bar', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('flag', Boolean()),
            mysql_engine='InnoDB'
        )
        bar.create(self.conn)
        self.conn.execute(bar.insert(), {'id': 1, 'flag': True})
        self.conn.execute(bar.insert(), {'id': 2, 'flag': False})

        with self.op.batch_alter_table(
            "bar"
        ) as batch_op:
            batch_op.alter_column(
                'flag', new_column_name='bflag', existing_type=Boolean)

        self._assert_data([
            {"id": 1, 'bflag': True},
            {"id": 2, 'bflag': False},
        ], 'bar')

    @config.requirements.non_native_boolean
    def test_rename_column_non_native_boolean_no_ck(self):
        bar = Table(
            'bar', self.metadata,
            Column('id', Integer, primary_key=True),
            Column('flag', Boolean(create_constraint=False)),
            mysql_engine='InnoDB'
        )
        bar.create(self.conn)
        self.conn.execute(bar.insert(), {'id': 1, 'flag': True})
        self.conn.execute(bar.insert(), {'id': 2, 'flag': False})
        self.conn.execute(bar.insert(), {'id': 3, 'flag': 5})

        with self.op.batch_alter_table(
            "bar",
            reflect_args=[Column('flag', Boolean(create_constraint=False))]
        ) as batch_op:
            batch_op.alter_column(
                'flag', new_column_name='bflag', existing_type=Boolean)

        self._assert_data([
            {"id": 1, 'bflag': True},
            {"id": 2, 'bflag': False},
            {'id': 3, 'bflag': 5}
        ], 'bar')

    def test_drop_column_pk(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.drop_column('id')

        self._assert_data([
            {"data": "d1", "x": 5},
            {"data": "22", "x": 6},
            {"data": "8.5", "x": 7},
            {"data": "9.46", "x": 8},
            {"data": "d5", "x": 9}
        ])

    def test_rename_column_pk(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.alter_column('id', new_column_name='ident')

        self._assert_data([
            {"ident": 1, "data": "d1", "x": 5},
            {"ident": 2, "data": "22", "x": 6},
            {"ident": 3, "data": "8.5", "x": 7},
            {"ident": 4, "data": "9.46", "x": 8},
            {"ident": 5, "data": "d5", "x": 9}
        ])

    def test_add_column_auto(self):
        # note this uses ALTER
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.add_column(
                Column('data2', String(50), server_default='hi'))

        self._assert_data([
            {"id": 1, "data": "d1", "x": 5, 'data2': 'hi'},
            {"id": 2, "data": "22", "x": 6, 'data2': 'hi'},
            {"id": 3, "data": "8.5", "x": 7, 'data2': 'hi'},
            {"id": 4, "data": "9.46", "x": 8, 'data2': 'hi'},
            {"id": 5, "data": "d5", "x": 9, 'data2': 'hi'}
        ])

    def test_add_column_recreate(self):
        with self.op.batch_alter_table("foo", recreate='always') as batch_op:
            batch_op.add_column(
                Column('data2', String(50), server_default='hi'))

        self._assert_data([
            {"id": 1, "data": "d1", "x": 5, 'data2': 'hi'},
            {"id": 2, "data": "22", "x": 6, 'data2': 'hi'},
            {"id": 3, "data": "8.5", "x": 7, 'data2': 'hi'},
            {"id": 4, "data": "9.46", "x": 8, 'data2': 'hi'},
            {"id": 5, "data": "d5", "x": 9, 'data2': 'hi'}
        ])


class BatchRoundTripMySQLTest(BatchRoundTripTest):
    __only_on__ = "mysql"

    @exclusions.fails()
    def test_rename_column_pk(self):
        super(BatchRoundTripMySQLTest, self).test_rename_column_pk()

    @exclusions.fails()
    def test_rename_column(self):
        super(BatchRoundTripMySQLTest, self).test_rename_column()

    @exclusions.fails()
    def test_change_type(self):
        super(BatchRoundTripMySQLTest, self).test_change_type()


class BatchRoundTripPostgresqlTest(BatchRoundTripTest):
    __only_on__ = "postgresql"

    @exclusions.fails()
    def test_change_type(self):
        super(BatchRoundTripPostgresqlTest, self).test_change_type()

