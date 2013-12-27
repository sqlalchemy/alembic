import re
import sys
from unittest import TestCase
from . import Mock

from sqlalchemy import MetaData, Column, Table, Integer, String, Text, \
    Numeric, CHAR, ForeignKey, DATETIME, INTEGER, \
    TypeDecorator, CheckConstraint, Unicode, Enum,\
    UniqueConstraint, Boolean, ForeignKeyConstraint,\
    PrimaryKeyConstraint, Index, func
from sqlalchemy.types import NULLTYPE, TIMESTAMP
from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.sql import and_, column, literal_column

from alembic import autogenerate, util, compat
from alembic.migration import MigrationContext
from . import staging_env, sqlite_db, clear_staging_env, eq_, \
        eq_ignore_whitespace, db_for_dialect

py3k = sys.version_info >= (3, )



names_in_this_test = set()
def _default_include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in names_in_this_test
    else:
        return True

_default_object_filters = [
    _default_include_object
]
from sqlalchemy import event
@event.listens_for(Table, "after_parent_attach")
def new_table(table, parent):
    names_in_this_test.add(table.name)

class AutogenTest(object):
    @classmethod
    def _get_bind(cls):
        return sqlite_db()

    @classmethod
    def setup_class(cls):
        staging_env()
        cls.bind = cls._get_bind()
        cls.m1 = cls._get_db_schema()
        cls.m1.create_all(cls.bind)
        cls.m2 = cls._get_model_schema()

        conn = cls.bind.connect()
        cls.context = context = MigrationContext.configure(
            connection=conn,
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'target_metadata': cls.m2,
                'upgrade_token': "upgrades",
                'downgrade_token': "downgrades",
                'alembic_module_prefix': 'op.',
                'sqlalchemy_module_prefix': 'sa.',
            }
        )

        connection = context.bind
        cls.autogen_context = {
            'imports': set(),
            'connection': connection,
            'dialect': connection.dialect,
            'context': context
            }

    @classmethod
    def teardown_class(cls):
        cls.m1.drop_all(cls.bind)
        clear_staging_env()


class AutogenCrossSchemaTest(AutogenTest, TestCase):
    @classmethod
    def _get_bind(cls):
        cls.test_schema_name = "test_schema"
        return db_for_dialect('postgresql')

    @classmethod
    def _get_db_schema(cls):
        m = MetaData()
        Table('t1', m,
                Column('x', Integer)
            )
        Table('t2', m,
                Column('y', Integer),
                schema=cls.test_schema_name
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
                schema=cls.test_schema_name
            )
        return m

    def test_default_schema_omitted_upgrade(self):
        metadata = self.m2
        connection = self.context.bind
        diffs = []
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t3"
            else:
                return True
        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          object_filters=[include_object],
                                          include_schemas=True
                                          )
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, None)

    def test_alt_schema_included_upgrade(self):
        metadata = self.m2
        connection = self.context.bind
        diffs = []
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t4"
            else:
                return True
        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          object_filters=[include_object],
                                          include_schemas=True
                                          )
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, self.test_schema_name)

    def test_default_schema_omitted_downgrade(self):
        metadata = self.m2
        connection = self.context.bind
        diffs = []
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t1"
            else:
                return True
        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          object_filters=[include_object],
                                          include_schemas=True
                                          )
        eq_(diffs[0][0], "remove_table")
        eq_(diffs[0][1].schema, None)

    def test_alt_schema_included_downgrade(self):
        metadata = self.m2
        connection = self.context.bind
        diffs = []
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t2"
            else:
                return True
        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          object_filters=[include_object],
                                          include_schemas=True
                                          )
        eq_(diffs[0][0], "remove_table")
        eq_(diffs[0][1].schema, self.test_schema_name)


class ModelOne(object):
    schema = None

    @classmethod
    def _get_db_schema(cls):
        schema = cls.schema

        m = MetaData(schema=schema)

        Table('user', m,
            Column('id', Integer, primary_key=True),
            Column('name', String(50)),
            Column('a1', Text),
            Column("pw", String(50))
        )

        Table('address', m,
            Column('id', Integer, primary_key=True),
            Column('email_address', String(100), nullable=False),
        )

        Table('order', m,
            Column('order_id', Integer, primary_key=True),
            Column("amount", Numeric(8, 2), nullable=False,
                    server_default="0"),
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
        )

        Table('order', m,
            Column('order_id', Integer, primary_key=True),
            Column('amount', Numeric(10, 2), nullable=True,
                        server_default="0"),
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



class AutogenerateDiffTest(ModelOne, AutogenTest, TestCase):

    def test_diffs(self):
        """test generation of diff rules"""

        metadata = self.m2
        connection = self.context.bind
        diffs = []
        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          object_filters=_default_object_filters,
                                    )

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

        eq_(diffs[3][0], "add_column")
        eq_(diffs[3][1], None)
        eq_(diffs[3][2], "order")
        eq_(diffs[3][3], metadata.tables['order'].c.user_id)

        eq_(diffs[4][0][0], "modify_type")
        eq_(diffs[4][0][1], None)
        eq_(diffs[4][0][2], "order")
        eq_(diffs[4][0][3], "amount")
        eq_(repr(diffs[4][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[4][0][6]), "Numeric(precision=10, scale=2)")

        eq_(diffs[5][0], 'remove_column')
        eq_(diffs[5][3].name, 'pw')

        eq_(diffs[6][0][0], "modify_default")
        eq_(diffs[6][0][1], None)
        eq_(diffs[6][0][2], "user")
        eq_(diffs[6][0][3], "a1")
        eq_(diffs[6][0][6].arg, "x")

        eq_(diffs[7][0][0], 'modify_nullable')
        eq_(diffs[7][0][5], True)
        eq_(diffs[7][0][6], False)

    def test_render_nothing(self):
        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'target_metadata': self.m1,
                'upgrade_token': "upgrades",
                'downgrade_token': "downgrades",
            }
        )
        template_args = {}
        autogenerate._produce_migration_diffs(context, template_args, set())

        eq_(re.sub(r"u'", "'", template_args['upgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###""")
        eq_(re.sub(r"u'", "'", template_args['downgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###""")

    def test_render_diffs_standard(self):
        """test a full render including indentation"""

        template_args = {}
        autogenerate._produce_migration_diffs(self.context, template_args, set())

        eq_(re.sub(r"u'", "'", template_args['upgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    op.create_table('item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(length=100), nullable=True),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.CheckConstraint('len(description) > 5'),
    sa.ForeignKeyConstraint(['order_id'], ['order.order_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('extra')
    op.add_column('address', sa.Column('street', sa.String(length=50), nullable=True))
    op.add_column('order', sa.Column('user_id', sa.Integer(), nullable=True))
    op.alter_column('order', 'amount',
               existing_type=sa.NUMERIC(precision=8, scale=2),
               type_=sa.Numeric(precision=10, scale=2),
               nullable=True,
               existing_server_default='0')
    op.drop_column('user', 'pw')
    op.alter_column('user', 'a1',
               existing_type=sa.TEXT(),
               server_default='x',
               existing_nullable=True)
    op.alter_column('user', 'name',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)
    ### end Alembic commands ###""")

        eq_(re.sub(r"u'", "'", template_args['downgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'name',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
    op.alter_column('user', 'a1',
               existing_type=sa.TEXT(),
               server_default=None,
               existing_nullable=True)
    op.add_column('user', sa.Column('pw', sa.VARCHAR(length=50), nullable=True))
    op.alter_column('order', 'amount',
               existing_type=sa.Numeric(precision=10, scale=2),
               type_=sa.NUMERIC(precision=8, scale=2),
               nullable=False,
               existing_server_default='0')
    op.drop_column('order', 'user_id')
    op.drop_column('address', 'street')
    op.create_table('extra',
    sa.Column('x', sa.CHAR(), nullable=True),
    sa.Column('uid', sa.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['user.id'], )
    )
    op.drop_table('item')
    ### end Alembic commands ###""")

    def test_include_symbol(self):
        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'target_metadata': self.m2,
                'include_symbol': lambda name, schema=None:
                                    name in ('address', 'order'),
                'upgrade_token': "upgrades",
                'downgrade_token': "downgrades",
                'alembic_module_prefix': 'op.',
                'sqlalchemy_module_prefix': 'sa.',
            }
        )
        template_args = {}
        autogenerate._produce_migration_diffs(context, template_args, set())
        template_args['upgrades'] = template_args['upgrades'].replace("u'", "'")
        template_args['downgrades'] = template_args['downgrades'].\
                                        replace("u'", "'")
        assert "alter_column('user'" not in template_args['upgrades']
        assert "alter_column('user'" not in template_args['downgrades']
        assert "alter_column('order'" in template_args['upgrades']
        assert "alter_column('order'" in template_args['downgrades']

    def test_include_object(self):
        def include_object(obj, name, type_, reflected, compare_to):
            assert obj.name == name
            if type_ == "table":
                if reflected:
                    assert obj.metadata is not self.m2
                else:
                    assert obj.metadata is self.m2
                return name in ("address", "order")
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
                'upgrade_token': "upgrades",
                'downgrade_token': "downgrades",
                'alembic_module_prefix': 'op.',
                'sqlalchemy_module_prefix': 'sa.',
            }
        )
        template_args = {}
        autogenerate._produce_migration_diffs(context, template_args, set())
        template_args['upgrades'] = template_args['upgrades'].replace("u'", "'")
        template_args['downgrades'] = template_args['downgrades'].\
                                        replace("u'", "'")

        assert "alter_column('user'" not in template_args['upgrades']
        assert "alter_column('user'" not in template_args['downgrades']
        assert "'street'" not in template_args['upgrades']
        assert "'street'" not in template_args['downgrades']
        assert "alter_column('order'" in template_args['upgrades']
        assert "alter_column('order'" in template_args['downgrades']

    def test_skip_null_type_comparison_reflected(self):
        diff = []
        autogenerate.compare._compare_type(None, "sometable", "somecol",
            Column("somecol", NULLTYPE),
            Column("somecol", Integer()),
            diff, self.autogen_context
        )
        assert not diff

    def test_skip_null_type_comparison_local(self):
        diff = []
        autogenerate.compare._compare_type(None, "sometable", "somecol",
            Column("somecol", Integer()),
            Column("somecol", NULLTYPE),
            diff, self.autogen_context
        )
        assert not diff

    def test_affinity_typedec(self):
        class MyType(TypeDecorator):
            impl = CHAR

            def load_dialect_impl(self, dialect):
                if dialect.name == 'sqlite':
                    return dialect.type_descriptor(Integer())
                else:
                    return dialect.type_descriptor(CHAR(32))

        diff = []
        autogenerate.compare._compare_type(None, "sometable", "somecol",
            Column("somecol", Integer, nullable=True),
            Column("somecol", MyType()),
            diff, self.autogen_context
        )
        assert not diff

    def test_dont_barf_on_already_reflected(self):
        diffs = []
        from sqlalchemy.util import OrderedSet
        inspector = Inspector.from_engine(self.bind)
        autogenerate.compare._compare_tables(
            OrderedSet([(None, 'extra'), (None, 'user')]),
            OrderedSet(), [], inspector,
                MetaData(), diffs, self.autogen_context
        )
        eq_(
            [(rec[0], rec[1].name) for rec in diffs],
            [('remove_table', 'extra'), ('remove_table', 'user')]
        )

class AutogenerateDiffTestWSchema(ModelOne, AutogenTest, TestCase):
    schema = "test_schema"


    @classmethod
    def _get_bind(cls):
        return db_for_dialect('postgresql')

    def test_diffs(self):
        """test generation of diff rules"""

        metadata = self.m2
        connection = self.context.bind
        diffs = []
        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          object_filters=_default_object_filters,
                                          include_schemas=True
                                          )

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

        eq_(diffs[3][0], "add_column")
        eq_(diffs[3][1], self.schema)
        eq_(diffs[3][2], "order")
        eq_(diffs[3][3], metadata.tables['%s.order' % self.schema].c.user_id)

        eq_(diffs[4][0][0], "modify_type")
        eq_(diffs[4][0][1], self.schema)
        eq_(diffs[4][0][2], "order")
        eq_(diffs[4][0][3], "amount")
        eq_(repr(diffs[4][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[4][0][6]), "Numeric(precision=10, scale=2)")

        eq_(diffs[5][0], 'remove_column')
        eq_(diffs[5][3].name, 'pw')

        eq_(diffs[6][0][0], "modify_default")
        eq_(diffs[6][0][1], self.schema)
        eq_(diffs[6][0][2], "user")
        eq_(diffs[6][0][3], "a1")
        eq_(diffs[6][0][6].arg, "x")

        eq_(diffs[7][0][0], 'modify_nullable')
        eq_(diffs[7][0][5], True)
        eq_(diffs[7][0][6], False)

    def test_render_nothing(self):
        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                'compare_type': True,
                'compare_server_default': True,
                'target_metadata': self.m1,
                'upgrade_token': "upgrades",
                'downgrade_token': "downgrades",
                'alembic_module_prefix': 'op.',
                'sqlalchemy_module_prefix': 'sa.',
            }
        )
        template_args = {}
        autogenerate._produce_migration_diffs(context, template_args, set(),
                include_symbol=lambda name, schema: False
            )
        eq_(re.sub(r"u'", "'", template_args['upgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###""")
        eq_(re.sub(r"u'", "'", template_args['downgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###""")

    def test_render_diffs_extras(self):
        """test a full render including indentation (include and schema)"""

        template_args = {}
        autogenerate._produce_migration_diffs(
                        self.context, template_args, set(),
                        include_object=_default_include_object,
                        include_schemas=True
                        )

        eq_(re.sub(r"u'", "'", template_args['upgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    op.create_table('item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(length=100), nullable=True),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.CheckConstraint('len(description) > 5'),
    sa.ForeignKeyConstraint(['order_id'], ['%(schema)s.order.order_id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema='%(schema)s'
    )
    op.drop_table('extra', schema='%(schema)s')
    op.add_column('address', sa.Column('street', sa.String(length=50), nullable=True), schema='%(schema)s')
    op.add_column('order', sa.Column('user_id', sa.Integer(), nullable=True), schema='%(schema)s')
    op.alter_column('order', 'amount',
               existing_type=sa.NUMERIC(precision=8, scale=2),
               type_=sa.Numeric(precision=10, scale=2),
               nullable=True,
               existing_server_default='0::numeric',
               schema='%(schema)s')
    op.drop_column('user', 'pw', schema='%(schema)s')
    op.alter_column('user', 'a1',
               existing_type=sa.TEXT(),
               server_default='x',
               existing_nullable=True,
               schema='%(schema)s')
    op.alter_column('user', 'name',
               existing_type=sa.VARCHAR(length=50),
               nullable=False,
               schema='%(schema)s')
    ### end Alembic commands ###""" % {"schema": self.schema})

        eq_(re.sub(r"u'", "'", template_args['downgrades']),
"""### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'name',
               existing_type=sa.VARCHAR(length=50),
               nullable=True,
               schema='%(schema)s')
    op.alter_column('user', 'a1',
               existing_type=sa.TEXT(),
               server_default=None,
               existing_nullable=True,
               schema='%(schema)s')
    op.add_column('user', sa.Column('pw', sa.VARCHAR(length=50), nullable=True), schema='%(schema)s')
    op.alter_column('order', 'amount',
               existing_type=sa.Numeric(precision=10, scale=2),
               type_=sa.NUMERIC(precision=8, scale=2),
               nullable=False,
               existing_server_default='0::numeric',
               schema='%(schema)s')
    op.drop_column('order', 'user_id', schema='%(schema)s')
    op.drop_column('address', 'street', schema='%(schema)s')
    op.create_table('extra',
    sa.Column('x', sa.CHAR(length=1), autoincrement=False, nullable=True),
    sa.Column('uid', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['uid'], ['%(schema)s.user.id'], name='extra_uid_fkey'),
    schema='%(schema)s'
    )
    op.drop_table('item', schema='%(schema)s')
    ### end Alembic commands ###""" % {"schema": self.schema})


class AutogenerateUniqueIndexTest(TestCase):

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

        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "uq_user_name")

        eq_(diffs[1][0], "remove_index")
        eq_(diffs[1][1].name, "ix_user_name")


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
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "uq_email_address")


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

        eq_(diffs[0][0], "remove_constraint")
        eq_(diffs[0][1].name, "nochange")

        eq_(diffs[1][0], "add_constraint")
        eq_(diffs[1][1].name, "nochange")


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
            Column('x', String(20), unique=True)
            )
        Table('nothing_changed_related', m1,
            Column('id1', Integer),
            Column('id2', Integer),
            ForeignKeyConstraint(['id1', 'id2'],
                    ['nothing_changed.id1', 'nothing_changed.id2'])
            )

        Table('nothing_changed', m2,
            Column('id1', Integer, primary_key=True),
            Column('id2', Integer, primary_key=True),
            Column('x', String(20), unique=True)
            )
        Table('nothing_changed_related', m2,
            Column('id1', Integer),
            Column('id2', Integer),
            ForeignKeyConstraint(['id1', 'id2'],
                    ['nothing_changed.id1', 'nothing_changed.id2'])
            )


        diffs = self._fixture(m1, m2)
        eq_(diffs, [])


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

        diffs = set((cmd, obj.name) for cmd, obj in diffs)
        assert ("remove_index", "xidx") in diffs


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

        diffs = ((cmd, obj.name) for cmd, obj in diffs)
        assert ("remove_constraint", "xidx") in diffs

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

    def _fixture(self, m1, m2):
        self.metadata, model_metadata = m1, m2
        self.metadata.create_all(self.bind)

        with self.bind.connect() as conn:
            self.context = context = MigrationContext.configure(
                connection=conn,
                opts={
                    'compare_type': True,
                    'compare_server_default': True,
                    'target_metadata': model_metadata,
                    'upgrade_token': "upgrades",
                    'downgrade_token': "downgrades",
                    'alembic_module_prefix': 'op.',
                    'sqlalchemy_module_prefix': 'sa.',
                }
            )

            connection = context.bind
            autogen_context = {
                'imports': set(),
                'connection': connection,
                'dialect': connection.dialect,
                'context': context
                }
            diffs = []
            autogenerate._produce_net_changes(connection, model_metadata, diffs,
                                              autogen_context,
                                              object_filters=_default_object_filters,
                                        )
            return diffs

    reports_unnamed_constraints = False

    def setUp(self):
        staging_env()
        self.bind = self._get_bind()

    def tearDown(self):
        self.metadata.drop_all(self.bind)
        clear_staging_env()

    @classmethod
    def _get_bind(cls):
        return sqlite_db()



class PGUniqueIndexTest(AutogenerateUniqueIndexTest):
    reports_unnamed_constraints = True

    @classmethod
    def _get_bind(cls):
        return db_for_dialect('postgresql')


class MySQLUniqueIndexTest(AutogenerateUniqueIndexTest):
    reports_unnamed_constraints = True

    @classmethod
    def _get_bind(cls):
        return db_for_dialect('mysql')


class AutogenerateCustomCompareTypeTest(AutogenTest, TestCase):
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

        diffs = []
        autogenerate._produce_net_changes(self.context.bind, self.m2,
                                    diffs, self.autogen_context)

        first_table = self.m2.tables['sometable']
        first_column = first_table.columns['id']

        eq_(len(my_compare_type.mock_calls), 2)

        # We'll just test the first call
        _, args, _ = my_compare_type.mock_calls[0]
        context, inspected_column, metadata_column, inspected_type, metadata_type = args
        eq_(context, self.context)
        eq_(metadata_column, first_column)
        eq_(metadata_type, first_column.type)
        eq_(inspected_column.name, first_column.name)
        eq_(type(inspected_type), INTEGER)

    def test_column_type_not_modified_when_custom_compare_type_returns_False(self):
        my_compare_type = Mock()
        my_compare_type.return_value = False
        self.context._user_compare_type = my_compare_type

        diffs = []
        autogenerate._produce_net_changes(self.context.bind, self.m2,
                                                diffs, self.autogen_context)

        eq_(diffs, [])

    def test_column_type_modified_when_custom_compare_type_returns_True(self):
        my_compare_type = Mock()
        my_compare_type.return_value = True
        self.context._user_compare_type = my_compare_type

        diffs = []
        autogenerate._produce_net_changes(self.context.bind, self.m2,
                                                diffs, self.autogen_context)

        eq_(diffs[0][0][0], 'modify_type')
        eq_(diffs[1][0][0], 'modify_type')


class AutogenKeyTest(AutogenTest, TestCase):
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
        metadata = self.m2
        connection = self.context.bind

        diffs = []

        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context,
                                          include_schemas=False
                                          )
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].name, "sometable")
        eq_(diffs[1][0], "add_column")
        eq_(diffs[1][3].key, "otherkey")

class AutogenerateDiffOrderTest(AutogenTest, TestCase):
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

        metadata = self.m2
        connection = self.context.bind
        diffs = []

        autogenerate._produce_net_changes(connection, metadata, diffs,
                                          self.autogen_context
                                          )

        eq_(diffs[0][0], 'add_table')
        eq_(diffs[0][1].name, "parent")
        eq_(diffs[1][0], 'add_table')
        eq_(diffs[1][1].name, "child")

