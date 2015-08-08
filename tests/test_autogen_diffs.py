import sys

from sqlalchemy import MetaData, Column, Table, Integer, String, Text, \
    Numeric, CHAR, ForeignKey, INTEGER, Index, UniqueConstraint, \
    TypeDecorator, CheckConstraint, text, PrimaryKeyConstraint, \
    ForeignKeyConstraint
from sqlalchemy.types import NULLTYPE
from sqlalchemy.engine.reflection import Inspector

from alembic.operations import ops
from alembic import autogenerate
from alembic.migration import MigrationContext
from alembic.testing import TestBase
from alembic.testing import config
from alembic.testing import assert_raises_message
from alembic.testing.mock import Mock
from alembic.testing import eq_, is_, is_not_
from alembic.util import CommandError
from ._autogen_fixtures import AutogenTest, AutogenFixtureTest

py3k = sys.version_info >= (3, )


class AutogenCrossSchemaTest(AutogenTest, TestBase):
    __only_on__ = 'postgresql'

    @classmethod
    def _get_db_schema(cls):
        m = MetaData()
        Table('t1', m,
              Column('x', Integer)
              )
        Table('t2', m,
              Column('y', Integer),
              schema=config.test_schema
              )
        Table('t6', m,
              Column('u', Integer)
              )
        Table('t7', m,
              Column('v', Integer),
              schema=config.test_schema
              )

        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()
        Table('t3', m,
              Column('q', Integer)
              )
        Table('t4', m,
              Column('z', Integer),
              schema=config.test_schema
              )
        Table('t6', m,
              Column('u', Integer)
              )
        Table('t7', m,
              Column('v', Integer),
              schema=config.test_schema
              )
        return m

    def test_default_schema_omitted_upgrade(self):

        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t3"
            else:
                return True
        self._update_context(
            object_filters=include_object,
            include_schemas=True,
        )
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        diffs = uo.as_diffs()
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, None)

    def test_alt_schema_included_upgrade(self):

        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t4"
            else:
                return True

        self._update_context(
            object_filters=include_object,
            include_schemas=True,
        )
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        diffs = uo.as_diffs()
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, config.test_schema)

    def test_default_schema_omitted_downgrade(self):
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t1"
            else:
                return True
        self._update_context(
            object_filters=include_object,
            include_schemas=True,
        )
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        diffs = uo.as_diffs()
        eq_(diffs[0][0], "remove_table")
        eq_(diffs[0][1].schema, None)

    def test_alt_schema_included_downgrade(self):

        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t2"
            else:
                return True
        self._update_context(
            object_filters=include_object,
            include_schemas=True,
        )
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)
        diffs = uo.as_diffs()
        eq_(diffs[0][0], "remove_table")
        eq_(diffs[0][1].schema, config.test_schema)


class AutogenDefaultSchemaTest(AutogenFixtureTest, TestBase):
    __only_on__ = 'postgresql'

    def test_uses_explcit_schema_in_default_one(self):

        default_schema = self.bind.dialect.default_schema_name

        m1 = MetaData()
        m2 = MetaData()

        Table('a', m1, Column('x', String(50)))
        Table('a', m2, Column('x', String(50)), schema=default_schema)

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs, [])

    def test_uses_explcit_schema_in_default_two(self):

        default_schema = self.bind.dialect.default_schema_name

        m1 = MetaData()
        m2 = MetaData()

        Table('a', m1, Column('x', String(50)))
        Table('a', m2, Column('x', String(50)), schema=default_schema)
        Table('a', m2, Column('y', String(50)), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, "test_schema")
        eq_(diffs[0][1].c.keys(), ['y'])

    def test_uses_explcit_schema_in_default_three(self):

        default_schema = self.bind.dialect.default_schema_name

        m1 = MetaData()
        m2 = MetaData()

        Table('a', m1, Column('y', String(50)), schema="test_schema")

        Table('a', m2, Column('x', String(50)), schema=default_schema)
        Table('a', m2, Column('y', String(50)), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, default_schema)
        eq_(diffs[0][1].c.keys(), ['x'])


class ModelOne(object):
    __requires__ = ('unique_constraint_reflection', )

    schema = None

    @classmethod
    def _get_db_schema(cls):
        schema = cls.schema

        m = MetaData(schema=schema)

        Table('user', m,
              Column('id', Integer, primary_key=True),
              Column('name', String(50)),
              Column('a1', Text),
              Column("pw", String(50)),
              Index('pw_idx', 'pw')
              )

        Table('address', m,
              Column('id', Integer, primary_key=True),
              Column('email_address', String(100), nullable=False),
              )

        Table('order', m,
              Column('order_id', Integer, primary_key=True),
              Column("amount", Numeric(8, 2), nullable=False,
                     server_default=text("0")),
              CheckConstraint('amount >= 0', name='ck_order_amount')
              )

        Table('extra', m,
              Column("x", CHAR),
              Column('uid', Integer, ForeignKey('user.id'))
              )

        return m

    @classmethod
    def _get_model_schema(cls):
        schema = cls.schema

        m = MetaData(schema=schema)

        Table('user', m,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False),
              Column('a1', Text, server_default="x")
              )

        Table('address', m,
              Column('id', Integer, primary_key=True),
              Column('email_address', String(100), nullable=False),
              Column('street', String(50)),
              UniqueConstraint('email_address', name="uq_email")
              )

        Table('order', m,
              Column('order_id', Integer, primary_key=True),
              Column('amount', Numeric(10, 2), nullable=True,
                     server_default=text("0")),
              Column('user_id', Integer, ForeignKey('user.id')),
              CheckConstraint('amount > -1', name='ck_order_amount'),
              )

        Table('item', m,
              Column('id', Integer, primary_key=True),
              Column('description', String(100)),
              Column('order_id', Integer, ForeignKey('order.order_id')),
              CheckConstraint('len(description) > 5')
              )
        return m


class AutogenerateDiffTest(ModelOne, AutogenTest, TestBase):
    __only_on__ = 'sqlite'

    def test_diffs(self):
        """test generation of diff rules"""

        metadata = self.m2
        uo = ops.UpgradeOps(ops=[])
        ctx = self.autogen_context

        autogenerate._produce_net_changes(
            ctx, uo
        )

        diffs = uo.as_diffs()
        eq_(
            diffs[0],
            ('add_table', metadata.tables['item'])
        )

        eq_(diffs[1][0], 'remove_table')
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], "add_column")
        eq_(diffs[2][1], None)
        eq_(diffs[2][2], "address")
        eq_(diffs[2][3], metadata.tables['address'].c.street)

        eq_(diffs[3][0], "add_constraint")
        eq_(diffs[3][1].name, "uq_email")

        eq_(diffs[4][0], "add_column")
        eq_(diffs[4][1], None)
        eq_(diffs[4][2], "order")
        eq_(diffs[4][3], metadata.tables['order'].c.user_id)

        eq_(diffs[5][0][0], "modify_type")
        eq_(diffs[5][0][1], None)
        eq_(diffs[5][0][2], "order")
        eq_(diffs[5][0][3], "amount")
        eq_(repr(diffs[5][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[5][0][6]), "Numeric(precision=10, scale=2)")

        self._assert_fk_diff(
            diffs[6], "add_fk",
            "order", ["user_id"],
            "user", ["id"]
        )

        eq_(diffs[7][0][0], "modify_default")
        eq_(diffs[7][0][1], None)
        eq_(diffs[7][0][2], "user")
        eq_(diffs[7][0][3], "a1")
        eq_(diffs[7][0][6].arg, "x")

        eq_(diffs[8][0][0], 'modify_nullable')
        eq_(diffs[8][0][5], True)
        eq_(diffs[8][0][6], False)

        eq_(diffs[9][0], 'remove_index')
        eq_(diffs[9][1].name, 'pw_idx')

        eq_(diffs[10][0], 'remove_column')
        eq_(diffs[10][3].name, 'pw')
        eq_(diffs[10][3].table.name, 'user')
        assert isinstance(
            diffs[10][3].type, String
        )

    def test_include_symbol(self):

        diffs = []

        def include_symbol(name, schema=None):
            return name in ('address', 'order')

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'target_metadata': self.m2,
                'include_symbol': include_symbol,
            }
        )

        diffs = autogenerate.compare_metadata(
            context, context.opts['target_metadata'])

        alter_cols = set([
            d[2] for d in self._flatten_diffs(diffs)
            if d[0].startswith('modify')
        ])
        eq_(alter_cols, set(['order']))

    def test_include_object(self):
        def include_object(obj, name, type_, reflected, compare_to):
            assert obj.name == name
            if type_ == "table":
                if reflected:
                    assert obj.metadata is not self.m2
                else:
                    assert obj.metadata is self.m2
                return name in ("address", "order", "user")
            elif type_ == "column":
                if reflected:
                    assert obj.table.metadata is not self.m2
                else:
                    assert obj.table.metadata is self.m2
                return name != "street"
            else:
                return True

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'target_metadata': self.m2,
                'include_object': include_object,
            }
        )

        diffs = autogenerate.compare_metadata(
            context, context.opts['target_metadata'])

        alter_cols = set([
            d[2] for d in self._flatten_diffs(diffs)
            if d[0].startswith('modify')
        ]).union(
            d[3].name for d in self._flatten_diffs(diffs)
            if d[0] == 'add_column'
        ).union(
            d[1].name for d in self._flatten_diffs(diffs)
            if d[0] == 'add_table'
        )
        eq_(alter_cols, set(['user_id', 'order', 'user']))

    def test_skip_null_type_comparison_reflected(self):
        ac = ops.AlterColumnOp("sometable", "somecol")
        autogenerate.compare._compare_type(
            self.autogen_context, ac,
            None, "sometable", "somecol",
            Column("somecol", NULLTYPE),
            Column("somecol", Integer()),
        )
        diff = ac.to_diff_tuple()
        assert not diff

    def test_skip_null_type_comparison_local(self):
        ac = ops.AlterColumnOp("sometable", "somecol")
        autogenerate.compare._compare_type(
            self.autogen_context, ac,
            None, "sometable", "somecol",
            Column("somecol", Integer()),
            Column("somecol", NULLTYPE),
        )
        diff = ac.to_diff_tuple()
        assert not diff

    def test_custom_type_compare(self):
        class MyType(TypeDecorator):
            impl = Integer

            def compare_against_backend(self, dialect, conn_type):
                return isinstance(conn_type, Integer)

        ac = ops.AlterColumnOp("sometable", "somecol")
        autogenerate.compare._compare_type(
            self.autogen_context, ac,
            None, "sometable", "somecol",
            Column("somecol", INTEGER()),
            Column("somecol", MyType()),
        )

        assert not ac.has_changes()

        ac = ops.AlterColumnOp("sometable", "somecol")
        autogenerate.compare._compare_type(
            self.autogen_context, ac,
            None, "sometable", "somecol",
            Column("somecol", String()),
            Column("somecol", MyType()),
        )
        diff = ac.to_diff_tuple()
        eq_(
            diff[0][0:4],
            ('modify_type', None, 'sometable', 'somecol')
        )

    def test_affinity_typedec(self):
        class MyType(TypeDecorator):
            impl = CHAR

            def load_dialect_impl(self, dialect):
                if dialect.name == 'sqlite':
                    return dialect.type_descriptor(Integer())
                else:
                    return dialect.type_descriptor(CHAR(32))

        uo = ops.AlterColumnOp('sometable', 'somecol')
        autogenerate.compare._compare_type(
            self.autogen_context, uo,
            None, "sometable", "somecol",
            Column("somecol", Integer, nullable=True),
            Column("somecol", MyType())
        )
        assert not uo.has_changes()

    def test_dont_barf_on_already_reflected(self):
        from sqlalchemy.util import OrderedSet
        inspector = Inspector.from_engine(self.bind)
        uo = ops.UpgradeOps(ops=[])
        autogenerate.compare._compare_tables(
            OrderedSet([(None, 'extra'), (None, 'user')]),
            OrderedSet(), inspector,
            MetaData(), uo, self.autogen_context
        )
        eq_(
            [(rec[0], rec[1].name) for rec in uo.as_diffs()],
            [('remove_table', 'extra'), ('remove_table', 'user')]
        )


class AutogenerateDiffTestWSchema(ModelOne, AutogenTest, TestBase):
    __only_on__ = 'postgresql'
    schema = "test_schema"

    def test_diffs(self):
        """test generation of diff rules"""

        metadata = self.m2

        self._update_context(
            include_schemas=True,
        )
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        diffs = uo.as_diffs()

        eq_(
            diffs[0],
            ('add_table', metadata.tables['%s.item' % self.schema])
        )

        eq_(diffs[1][0], 'remove_table')
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], "add_column")
        eq_(diffs[2][1], self.schema)
        eq_(diffs[2][2], "address")
        eq_(diffs[2][3], metadata.tables['%s.address' % self.schema].c.street)

        eq_(diffs[3][0], "add_constraint")
        eq_(diffs[3][1].name, "uq_email")

        eq_(diffs[4][0], "add_column")
        eq_(diffs[4][1], self.schema)
        eq_(diffs[4][2], "order")
        eq_(diffs[4][3], metadata.tables['%s.order' % self.schema].c.user_id)

        eq_(diffs[5][0][0], "modify_type")
        eq_(diffs[5][0][1], self.schema)
        eq_(diffs[5][0][2], "order")
        eq_(diffs[5][0][3], "amount")
        eq_(repr(diffs[5][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[5][0][6]), "Numeric(precision=10, scale=2)")

        self._assert_fk_diff(
            diffs[6], "add_fk",
            "order", ["user_id"],
            "user", ["id"],
            source_schema=config.test_schema
        )

        eq_(diffs[7][0][0], "modify_default")
        eq_(diffs[7][0][1], self.schema)
        eq_(diffs[7][0][2], "user")
        eq_(diffs[7][0][3], "a1")
        eq_(diffs[7][0][6].arg, "x")

        eq_(diffs[8][0][0], 'modify_nullable')
        eq_(diffs[8][0][5], True)
        eq_(diffs[8][0][6], False)

        eq_(diffs[9][0], 'remove_index')
        eq_(diffs[9][1].name, 'pw_idx')

        eq_(diffs[10][0], 'remove_column')
        eq_(diffs[10][3].name, 'pw')


class AutogenerateCustomCompareTypeTest(AutogenTest, TestBase):
    __only_on__ = 'sqlite'

    @classmethod
    def _get_db_schema(cls):
        m = MetaData()

        Table('sometable', m,
              Column('id', Integer, primary_key=True),
              Column('value', Integer))
        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()

        Table('sometable', m,
              Column('id', Integer, primary_key=True),
              Column('value', String))
        return m

    def test_uses_custom_compare_type_function(self):
        my_compare_type = Mock()
        self.context._user_compare_type = my_compare_type

        uo = ops.UpgradeOps(ops=[])

        ctx = self.autogen_context
        autogenerate._produce_net_changes(ctx, uo)

        first_table = self.m2.tables['sometable']
        first_column = first_table.columns['id']

        eq_(len(my_compare_type.mock_calls), 2)

        # We'll just test the first call
        _, args, _ = my_compare_type.mock_calls[0]
        (context, inspected_column, metadata_column,
         inspected_type, metadata_type) = args
        eq_(context, self.context)
        eq_(metadata_column, first_column)
        eq_(metadata_type, first_column.type)
        eq_(inspected_column.name, first_column.name)
        eq_(type(inspected_type), INTEGER)

    def test_column_type_not_modified_custom_compare_type_returns_False(self):
        my_compare_type = Mock()
        my_compare_type.return_value = False
        self.context._user_compare_type = my_compare_type

        diffs = []
        ctx = self.autogen_context
        diffs = []
        autogenerate._produce_net_changes(ctx, diffs)

        eq_(diffs, [])

    def test_column_type_modified_custom_compare_type_returns_True(self):
        my_compare_type = Mock()
        my_compare_type.return_value = True
        self.context._user_compare_type = my_compare_type

        ctx = self.autogen_context
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(ctx, uo)
        diffs = uo.as_diffs()

        eq_(diffs[0][0][0], 'modify_type')
        eq_(diffs[1][0][0], 'modify_type')


class PKConstraintUpgradesIgnoresNullableTest(AutogenTest, TestBase):
    __backend__ = True

    # test workaround for SQLAlchemy issue #3023, alembic issue #199
    @classmethod
    def _get_db_schema(cls):
        m = MetaData()

        Table(
            'person_to_role', m,
            Column('person_id', Integer, autoincrement=False),
            Column('role_id', Integer, autoincrement=False),
            PrimaryKeyConstraint('person_id', 'role_id')
        )
        return m

    @classmethod
    def _get_model_schema(cls):
        return cls._get_db_schema()

    def test_no_change(self):
        diffs = []
        ctx = self.autogen_context
        autogenerate._produce_net_changes(ctx, diffs)
        eq_(diffs, [])


class AutogenKeyTest(AutogenTest, TestBase):
    __only_on__ = 'sqlite'

    @classmethod
    def _get_db_schema(cls):
        m = MetaData()

        Table('someothertable', m,
              Column('id', Integer, primary_key=True),
              Column('value', Integer, key="somekey"),
              )
        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()

        Table('sometable', m,
              Column('id', Integer, primary_key=True),
              Column('value', Integer, key="someotherkey"),
              )
        Table('someothertable', m,
              Column('id', Integer, primary_key=True),
              Column('value', Integer, key="somekey"),
              Column("othervalue", Integer, key="otherkey")
              )
        return m

    symbols = ['someothertable', 'sometable']

    def test_autogen(self):

        uo = ops.UpgradeOps(ops=[])

        ctx = self.autogen_context
        autogenerate._produce_net_changes(ctx, uo)
        diffs = uo.as_diffs()
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].name, "sometable")
        eq_(diffs[1][0], "add_column")
        eq_(diffs[1][3].key, "otherkey")


class AutogenVersionTableTest(AutogenTest, TestBase):
    __only_on__ = 'sqlite'
    version_table_name = 'alembic_version'
    version_table_schema = None

    @classmethod
    def _get_db_schema(cls):
        m = MetaData()
        Table(
            cls.version_table_name, m,
            Column('x', Integer), schema=cls.version_table_schema)
        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()
        return m

    def test_no_version_table(self):
        diffs = []
        ctx = self.autogen_context

        autogenerate._produce_net_changes(ctx, diffs)
        eq_(diffs, [])

    def test_version_table_in_target(self):
        diffs = []
        Table(
            self.version_table_name,
            self.m2, Column('x', Integer), schema=self.version_table_schema)

        ctx = self.autogen_context
        autogenerate._produce_net_changes(ctx, diffs)
        eq_(diffs, [])


class AutogenCustomVersionTableSchemaTest(AutogenVersionTableTest):
    __only_on__ = 'postgresql'
    version_table_schema = 'test_schema'
    configure_opts = {'version_table_schema': 'test_schema'}


class AutogenCustomVersionTableTest(AutogenVersionTableTest):
    version_table_name = 'my_version_table'
    configure_opts = {'version_table': 'my_version_table'}


class AutogenCustomVersionTableAndSchemaTest(AutogenVersionTableTest):
    __only_on__ = 'postgresql'
    version_table_name = 'my_version_table'
    version_table_schema = 'test_schema'
    configure_opts = {
        'version_table': 'my_version_table',
        'version_table_schema': 'test_schema'}


class AutogenerateDiffOrderTest(AutogenTest, TestBase):
    __only_on__ = 'sqlite'

    @classmethod
    def _get_db_schema(cls):
        return MetaData()

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()
        Table('parent', m,
              Column('id', Integer, primary_key=True)
              )

        Table('child', m,
              Column('parent_id', Integer, ForeignKey('parent.id')),
              )

        return m

    def test_diffs_order(self):
        """
        Added in order to test that child tables(tables with FKs) are generated
        before their parent tables
        """

        ctx = self.autogen_context
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(ctx, uo)
        diffs = uo.as_diffs()

        eq_(diffs[0][0], 'add_table')
        eq_(diffs[0][1].name, "parent")
        eq_(diffs[1][0], 'add_table')
        eq_(diffs[1][1].name, "child")


class CompareMetadataTest(ModelOne, AutogenTest, TestBase):
    __only_on__ = 'sqlite'

    def test_compare_metadata(self):
        metadata = self.m2

        diffs = autogenerate.compare_metadata(self.context, metadata)

        eq_(
            diffs[0],
            ('add_table', metadata.tables['item'])
        )

        eq_(diffs[1][0], 'remove_table')
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], "add_column")
        eq_(diffs[2][1], None)
        eq_(diffs[2][2], "address")
        eq_(diffs[2][3], metadata.tables['address'].c.street)

        eq_(diffs[3][0], "add_constraint")
        eq_(diffs[3][1].name, "uq_email")

        eq_(diffs[4][0], "add_column")
        eq_(diffs[4][1], None)
        eq_(diffs[4][2], "order")
        eq_(diffs[4][3], metadata.tables['order'].c.user_id)

        eq_(diffs[5][0][0], "modify_type")
        eq_(diffs[5][0][1], None)
        eq_(diffs[5][0][2], "order")
        eq_(diffs[5][0][3], "amount")
        eq_(repr(diffs[5][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[5][0][6]), "Numeric(precision=10, scale=2)")

        self._assert_fk_diff(
            diffs[6], "add_fk",
            "order", ["user_id"],
            "user", ["id"]
        )

        eq_(diffs[7][0][0], "modify_default")
        eq_(diffs[7][0][1], None)
        eq_(diffs[7][0][2], "user")
        eq_(diffs[7][0][3], "a1")
        eq_(diffs[7][0][6].arg, "x")

        eq_(diffs[8][0][0], 'modify_nullable')
        eq_(diffs[8][0][5], True)
        eq_(diffs[8][0][6], False)

        eq_(diffs[9][0], 'remove_index')
        eq_(diffs[9][1].name, 'pw_idx')

        eq_(diffs[10][0], 'remove_column')
        eq_(diffs[10][3].name, 'pw')

    def test_compare_metadata_include_object(self):
        metadata = self.m2

        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name in ("extra", "order")
            elif type_ == "column":
                return name != "amount"
            else:
                return True

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'include_object': include_object,
            }
        )

        diffs = autogenerate.compare_metadata(context, metadata)

        eq_(diffs[0][0], 'remove_table')
        eq_(diffs[0][1].name, "extra")

        eq_(diffs[1][0], "add_column")
        eq_(diffs[1][1], None)
        eq_(diffs[1][2], "order")
        eq_(diffs[1][3], metadata.tables['order'].c.user_id)

    def test_compare_metadata_include_symbol(self):
        metadata = self.m2

        def include_symbol(table_name, schema_name):
            return table_name in ('extra', 'order')

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'include_symbol': include_symbol,
            }
        )

        diffs = autogenerate.compare_metadata(context, metadata)

        eq_(diffs[0][0], 'remove_table')
        eq_(diffs[0][1].name, "extra")

        eq_(diffs[1][0], "add_column")
        eq_(diffs[1][1], None)
        eq_(diffs[1][2], "order")
        eq_(diffs[1][3], metadata.tables['order'].c.user_id)

        eq_(diffs[2][0][0], "modify_type")
        eq_(diffs[2][0][1], None)
        eq_(diffs[2][0][2], "order")
        eq_(diffs[2][0][3], "amount")
        eq_(repr(diffs[2][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[2][0][6]), "Numeric(precision=10, scale=2)")

        eq_(diffs[2][1][0], 'modify_nullable')
        eq_(diffs[2][1][2], 'order')
        eq_(diffs[2][1][5], False)
        eq_(diffs[2][1][6], True)

    def test_compare_metadata_as_sql(self):
        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={'as_sql': True}
        )
        metadata = self.m2

        assert_raises_message(
            CommandError,
            "autogenerate can't use as_sql=True as it prevents "
            "querying the database for schema information",
            autogenerate.compare_metadata, context, metadata
        )


class PGCompareMetaData(ModelOne, AutogenTest, TestBase):
    __only_on__ = 'postgresql'
    schema = "test_schema"

    def test_compare_metadata_schema(self):
        metadata = self.m2

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                "include_schemas": True
            }
        )

        diffs = autogenerate.compare_metadata(context, metadata)

        eq_(
            diffs[0],
            ('add_table', metadata.tables['test_schema.item'])
        )

        eq_(diffs[1][0], 'remove_table')
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], "add_column")
        eq_(diffs[2][1], "test_schema")
        eq_(diffs[2][2], "address")
        eq_(diffs[2][3], metadata.tables['test_schema.address'].c.street)

        eq_(diffs[3][0], "add_constraint")
        eq_(diffs[3][1].name, "uq_email")

        eq_(diffs[4][0], "add_column")
        eq_(diffs[4][1], "test_schema")
        eq_(diffs[4][2], "order")
        eq_(diffs[4][3], metadata.tables['test_schema.order'].c.user_id)

        eq_(diffs[5][0][0], 'modify_nullable')
        eq_(diffs[5][0][5], False)
        eq_(diffs[5][0][6], True)


class OrigObjectTest(TestBase):
    def setUp(self):
        self.metadata = m = MetaData()
        t = Table(
            't', m,
            Column('id', Integer(), primary_key=True),
            Column('x', Integer())
        )
        self.ix = Index('ix1', t.c.id)
        fk = ForeignKeyConstraint(['t_id'], ['t.id'])
        q = Table(
            'q', m,
            Column('t_id', Integer()),
            fk
        )
        self.table = t
        self.fk = fk
        self.ck = CheckConstraint(t.c.x > 5)
        t.append_constraint(self.ck)
        self.uq = UniqueConstraint(q.c.t_id)
        self.pk = t.primary_key

    def test_drop_fk(self):
        fk = self.fk
        op = ops.DropConstraintOp.from_constraint(fk)
        is_(op.to_constraint(), fk)
        is_(op.reverse().to_constraint(), fk)

    def test_add_fk(self):
        fk = self.fk
        op = ops.AddConstraintOp.from_constraint(fk)
        is_(op.to_constraint(), fk)
        is_(op.reverse().to_constraint(), fk)
        is_not_(None, op.to_constraint().table)

    def test_add_check(self):
        ck = self.ck
        op = ops.AddConstraintOp.from_constraint(ck)
        is_(op.to_constraint(), ck)
        is_(op.reverse().to_constraint(), ck)
        is_not_(None, op.to_constraint().table)

    def test_drop_check(self):
        ck = self.ck
        op = ops.DropConstraintOp.from_constraint(ck)
        is_(op.to_constraint(), ck)
        is_(op.reverse().to_constraint(), ck)
        is_not_(None, op.to_constraint().table)

    def test_add_unique(self):
        uq = self.uq
        op = ops.AddConstraintOp.from_constraint(uq)
        is_(op.to_constraint(), uq)
        is_(op.reverse().to_constraint(), uq)
        is_not_(None, op.to_constraint().table)

    def test_drop_unique(self):
        uq = self.uq
        op = ops.DropConstraintOp.from_constraint(uq)
        is_(op.to_constraint(), uq)
        is_(op.reverse().to_constraint(), uq)
        is_not_(None, op.to_constraint().table)

    def test_add_pk_no_orig(self):
        op = ops.CreatePrimaryKeyOp('pk1', 't', ['x', 'y'])
        pk = op.to_constraint()
        eq_(pk.name, 'pk1')
        eq_(pk.table.name, 't')

    def test_add_pk(self):
        pk = self.pk
        op = ops.AddConstraintOp.from_constraint(pk)
        is_(op.to_constraint(), pk)
        is_(op.reverse().to_constraint(), pk)
        is_not_(None, op.to_constraint().table)

    def test_drop_pk(self):
        pk = self.pk
        op = ops.DropConstraintOp.from_constraint(pk)
        is_(op.to_constraint(), pk)
        is_(op.reverse().to_constraint(), pk)
        is_not_(None, op.to_constraint().table)

    def test_drop_column(self):
        t = self.table

        op = ops.DropColumnOp.from_column_and_tablename(None, 't', t.c.x)
        is_(op.to_column(), t.c.x)
        is_(op.reverse().to_column(), t.c.x)
        is_not_(None, op.to_column().table)

    def test_add_column(self):
        t = self.table

        op = ops.AddColumnOp.from_column_and_tablename(None, 't', t.c.x)
        is_(op.to_column(), t.c.x)
        is_(op.reverse().to_column(), t.c.x)
        is_not_(None, op.to_column().table)

    def test_drop_table(self):
        t = self.table

        op = ops.DropTableOp.from_table(t)
        is_(op.to_table(), t)
        is_(op.reverse().to_table(), t)
        is_(self.metadata, op.to_table().metadata)

    def test_add_table(self):
        t = self.table

        op = ops.CreateTableOp.from_table(t)
        is_(op.to_table(), t)
        is_(op.reverse().to_table(), t)
        is_(self.metadata, op.to_table().metadata)

    def test_drop_index(self):
        op = ops.DropIndexOp.from_index(self.ix)
        is_(op.to_index(), self.ix)
        is_(op.reverse().to_index(), self.ix)

    def test_create_index(self):
        op = ops.CreateIndexOp.from_index(self.ix)
        is_(op.to_index(), self.ix)
        is_(op.reverse().to_index(), self.ix)

