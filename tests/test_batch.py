from contextlib import contextmanager
import re

from alembic.testing import TestBase, eq_
from alembic.testing.fixtures import op_fixture
from alembic.testing import mock
from alembic.operations import Operations
from alembic.batch import ApplyBatchImpl

from sqlalchemy import Integer, Table, Column, String, MetaData, ForeignKey, \
    UniqueConstraint, Index, CheckConstraint, PrimaryKeyConstraint, \
    ForeignKeyConstraint
from sqlalchemy.sql import column
from sqlalchemy.schema import CreateTable


class BatchApplyTest(TestBase):
    def _simple_fixture(self):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('x', String()),
            Column('y', Integer)
        )
        return ApplyBatchImpl(t)

    def _fk_fixture(self):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('email', String()),
            Column('user_id', Integer, ForeignKey('user.id'))
        )
        return ApplyBatchImpl(t)

    def _selfref_fk_fixture(self):
        m = MetaData()
        t = Table(
            'tname', m,
            Column('id', Integer, primary_key=True),
            Column('parent_id', ForeignKey('tname.id')),
            Column('data', String)
        )
        return ApplyBatchImpl(t)

    def _assert_impl(self, impl, colnames=None):
        context = op_fixture()

        impl._create(context.impl)

        if colnames is None:
            colnames = ['id', 'x', 'y']
        eq_(impl.new_table.c.keys(), colnames)

        pk_cols = [col for col in impl.new_table.c if col.primary_key]
        eq_(list(impl.new_table.primary_key), pk_cols)

        create_stmt = str(
            CreateTable(impl.new_table).compile(dialect=context.dialect))
        create_stmt = re.sub(r'[\n\t]', '', create_stmt)
        if pk_cols:
            assert "PRIMARY KEY" in create_stmt
        else:
            assert "PRIMARY KEY" not in create_stmt

        context.assert_(
            create_stmt,
            'INSERT INTO _alembic_batch_temp (%(colnames)s) '
            'SELECT %(tname_colnames)s FROM tname' % {
                "colnames": ", ".join([
                    impl.new_table.c[name].name for name in colnames]),
                "tname_colnames":
                ", ".join("tname.%s" % name for name in colnames)
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
        new_table = self._assert_impl(impl)
        eq_(new_table.c.id.name, 'foobar')
        eq_(list(new_table.primary_key), [new_table.c.id])

    def test_rename_col_fk(self):
        impl = self._fk_fixture()
        impl.alter_column('tname', 'user_id', new_column_name='foobar')
        new_table = self._assert_impl(
            impl, colnames=['id', 'email', 'user_id'])
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
        new_table = self._assert_impl(impl, colnames=['x', 'y'])
        assert 'y' in new_table.c
        assert 'id' not in new_table.c
        assert not new_table.primary_key

    def test_drop_col_remove_fk(self):
        impl = self._fk_fixture()
        impl.drop_column('tname', column('user_id'))
        new_table = self._assert_impl(impl, colnames=['id', 'email'])
        assert 'user_id' not in new_table.c
        assert not new_table.foreign_keys

    def test_drop_col_retain_fk(self):
        impl = self._fk_fixture()
        impl.drop_column('tname', column('email'))
        new_table = self._assert_impl(impl, colnames=['id', 'user_id'])
        assert 'email' not in new_table.c
        assert new_table.c.user_id.foreign_keys

    def test_drop_col_retain_fk_selfref(self):
        impl = self._selfref_fk_fixture()
        impl.drop_column('tname', column('data'))
        new_table = self._assert_impl(impl, colnames=['id', 'parent_id'])
        assert 'data' not in new_table.c
        assert new_table.c.parent_id.foreign_keys


class BatchAPITest(TestBase):
    @contextmanager
    def _fixture(self):
        migration_context = mock.Mock(opts={})
        op = Operations(migration_context)
        batch = op.batch_alter_table('tname', recreate='never').__enter__()

        with mock.patch("alembic.operations.sa_schema") as mock_schema:
            yield batch
        self.mock_schema = mock_schema

    def test_drop_col(self):
        with self._fixture() as batch:
            batch.drop_column('q')
            batch.impl.flush()

        eq_(
            batch.impl.operations.impl.mock_calls,
            [mock.call.drop_column(
                'tname', self.mock_schema.Column(), schema=None)]
        )

    def test_add_col(self):
        column = Column('w', String(50))

        with self._fixture() as batch:
            batch.add_column(column)
            batch.impl.flush()

        eq_(
            batch.impl.operations.impl.mock_calls,
            [mock.call.add_column(
                'tname', column, schema=None)]
        )
