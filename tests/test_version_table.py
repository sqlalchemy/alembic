from alembic.testing.fixtures import TestBase

from alembic.testing import config, eq_, assert_raises, assert_raises_message

from sqlalchemy import Table, MetaData, Column, String
from sqlalchemy.engine.reflection import Inspector
from alembic.migration import MigrationContext

from alembic.util import CommandError

version_table = Table('version_table', MetaData(),
                      Column('version_num', String(32), nullable=False))


class TestMigrationContext(TestBase):

    @classmethod
    def setup_class(cls):
        cls.bind = config.db

    def setUp(self):
        self.connection = self.bind.connect()
        self.transaction = self.connection.begin()

    def tearDown(self):
        version_table.drop(self.connection, checkfirst=True)
        self.transaction.rollback()
        self.connection.close()

    def make_one(self, **kwargs):
        return MigrationContext.configure(**kwargs)

    def get_revision(self):
        result = self.connection.execute(version_table.select())
        rows = result.fetchall()
        if len(rows) == 0:
            return None
        eq_(len(rows), 1)
        return rows[0]['version_num']

    def test_config_default_version_table_name(self):
        context = self.make_one(dialect_name='sqlite')
        eq_(context._version.name, 'alembic_version')

    def test_config_explicit_version_table_name(self):
        context = self.make_one(dialect_name='sqlite',
                                opts={'version_table': 'explicit'})
        eq_(context._version.name, 'explicit')

    def test_config_explicit_version_table_schema(self):
        context = self.make_one(dialect_name='sqlite',
                                opts={'version_table_schema': 'explicit'})
        eq_(context._version.schema, 'explicit')

    def test_get_current_revision_doesnt_create_version_table(self):
        context = self.make_one(connection=self.connection,
                                opts={'version_table': 'version_table'})
        eq_(context.get_current_revision(), None)
        insp = Inspector(self.connection)
        assert ('version_table' not in insp.get_table_names())

    def test_get_current_revision(self):
        context = self.make_one(connection=self.connection,
                                opts={'version_table': 'version_table'})
        version_table.create(self.connection)
        eq_(context.get_current_revision(), None)
        self.connection.execute(
            version_table.insert().values(version_num='revid'))
        eq_(context.get_current_revision(), 'revid')

    def test_get_current_revision_error_if_starting_rev_given_online(self):
        context = self.make_one(connection=self.connection,
                                opts={'starting_rev': 'boo'})
        assert_raises(
            CommandError,
            context.get_current_revision
        )

    def test_get_current_revision_offline(self):
        context = self.make_one(dialect_name='sqlite',
                                opts={'starting_rev': 'startrev',
                                      'as_sql': True})
        eq_(context.get_current_revision(), 'startrev')

    def test_get_current_revision_multiple_heads(self):
        version_table.create(self.connection)
        context = self.make_one(connection=self.connection,
                                opts={'version_table': 'version_table'})
        context._update_current_rev(None, 'a')
        context._update_current_rev(None, 'b')
        assert_raises_message(
            CommandError,
            "Version table 'version_table' has more than one head present; "
            "please use get_current_heads()",
            context.get_current_revision
        )

    def test_get_heads(self):
        version_table.create(self.connection)
        context = self.make_one(connection=self.connection,
                                opts={'version_table': 'version_table'})
        context._update_current_rev(None, 'a')
        context._update_current_rev(None, 'b')
        eq_(context.get_current_heads(), ('a', 'b'))

    def test_get_heads_offline(self):
        version_table.create(self.connection)
        context = self.make_one(connection=self.connection,
                                opts={
                                    'starting_rev': 'q',
                                    'version_table': 'version_table',
                                    'as_sql': True})
        eq_(context.get_current_heads(), ('q', ))


class UpdateRevTest(TestBase):

    @classmethod
    def setup_class(cls):
        cls.bind = config.db

    def setUp(self):
        self.connection = self.bind.connect()
        self.context = MigrationContext.configure(
            connection=self.connection,
            opts={"version_table": "version_table"})
        version_table.create(self.connection)

    def tearDown(self):
        version_table.drop(self.connection, checkfirst=True)
        self.connection.close()

    def test_update_none_to_single(self):
        self.context._update_current_rev(None, 'a')
        eq_(self.context.get_current_heads(), ('a',))

    def test_update_single_to_single(self):
        self.context._update_current_rev(None, 'a')
        self.context._update_current_rev('a', 'b')
        eq_(self.context.get_current_heads(), ('b',))

    def test_update_single_to_none(self):
        self.context._update_current_rev(None, 'a')
        self.context._update_current_rev('a', None)
        eq_(self.context.get_current_heads(), ())

    def test_update_no_change(self):
        self.context._update_current_rev(None, 'a')
        self.context._update_current_rev('a', 'a')
        eq_(self.context.get_current_heads(), ('a',))

    def test_update_no_match(self):
        self.context._update_current_rev(None, 'a')

        assert_raises_message(
            CommandError,
            "Online migration expected to match one row when updating "
            "'x' to 'b' in 'version_table'; 0 found",
            self.context._update_current_rev, 'x', 'b'
        )

    def test_update_multi_match(self):
        self.connection.execute(version_table.insert(), version_num='a')
        self.connection.execute(version_table.insert(), version_num='a')

        assert_raises_message(
            CommandError,
            "Online migration expected to match one row when updating "
            "'a' to 'b' in 'version_table'; 2 found",
            self.context._update_current_rev, 'a', 'b'
        )

    def test_delete_no_match(self):
        self.context._update_current_rev(None, 'a')

        assert_raises_message(
            CommandError,
            "Online migration expected to match one row when "
            "deleting 'x' in 'version_table'; 0 found",
            self.context._update_current_rev, 'x', None
        )

    def test_delete_multi_match(self):
        self.connection.execute(version_table.insert(), version_num='a')
        self.connection.execute(version_table.insert(), version_num='a')

        assert_raises_message(
            CommandError,
            "Online migration expected to match one row when "
            "deleting 'a' in 'version_table'; 2 found",
            self.context._update_current_rev, 'a', None
        )

