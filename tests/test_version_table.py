import unittest

from sqlalchemy import Table, MetaData, Column, String, create_engine
from sqlalchemy.engine.reflection import Inspector

from alembic.util import CommandError

version_table = Table('version_table', MetaData(),
                      Column('version_num', String(32), nullable=False))

class TestMigrationContext(unittest.TestCase):
    _bind = []

    @property
    def bind(self):
        if not self._bind:
            engine = create_engine('sqlite:///', echo=True)
            self._bind.append(engine)
        return self._bind[0]

    def setUp(self):
        self.connection = self.bind.connect()
        self.transaction = self.connection.begin()

    def tearDown(self):
        version_table.drop(self.connection, checkfirst=True)
        self.transaction.rollback()

    def make_one(self, **kwargs):
        from alembic.migration import MigrationContext
        return MigrationContext.configure(**kwargs)

    def get_revision(self):
        result = self.connection.execute(version_table.select())
        rows = result.fetchall()
        if len(rows) == 0:
            return None
        self.assertEqual(len(rows), 1)
        return rows[0]['version_num']

    def test_config_default_version_table_name(self):
        context = self.make_one(dialect_name='sqlite')
        self.assertEqual(context._version.name, 'alembic_version')

    def test_config_explicit_version_table_name(self):
        context = self.make_one(dialect_name='sqlite',
                                opts={'version_table': 'explicit'})
        self.assertEqual(context._version.name, 'explicit')

    def test_config_explicit_version_table_schema(self):
        context = self.make_one(dialect_name='sqlite',
                                opts={'version_table_schema': 'explicit'})
        self.assertEqual(context._version.schema, 'explicit')

    def test_get_current_revision_creates_version_table(self):
        context = self.make_one(connection=self.connection,
                                opts={'version_table': 'version_table'})
        self.assertEqual(context.get_current_revision(), None)
        insp = Inspector(self.connection)
        self.assertTrue('version_table' in insp.get_table_names())

    def test_get_current_revision(self):
        context = self.make_one(connection=self.connection,
                                opts={'version_table': 'version_table'})
        version_table.create(self.connection)
        self.assertEqual(context.get_current_revision(), None)
        self.connection.execute(
            version_table.insert().values(version_num='revid'))
        self.assertEqual(context.get_current_revision(), 'revid')

    def test_get_current_revision_error_if_starting_rev_given_online(self):
        context = self.make_one(connection=self.connection,
                                opts={'starting_rev': 'boo'})
        self.assertRaises(CommandError, context.get_current_revision)

    def test_get_current_revision_offline(self):
        context = self.make_one(dialect_name='sqlite',
                                opts={'starting_rev': 'startrev',
                                      'as_sql': True})
        self.assertEqual(context.get_current_revision(), 'startrev')

    def test__update_current_rev(self):
        version_table.create(self.connection)
        context = self.make_one(connection=self.connection,
                                opts={'version_table': 'version_table'})

        context._update_current_rev(None, 'a')
        self.assertEqual(self.get_revision(), 'a')
        context._update_current_rev('a', 'b')
        self.assertEqual(self.get_revision(), 'b')
        context._update_current_rev('b', None)
        self.assertEqual(self.get_revision(), None)
