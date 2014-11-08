from contextlib import contextmanager
import re

from alembic.testing import TestBase, eq_
from alembic.testing.fixtures import op_fixture
from alembic.testing import mock
from alembic.operations import Operations
from alembic.batch import ApplyBatchImpl

from sqlalchemy import Integer, Table, Column, String, MetaData, ForeignKey, \
    UniqueConstraint, ForeignKeyConstraint
from sqlalchemy.sql import column
from sqlalchemy.schema import CreateTable


class BatchApplyTest(TestBase):
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
            Column('parent_id', ForeignKey('tname.id')),
            Column('data', String)
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

        if ddl_contains:
            assert ddl_contains in create_stmt
        if ddl_not_contains:
            assert ddl_not_contains not in create_stmt

        context.assert_(
            create_stmt,
            'INSERT INTO _alembic_batch_temp (%(colnames)s) '
            'SELECT %(tname_colnames)s FROM tname' % {
                "colnames": ", ".join([
                    impl.new_table.c[name].name
                    for name in colnames if name in impl.table.c]),
                "tname_colnames":
                ", ".join("tname.%s" % name
                          for name in colnames if name in impl.table.c)
            },
            'DROP TABLE tname',
            'ALTER TABLE _alembic_batch_temp RENAME TO tname'
        )
        return impl.new_table

    def test_change_type(self):
        impl = self._simple_fixture()
        impl.alter_column('tname', 'x', type_=Integer)
        new_table = self._assert_impl(impl)
        assert new_table.c.x.type._type_affinity is Integer

    def test_rename_col(self):
        impl = self._simple_fixture()
        impl.alter_column('tname', 'x', new_column_name='q')
        new_table = self._assert_impl(impl)
        eq_(new_table.c.x.name, 'q')

    def test_rename_col_pk(self):
        impl = self._simple_fixture()
        impl.alter_column('tname', 'id', new_column_name='foobar')
        new_table = self._assert_impl(
            impl, ddl_contains="PRIMARY KEY (foobar)")
        eq_(new_table.c.id.name, 'foobar')
        eq_(list(new_table.primary_key), [new_table.c.id])

    def test_rename_col_fk(self):
        impl = self._fk_fixture()
        impl.alter_column('tname', 'user_id', new_column_name='foobar')
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

    def test_add_table_opts(self):
        impl = self._simple_fixture(table_kwargs={'mysql_engine': 'InnoDB'})
        self._assert_impl(
            impl, ddl_contains="ENGINE=InnoDB",
            dialect='mysql'
        )


class BatchAPITest(TestBase):
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
                    initially=None, deferrable=None, match=None)
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
