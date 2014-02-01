import re
import sys
from unittest import TestCase

from sqlalchemy import MetaData, Column, Table, Integer, String, Text, \
    Numeric, CHAR, ForeignKey, DATETIME, INTEGER, \
    TypeDecorator, CheckConstraint, Unicode, Enum,\
    UniqueConstraint, Boolean, ForeignKeyConstraint,\
    PrimaryKeyConstraint, Index, func
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.sql import and_, column, literal_column

from alembic import autogenerate, util, compat
from . import eq_, eq_ignore_whitespace

py3k = sys.version_info >= (3, )

class AutogenRenderTest(TestCase):
    """test individual directives"""

    @classmethod
    def setup_class(cls):
        cls.autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
            },
            'dialect': mysql.dialect()
        }
        cls.pg_autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
            },
            'dialect': postgresql.dialect()
        }


    def test_render_add_index(self):
        """
        autogenerate.render._add_index
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
        )
        idx = Index('test_active_code_idx', t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._add_index(idx, self.autogen_context),
            "op.create_index('test_active_code_idx', 'test', "
            "['active', 'code'], unique=False)"
        )

    def test_render_add_index_schema(self):
        """
        autogenerate.render._add_index using schema
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
            schema='CamelSchema'
        )
        idx = Index('test_active_code_idx', t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._add_index(idx, self.autogen_context),
            "op.create_index('test_active_code_idx', 'test', "
            "['active', 'code'], unique=False, schema='CamelSchema')"
        )

    def test_render_add_index_pg_where(self):
        autogen_context = self.pg_autogen_context

        m = MetaData()
        t = Table('t', m,
            Column('x', String),
            Column('y', String)
            )

        idx = Index('foo_idx', t.c.x, t.c.y,
                            postgresql_where=(t.c.y == 'something'))

        if compat.sqla_08:
            eq_ignore_whitespace(
                autogenerate.render._add_index(idx, autogen_context),
                """op.create_index('foo_idx', 't', ['x', 'y'], unique=False, """
                    """postgresql_where=sa.text("t.y = 'something'"))"""
            )
        else:
            eq_ignore_whitespace(
                autogenerate.render._add_index(idx, autogen_context),
                """op.create_index('foo_idx', 't', ['x', 'y'], unique=False, """
                    """postgresql_where=sa.text('t.y = %(y_1)s'))"""
            )

    # def test_render_add_index_func(self):
    #     """
    #     autogenerate.render._drop_index using func -- TODO: SQLA needs to
    #     reflect expressions as well as columns
    #     """
    #     m = MetaData()
    #     t = Table('test', m,
    #         Column('id', Integer, primary_key=True),
    #         Column('active', Boolean()),
    #         Column('code', String(255)),
    #     )
    #     idx = Index('test_active_lower_code_idx', t.c.active, func.lower(t.c.code))
    #     eq_ignore_whitespace(
    #         autogenerate.render._add_index(idx, self.autogen_context),
    #         ""
    #     )

    def test_drop_index(self):
        """
        autogenerate.render._drop_index
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
        )
        idx = Index('test_active_code_idx', t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._drop_index(idx, self.autogen_context),
            "op.drop_index('test_active_code_idx', table_name='test')"
        )

    def test_drop_index_schema(self):
        """
        autogenerate.render._drop_index using schema
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
            schema='CamelSchema'
        )
        idx = Index('test_active_code_idx', t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._drop_index(idx, self.autogen_context),
            "op.drop_index('test_active_code_idx', " +
                          "table_name='test', schema='CamelSchema')"
        )

    def test_add_unique_constraint(self):
        """
        autogenerate.render._add_unique_constraint
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
        )
        uq = UniqueConstraint(t.c.code, name='uq_test_code')
        eq_ignore_whitespace(
            autogenerate.render._add_unique_constraint(uq, self.autogen_context),
            "op.create_unique_constraint('uq_test_code', 'test', ['code'])"
        )

    def test_add_unique_constraint_schema(self):
        """
        autogenerate.render._add_unique_constraint using schema
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
            schema='CamelSchema'
        )
        uq = UniqueConstraint(t.c.code, name='uq_test_code')
        eq_ignore_whitespace(
            autogenerate.render._add_unique_constraint(uq, self.autogen_context),
            "op.create_unique_constraint('uq_test_code', 'test', ['code'], schema='CamelSchema')"
        )

    def test_drop_constraint(self):
        """
        autogenerate.render._drop_constraint
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
        )
        uq = UniqueConstraint(t.c.code, name='uq_test_code')
        eq_ignore_whitespace(
            autogenerate.render._drop_constraint(uq, self.autogen_context),
            "op.drop_constraint('uq_test_code', 'test')"
        )

    def test_drop_constraint_schema(self):
        """
        autogenerate.render._drop_constraint using schema
        """
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('active', Boolean()),
            Column('code', String(255)),
            schema='CamelSchema'
        )
        uq = UniqueConstraint(t.c.code, name='uq_test_code')
        eq_ignore_whitespace(
            autogenerate.render._drop_constraint(uq, self.autogen_context),
            "op.drop_constraint('uq_test_code', 'test', schema='CamelSchema')"
        )

    def test_render_table_upgrade(self):
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('name', Unicode(255)),
            Column("address_id", Integer, ForeignKey("address.id")),
            Column("timestamp", DATETIME, server_default="NOW()"),
            Column("amount", Numeric(5, 2)),
            UniqueConstraint("name", name="uq_name"),
            UniqueConstraint("timestamp"),
        )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('name', sa.Unicode(length=255), nullable=True),"
            "sa.Column('address_id', sa.Integer(), nullable=True),"
            "sa.Column('timestamp', sa.DATETIME(), "
                "server_default='NOW()', "
                "nullable=True),"
            "sa.Column('amount', sa.Numeric(precision=5, scale=2), nullable=True),"
            "sa.ForeignKeyConstraint(['address_id'], ['address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "sa.UniqueConstraint('name', name='uq_name'),"
            "sa.UniqueConstraint('timestamp')"
            ")"
        )

    def test_render_table_w_schema(self):
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('q', Integer, ForeignKey('address.id')),
            schema='foo'
        )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "schema='foo'"
            ")"
        )

    def test_render_table_w_fk_schema(self):
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('q', Integer, ForeignKey('foo.address.id')),
        )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['foo.address.id'], ),"
            "sa.PrimaryKeyConstraint('id')"
            ")"
        )

    def test_render_table_w_metadata_schema(self):
        m = MetaData(schema="foo")
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('q', Integer, ForeignKey('address.id')),
        )
        eq_ignore_whitespace(
            re.sub(r"u'", "'", autogenerate.render._add_table(t, self.autogen_context)),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['foo.address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "schema='foo'"
            ")"
        )

    def test_render_table_w_metadata_schema_override(self):
        m = MetaData(schema="foo")
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('q', Integer, ForeignKey('bar.address.id')),
        )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['bar.address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "schema='foo'"
            ")"
        )

    def test_render_addtl_args(self):
        m = MetaData()
        t = Table('test', m,
            Column('id', Integer, primary_key=True),
            Column('q', Integer, ForeignKey('bar.address.id')),
            sqlite_autoincrement=True, mysql_engine="InnoDB"
        )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['bar.address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "mysql_engine='InnoDB',sqlite_autoincrement=True)"
        )

    def test_render_drop_table(self):
        eq_(
            autogenerate.render._drop_table(Table("sometable", MetaData()),
                        self.autogen_context),
            "op.drop_table('sometable')"
        )

    def test_render_drop_table_w_schema(self):
        eq_(
            autogenerate.render._drop_table(
                Table("sometable", MetaData(), schema='foo'),
                self.autogen_context),
            "op.drop_table('sometable', schema='foo')"
        )

    def test_render_table_no_implicit_check(self):
        m = MetaData()
        t = Table('test', m, Column('x', Boolean()))

        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',sa.Column('x', sa.Boolean(), nullable=True))"
        )

    def test_render_empty_pk_vs_nonempty_pk(self):
        m = MetaData()
        t1 = Table('t1', m, Column('x', Integer))
        t2 = Table('t2', m, Column('x', Integer, primary_key=True))

        eq_ignore_whitespace(
            autogenerate.render._add_table(t1, self.autogen_context),
            "op.create_table('t1',sa.Column('x', sa.Integer(), nullable=True))"
        )

        eq_ignore_whitespace(
            autogenerate.render._add_table(t2, self.autogen_context),
            "op.create_table('t2',"
            "sa.Column('x', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('x'))"
        )

    def test_render_add_column(self):
        eq_(
            autogenerate.render._add_column(
                    None, "foo", Column("x", Integer, server_default="5"),
                        self.autogen_context),
            "op.add_column('foo', sa.Column('x', sa.Integer(), "
                "server_default='5', nullable=True))"
        )

    def test_render_add_column_w_schema(self):
        eq_(
            autogenerate.render._add_column(
                    "foo", "bar", Column("x", Integer, server_default="5"),
                        self.autogen_context),
            "op.add_column('bar', sa.Column('x', sa.Integer(), "
                "server_default='5', nullable=True), schema='foo')"
        )

    def test_render_drop_column(self):
        eq_(
            autogenerate.render._drop_column(
                    None, "foo", Column("x", Integer, server_default="5"),
                        self.autogen_context),

            "op.drop_column('foo', 'x')"
        )

    def test_render_drop_column_w_schema(self):
        eq_(
            autogenerate.render._drop_column(
                    "foo", "bar", Column("x", Integer, server_default="5"),
                        self.autogen_context),

            "op.drop_column('bar', 'x', schema='foo')"
        )

    def test_render_quoted_server_default(self):
        eq_(
            autogenerate.render._render_server_default(
                "nextval('group_to_perm_group_to_perm_id_seq'::regclass)",
                    self.autogen_context),
            '"nextval(\'group_to_perm_group_to_perm_id_seq\'::regclass)"'
        )

    def test_render_col_with_server_default(self):
        c = Column('updated_at', TIMESTAMP(),
                server_default='TIMEZONE("utc", CURRENT_TIMESTAMP)',
                nullable=False)
        result = autogenerate.render._render_column(
                    c, self.autogen_context
                )
        eq_(
            result,
            'sa.Column(\'updated_at\', sa.TIMESTAMP(), '
                'server_default=\'TIMEZONE("utc", CURRENT_TIMESTAMP)\', '
                'nullable=False)'
        )

    def test_render_col_autoinc_false_mysql(self):
        c = Column('some_key', Integer, primary_key=True, autoincrement=False)
        Table('some_table', MetaData(), c)
        result = autogenerate.render._render_column(
                    c, self.autogen_context
                )
        eq_(
            result,
            'sa.Column(\'some_key\', sa.Integer(), '
                'autoincrement=False, '
                'nullable=False)'
        )

    def test_render_custom(self):

        def render(type_, obj, context):
            if type_ == "foreign_key":
                return None
            if type_ == "column":
                if obj.name == "y":
                    return None
                else:
                    return "col(%s)" % obj.name
            return "render:%s" % type_

        autogen_context = {"opts": {
            'render_item': render,
            'alembic_module_prefix': 'sa.'
        }}

        t = Table('t', MetaData(),
                Column('x', Integer),
                Column('y', Integer),
                PrimaryKeyConstraint('x'),
                ForeignKeyConstraint(['x'], ['y'])
            )
        result = autogenerate.render._add_table(
                    t, autogen_context
                )
        eq_(
            result, """sa.create_table('t',
col(x),
render:primary_key\n)"""
        )

    def test_render_modify_type(self):
        eq_ignore_whitespace(
            autogenerate.render._modify_col(
                        "sometable", "somecolumn",
                        self.autogen_context,
                        type_=CHAR(10), existing_type=CHAR(20)),
            "op.alter_column('sometable', 'somecolumn', "
                "existing_type=sa.CHAR(length=20), type_=sa.CHAR(length=10))"
        )

    def test_render_modify_type_w_schema(self):
        eq_ignore_whitespace(
            autogenerate.render._modify_col(
                        "sometable", "somecolumn",
                        self.autogen_context,
                        type_=CHAR(10), existing_type=CHAR(20),
                        schema='foo'),
            "op.alter_column('sometable', 'somecolumn', "
                "existing_type=sa.CHAR(length=20), type_=sa.CHAR(length=10), "
                "schema='foo')"
        )

    def test_render_modify_nullable(self):
        eq_ignore_whitespace(
            autogenerate.render._modify_col(
                        "sometable", "somecolumn",
                        self.autogen_context,
                        existing_type=Integer(),
                        nullable=True),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True)"
        )

    def test_render_modify_nullable_w_schema(self):
        eq_ignore_whitespace(
            autogenerate.render._modify_col(
                        "sometable", "somecolumn",
                        self.autogen_context,
                        existing_type=Integer(),
                        nullable=True, schema='foo'),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True, schema='foo')"
        )

    def test_render_fk_constraint_kwarg(self):
        m = MetaData()
        t1 = Table('t', m, Column('c', Integer))
        t2 = Table('t2', m, Column('c_rem', Integer))

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], onupdate="CASCADE")
        if not util.sqla_08:
            t1.append_constraint(fk)

        eq_ignore_whitespace(
            re.sub(r"u'", "'", autogenerate.render._render_constraint(fk, self.autogen_context)),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], onupdate='CASCADE')"
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], ondelete="CASCADE")
        if not util.sqla_08:
            t1.append_constraint(fk)

        eq_ignore_whitespace(
            re.sub(r"u'", "'", autogenerate.render._render_constraint(fk, self.autogen_context)),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], ondelete='CASCADE')"
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], deferrable=True)
        if not util.sqla_08:
            t1.append_constraint(fk)
        eq_ignore_whitespace(
            re.sub(r"u'", "'", autogenerate.render._render_constraint(fk, self.autogen_context)),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], deferrable=True)"
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], initially="XYZ")
        if not util.sqla_08:
            t1.append_constraint(fk)
        eq_ignore_whitespace(
            re.sub(r"u'", "'", autogenerate.render._render_constraint(fk, self.autogen_context)),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], initially='XYZ')"
        )

    def test_render_fk_constraint_use_alter(self):
        m = MetaData()
        Table('t', m, Column('c', Integer))
        t2 = Table('t2', m, Column('c_rem', Integer,
                                ForeignKey('t.c', name="fk1", use_alter=True)))
        const = list(t2.foreign_keys)[0].constraint

        eq_ignore_whitespace(
            autogenerate.render._render_constraint(const, self.autogen_context),
            "sa.ForeignKeyConstraint(['c_rem'], ['t.c'], "
                    "name='fk1', use_alter=True)"
        )

    def test_render_check_constraint_literal(self):
        eq_ignore_whitespace(
            autogenerate.render._render_check_constraint(
                CheckConstraint("im a constraint", name='cc1'),
                self.autogen_context
            ),
            "sa.CheckConstraint('im a constraint', name='cc1')"
        )

    def test_render_check_constraint_sqlexpr(self):
        c = column('c')
        five = literal_column('5')
        ten = literal_column('10')
        eq_ignore_whitespace(
            autogenerate.render._render_check_constraint(
                CheckConstraint(and_(c > five, c < ten)),
                self.autogen_context
            ),
            "sa.CheckConstraint('c > 5 AND c < 10')"
        )

    def test_render_unique_constraint_opts(self):
        m = MetaData()
        t = Table('t', m, Column('c', Integer))
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(
                UniqueConstraint(t.c.c, name='uq_1', deferrable='XYZ'),
                self.autogen_context
            ),
            "sa.UniqueConstraint('c', deferrable='XYZ', name='uq_1')"
        )

    def test_render_modify_nullable_w_default(self):
        eq_ignore_whitespace(
            autogenerate.render._modify_col(
                        "sometable", "somecolumn",
                        self.autogen_context,
                        existing_type=Integer(),
                        existing_server_default="5",
                        nullable=True),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True, "
            "existing_server_default='5')"
        )

    def test_render_enum(self):
        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                        Enum("one", "two", "three", name="myenum"),
                        self.autogen_context),
            "sa.Enum('one', 'two', 'three', name='myenum')"
        )
        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                        Enum("one", "two", "three"),
                        self.autogen_context),
            "sa.Enum('one', 'two', 'three')"
        )

    def test_repr_plain_sqla_type(self):
        type_ = Integer()
        autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
            },
            'dialect': mysql.dialect()
        }

        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, autogen_context),
            "sa.Integer()"
        )

    def test_repr_user_type_user_prefix_None(self):
        from sqlalchemy.types import UserDefinedType
        class MyType(UserDefinedType):
            def get_col_spec(self):
                return "MYTYPE"

        type_ = MyType()
        autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
                'user_module_prefix': None
            },
            'dialect': mysql.dialect()
        }

        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, autogen_context),
            "sa.MyType()"
        )

    def test_repr_user_type_user_prefix_present(self):
        from sqlalchemy.types import UserDefinedType
        class MyType(UserDefinedType):
            def get_col_spec(self):
                return "MYTYPE"

        type_ = MyType()
        autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
                'user_module_prefix': 'user.',
            },
            'dialect': mysql.dialect()
        }

        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, autogen_context),
            "user.MyType()"
        )

    def test_repr_dialect_type(self):
        from sqlalchemy.dialects.mysql import VARCHAR

        type_ = VARCHAR(20, charset='utf8', national=True)
        autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
                'user_module_prefix': None,
            },
            'imports': set(),
            'dialect': mysql.dialect()
        }
        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, autogen_context),
            "mysql.VARCHAR(charset='utf8', national=True, length=20)"
        )
        eq_(autogen_context['imports'],
                set(['from sqlalchemy.dialects import mysql'])
            )
