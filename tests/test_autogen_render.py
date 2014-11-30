import re
import sys
from alembic.testing import TestBase

from sqlalchemy import MetaData, Column, Table, String, \
    Numeric, CHAR, ForeignKey, DATETIME, Integer, \
    CheckConstraint, Unicode, Enum, cast,\
    UniqueConstraint, Boolean, ForeignKeyConstraint,\
    PrimaryKeyConstraint, Index, func, text, DefaultClause

from sqlalchemy.types import TIMESTAMP
from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.engine.default import DefaultDialect
from sqlalchemy.sql import and_, column, literal_column, false

from alembic.testing.mock import patch

from alembic import autogenerate, util, compat
from alembic.testing import eq_, eq_ignore_whitespace, config


py3k = sys.version_info >= (3, )


class AutogenRenderTest(TestBase):

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
                """op.create_index('foo_idx', 't', \
['x', 'y'], unique=False, """
                """postgresql_where=sa.text(!U"t.y = 'something'"))"""
            )
        else:
            eq_ignore_whitespace(
                autogenerate.render._add_index(idx, autogen_context),
                """op.create_index('foo_idx', 't', ['x', 'y'], \
unique=False, """
                """postgresql_where=sa.text(!U't.y = %(y_1)s'))"""
            )

    @config.requirements.fail_before_sqla_080
    def test_render_add_index_func(self):
        m = MetaData()
        t = Table(
            'test', m,
            Column('id', Integer, primary_key=True),
            Column('code', String(255))
        )
        idx = Index('test_lower_code_idx', func.lower(t.c.code))
        eq_ignore_whitespace(
            autogenerate.render._add_index(idx, self.autogen_context),
            "op.create_index('test_lower_code_idx', 'test', "
            "[sa.text(!U'lower(test.code)')], unique=False)"
        )

    @config.requirements.fail_before_sqla_080
    def test_render_add_index_cast(self):
        m = MetaData()
        t = Table(
            'test', m,
            Column('id', Integer, primary_key=True),
            Column('code', String(255))
        )
        idx = Index('test_lower_code_idx', cast(t.c.code, String))
        eq_ignore_whitespace(
            autogenerate.render._add_index(idx, self.autogen_context),
            "op.create_index('test_lower_code_idx', 'test', "
            "[sa.text(!U'CAST(test.code AS CHAR)')], unique=False)"
        )

    @config.requirements.fail_before_sqla_080
    def test_render_add_index_desc(self):
        m = MetaData()
        t = Table(
            'test', m,
            Column('id', Integer, primary_key=True),
            Column('code', String(255))
        )
        idx = Index('test_desc_code_idx', t.c.code.desc())
        eq_ignore_whitespace(
            autogenerate.render._add_index(idx, self.autogen_context),
            "op.create_index('test_desc_code_idx', 'test', "
            "[sa.text(!U'test.code DESC')], unique=False)"
        )

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
            autogenerate.render._add_unique_constraint(
                uq, self.autogen_context),
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
            autogenerate.render._add_unique_constraint(
                uq, self.autogen_context),
            "op.create_unique_constraint('uq_test_code', 'test', "
            "['code'], schema='CamelSchema')"
        )

    def test_drop_unique_constraint(self):
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
            "op.drop_constraint('uq_test_code', 'test', type_='unique')"
        )

    def test_drop_unique_constraint_schema(self):
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
            "op.drop_constraint('uq_test_code', 'test', "
            "schema='CamelSchema', type_='unique')"
        )

    def test_drop_fk_constraint(self):
        m = MetaData()
        Table('a', m, Column('id', Integer, primary_key=True))
        b = Table('b', m, Column('a_id', Integer, ForeignKey('a.id')))
        fk = ForeignKeyConstraint(['a_id'], ['a.id'], name='fk_a_id')
        b.append_constraint(fk)
        eq_ignore_whitespace(
            autogenerate.render._drop_constraint(fk, self.autogen_context),
            "op.drop_constraint('fk_a_id', 'b', type_='foreignkey')"
        )

    def test_drop_fk_constraint_schema(self):
        m = MetaData()
        m = MetaData()
        Table(
            'a', m, Column('id', Integer, primary_key=True),
            schema="CamelSchemaTwo")
        b = Table(
            'b', m, Column('a_id', Integer, ForeignKey('a.id')),
            schema="CamelSchemaOne")
        fk = ForeignKeyConstraint(
            ["a_id"],
            ["CamelSchemaTwo.a.id"], name='fk_a_id')
        b.append_constraint(fk)

        eq_ignore_whitespace(
            autogenerate.render._drop_constraint(fk, self.autogen_context),
            "op.drop_constraint('fk_a_id', 'b', schema='CamelSchemaOne', "
            "type_='foreignkey')"
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
            "sa.Column('amount', sa.Numeric(precision=5, scale=2), "
            "nullable=True),"
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

    def test_render_table_w_unicode_name(self):
        m = MetaData()
        t = Table(compat.ue('\u0411\u0435\u0437'), m,
                  Column('id', Integer, primary_key=True),
                  )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table(%r,"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('id'))" % compat.ue('\u0411\u0435\u0437')
        )

    def test_render_table_w_unicode_schema(self):
        m = MetaData()
        t = Table('test', m,
                  Column('id', Integer, primary_key=True),
                  schema=compat.ue('\u0411\u0435\u0437')
                  )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('id'),"
            "schema=%r)" % compat.ue('\u0411\u0435\u0437')
        )

    @patch("alembic.autogenerate.render.MAX_PYTHON_ARGS", 3)
    def test_render_table_max_cols(self):
        m = MetaData()
        t = Table(
            'test', m,
            Column('a', Integer),
            Column('b', Integer),
            Column('c', Integer),
            Column('d', Integer),
        )
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('test',"
            "*[sa.Column('a', sa.Integer(), nullable=True),"
            "sa.Column('b', sa.Integer(), nullable=True),"
            "sa.Column('c', sa.Integer(), nullable=True),"
            "sa.Column('d', sa.Integer(), nullable=True)])"
        )

        t2 = Table(
            'test2', m,
            Column('a', Integer),
            Column('b', Integer),
            Column('c', Integer),
        )

        eq_ignore_whitespace(
            autogenerate.render._add_table(t2, self.autogen_context),
            "op.create_table('test2',"
            "sa.Column('a', sa.Integer(), nullable=True),"
            "sa.Column('b', sa.Integer(), nullable=True),"
            "sa.Column('c', sa.Integer(), nullable=True))"
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
            re.sub(
                r"u'", "'",
                autogenerate.render._add_table(t, self.autogen_context)
            ),
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
        eq_ignore_whitespace(
            autogenerate.render._drop_table(Table("sometable", MetaData()),
                                            self.autogen_context),
            "op.drop_table('sometable')"
        )

    def test_render_drop_table_w_schema(self):
        eq_ignore_whitespace(
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
            "op.create_table('test',"
            "sa.Column('x', sa.Boolean(), nullable=True))"
        )

    def test_render_empty_pk_vs_nonempty_pk(self):
        m = MetaData()
        t1 = Table('t1', m, Column('x', Integer))
        t2 = Table('t2', m, Column('x', Integer, primary_key=True))

        eq_ignore_whitespace(
            autogenerate.render._add_table(t1, self.autogen_context),
            "op.create_table('t1',"
            "sa.Column('x', sa.Integer(), nullable=True))"
        )

        eq_ignore_whitespace(
            autogenerate.render._add_table(t2, self.autogen_context),
            "op.create_table('t2',"
            "sa.Column('x', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('x'))"
        )

    def test_render_add_column(self):
        eq_ignore_whitespace(
            autogenerate.render._add_column(
                None, "foo", Column("x", Integer, server_default="5"),
                self.autogen_context),
            "op.add_column('foo', sa.Column('x', sa.Integer(), "
            "server_default='5', nullable=True))"
        )

    def test_render_add_column_w_schema(self):
        eq_ignore_whitespace(
            autogenerate.render._add_column(
                "foo", "bar", Column("x", Integer, server_default="5"),
                self.autogen_context),
            "op.add_column('bar', sa.Column('x', sa.Integer(), "
            "server_default='5', nullable=True), schema='foo')"
        )

    def test_render_drop_column(self):
        eq_ignore_whitespace(
            autogenerate.render._drop_column(
                None, "foo", Column("x", Integer, server_default="5"),
                self.autogen_context),

            "op.drop_column('foo', 'x')"
        )

    def test_render_drop_column_w_schema(self):
        eq_ignore_whitespace(
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

    def test_render_unicode_server_default(self):
        default = compat.ue(
            '\u0411\u0435\u0437 '
            '\u043d\u0430\u0437\u0432\u0430\u043d\u0438\u044f'
        )

        c = Column(
            'x', Unicode,
            server_default=text(default)
        )

        eq_ignore_whitespace(
            autogenerate.render._render_server_default(
                c.server_default, self.autogen_context
            ),
            "sa.text(%r)" % default
        )

    def test_render_col_with_server_default(self):
        c = Column('updated_at', TIMESTAMP(),
                   server_default='TIMEZONE("utc", CURRENT_TIMESTAMP)',
                   nullable=False)
        result = autogenerate.render._render_column(
            c, self.autogen_context
        )
        eq_ignore_whitespace(
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
        eq_ignore_whitespace(
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
        eq_ignore_whitespace(
            result,
            "sa.create_table('t',"
            "col(x),"
            "render:primary_key)"
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

        # SQLA 0.9 generates a u'' here for remote cols while 0.8 does not,
        # so just whack out "'u" here from the generated

        eq_ignore_whitespace(
            re.sub(
                r"u'", "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context)),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], onupdate='CASCADE')"
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], ondelete="CASCADE")
        if not util.sqla_08:
            t1.append_constraint(fk)

        eq_ignore_whitespace(
            re.sub(
                r"u'", "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context)),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], ondelete='CASCADE')"
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], deferrable=True)
        if not util.sqla_08:
            t1.append_constraint(fk)
        eq_ignore_whitespace(
            re.sub(
                r"u'", "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context),
            ),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], deferrable=True)"
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], initially="XYZ")
        if not util.sqla_08:
            t1.append_constraint(fk)
        eq_ignore_whitespace(
            re.sub(
                r"u'", "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context)
            ),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], initially='XYZ')"
        )

    def test_render_fk_constraint_use_alter(self):
        m = MetaData()
        Table('t', m, Column('c', Integer))
        t2 = Table(
            't2', m,
            Column(
                'c_rem', Integer,
                ForeignKey('t.c', name="fk1", use_alter=True)))
        const = list(t2.foreign_keys)[0].constraint

        eq_ignore_whitespace(
            autogenerate.render._render_constraint(
                const, self.autogen_context),
            "sa.ForeignKeyConstraint(['c_rem'], ['t.c'], "
            "name='fk1', use_alter=True)"
        )

    def test_render_fk_constraint_w_metadata_schema(self):
        m = MetaData(schema="foo")
        t1 = Table('t', m, Column('c', Integer))
        t2 = Table('t2', m, Column('c_rem', Integer))

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], onupdate="CASCADE")
        if not util.sqla_08:
            t1.append_constraint(fk)

        eq_ignore_whitespace(
            re.sub(
                r"u'", "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context)
            ),
            "sa.ForeignKeyConstraint(['c'], ['foo.t2.c_rem'], "
            "onupdate='CASCADE')"
        )

    def test_render_check_constraint_literal(self):
        eq_ignore_whitespace(
            autogenerate.render._render_check_constraint(
                CheckConstraint("im a constraint", name='cc1'),
                self.autogen_context
            ),
            "sa.CheckConstraint(!U'im a constraint', name='cc1')"
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
            "sa.CheckConstraint(!U'c > 5 AND c < 10')"
        )

    @config.requirements.fail_before_sqla_080
    def test_render_check_constraint_literal_binds(self):
        c = column('c')
        eq_ignore_whitespace(
            autogenerate.render._render_check_constraint(
                CheckConstraint(and_(c > 5, c < 10)),
                self.autogen_context
            ),
            "sa.CheckConstraint(!U'c > 5 AND c < 10')"
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

    def test_add_unique_constraint_unicode_schema(self):
        m = MetaData()
        t = Table(
            't', m, Column('c', Integer),
            schema=compat.ue('\u0411\u0435\u0437')
        )
        eq_ignore_whitespace(
            autogenerate.render._add_unique_constraint(
                UniqueConstraint(t.c.c),
                self.autogen_context
            ),
            "op.create_unique_constraint(None, 't', ['c'], "
            "schema=%r)" % compat.ue('\u0411\u0435\u0437')
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
            "tests.test_autogen_render.MyType()"
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

    @config.requirements.sqlalchemy_09
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

    def test_render_server_default_text(self):
        c = Column(
            'updated_at', TIMESTAMP(),
            server_default=text('now()'),
            nullable=False)
        result = autogenerate.render._render_column(
            c, self.autogen_context
        )
        eq_ignore_whitespace(
            result,
            'sa.Column(\'updated_at\', sa.TIMESTAMP(), '
            'server_default=sa.text(!U\'now()\'), '
            'nullable=False)'
        )

    def test_render_server_default_native_boolean(self):
        autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
            },
            'dialect': postgresql.dialect()
        }
        c = Column(
            'updated_at', Boolean(),
            server_default=false(),
            nullable=False)
        result = autogenerate.render._render_column(
            c, autogen_context,
        )
        eq_ignore_whitespace(
            result,
            'sa.Column(\'updated_at\', sa.Boolean(), '
            'server_default=sa.text(!U\'false\'), '
            'nullable=False)'
        )

    @config.requirements.fail_before_sqla_09
    def test_render_server_default_non_native_boolean(self):
        c = Column(
            'updated_at', Boolean(),
            server_default=false(),
            nullable=False)
        dialect = DefaultDialect()
        autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
            },
            'dialect': dialect
        }

        result = autogenerate.render._render_column(
            c, autogen_context
        )
        eq_ignore_whitespace(
            result,
            'sa.Column(\'updated_at\', sa.Boolean(), '
            'server_default=sa.text(!U\'0\'), '
            'nullable=False)'
        )

    def test_render_server_default_func(self):
        c = Column(
            'updated_at', TIMESTAMP(),
            server_default=func.now(),
            nullable=False)
        result = autogenerate.render._render_column(
            c, self.autogen_context
        )
        eq_ignore_whitespace(
            result,
            'sa.Column(\'updated_at\', sa.TIMESTAMP(), '
            'server_default=sa.text(!U\'now()\'), '
            'nullable=False)'
        )

    def test_render_server_default_int(self):
        c = Column(
            'value', Integer,
            server_default="0")
        result = autogenerate.render._render_column(
            c, self.autogen_context
        )
        eq_(
            result,
            "sa.Column('value', sa.Integer(), "
            "server_default='0', nullable=True)"
        )

    def test_render_modify_reflected_int_server_default(self):
        eq_ignore_whitespace(
            autogenerate.render._modify_col(
                "sometable", "somecolumn",
                self.autogen_context,
                existing_type=Integer(),
                existing_server_default=DefaultClause(text("5")),
                nullable=True),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True, "
            "existing_server_default=sa.text(!U'5'))"
        )


class RenderNamingConventionTest(TestBase):
    __requires__ = ('sqlalchemy_094',)

    @classmethod
    def setup_class(cls):
        cls.autogen_context = {
            'opts': {
                'sqlalchemy_module_prefix': 'sa.',
                'alembic_module_prefix': 'op.',
            },
            'dialect': postgresql.dialect()
        }

    def setUp(self):

        convention = {
            "ix": 'ix_%(custom)s_%(column_0_label)s',
            "uq": "uq_%(custom)s_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(custom)s_%(table_name)s",
            "fk": "fk_%(custom)s_%(table_name)s_"
            "%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(custom)s_%(table_name)s",
            "custom": lambda const, table: "ct"
        }

        self.metadata = MetaData(
            naming_convention=convention
        )

    def test_schema_type_boolean(self):
        t = Table('t', self.metadata, Column('c', Boolean(name='xyz')))
        eq_ignore_whitespace(
            autogenerate.render._add_column(
                None, "t", t.c.c,
                self.autogen_context),
            "op.add_column('t', "
            "sa.Column('c', sa.Boolean(name='xyz'), nullable=True))"
        )

    def test_explicit_unique_constraint(self):
        t = Table('t', self.metadata, Column('c', Integer))
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(
                UniqueConstraint(t.c.c, deferrable='XYZ'),
                self.autogen_context
            ),
            "sa.UniqueConstraint('c', deferrable='XYZ', "
            "name=op.f('uq_ct_t_c'))"
        )

    def test_explicit_named_unique_constraint(self):
        t = Table('t', self.metadata, Column('c', Integer))
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(
                UniqueConstraint(t.c.c, name='q'),
                self.autogen_context
            ),
            "sa.UniqueConstraint('c', name='q')"
        )

    def test_render_add_index(self):
        t = Table('test', self.metadata,
                  Column('id', Integer, primary_key=True),
                  Column('active', Boolean()),
                  Column('code', String(255)),
                  )
        idx = Index(None, t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._add_index(idx, self.autogen_context),
            "op.create_index(op.f('ix_ct_test_active'), 'test', "
            "['active', 'code'], unique=False)"
        )

    def test_render_drop_index(self):
        t = Table('test', self.metadata,
                  Column('id', Integer, primary_key=True),
                  Column('active', Boolean()),
                  Column('code', String(255)),
                  )
        idx = Index(None, t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._drop_index(idx, self.autogen_context),
            "op.drop_index(op.f('ix_ct_test_active'), table_name='test')"
        )

    def test_render_add_index_schema(self):
        t = Table('test', self.metadata,
                  Column('id', Integer, primary_key=True),
                  Column('active', Boolean()),
                  Column('code', String(255)),
                  schema='CamelSchema'
                  )
        idx = Index(None, t.c.active, t.c.code)
        eq_ignore_whitespace(
            autogenerate.render._add_index(idx, self.autogen_context),
            "op.create_index(op.f('ix_ct_CamelSchema_test_active'), 'test', "
            "['active', 'code'], unique=False, schema='CamelSchema')"
        )

    def test_implicit_unique_constraint(self):
        t = Table('t', self.metadata, Column('c', Integer, unique=True))
        uq = [c for c in t.constraints if isinstance(c, UniqueConstraint)][0]
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(uq,
                                                          self.autogen_context
                                                          ),
            "sa.UniqueConstraint('c', name=op.f('uq_ct_t_c'))"
        )

    def test_inline_pk_constraint(self):
        t = Table('t', self.metadata, Column('c', Integer, primary_key=True))
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('t',sa.Column('c', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('c', name=op.f('pk_ct_t')))"
        )

    def test_inline_ck_constraint(self):
        t = Table(
            't', self.metadata, Column('c', Integer), CheckConstraint("c > 5"))
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('t',sa.Column('c', sa.Integer(), nullable=True),"
            "sa.CheckConstraint(!U'c > 5', name=op.f('ck_ct_t')))"
        )

    def test_inline_fk(self):
        t = Table('t', self.metadata, Column('c', Integer, ForeignKey('q.id')))
        eq_ignore_whitespace(
            autogenerate.render._add_table(t, self.autogen_context),
            "op.create_table('t',sa.Column('c', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['c'], ['q.id'], "
            "name=op.f('fk_ct_t_c_q')))"
        )

    def test_render_check_constraint_renamed(self):
        """test that constraints from autogenerate render with
        the naming convention name explicitly.  These names should
        be frozen into the migration scripts so that they remain
        the same if the application's naming convention changes.

        However, op.create_table() and others need to be careful that
        these don't double up when the "%(constraint_name)s" token is
        used.

        """
        m1 = MetaData(naming_convention={
            "ck": "ck_%(table_name)s_%(constraint_name)s"})
        ck = CheckConstraint("im a constraint", name="cc1")
        Table('t', m1, Column('x'), ck)

        eq_ignore_whitespace(
            autogenerate.render._render_check_constraint(
                ck,
                self.autogen_context
            ),
            "sa.CheckConstraint(!U'im a constraint', name=op.f('ck_t_cc1'))"
        )

