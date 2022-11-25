import re

import sqlalchemy as sa  # noqa
from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import cast
from sqlalchemy import CHAR
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DATETIME
from sqlalchemy import DateTime
from sqlalchemy import DefaultClause
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import func
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Numeric
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import text
from sqlalchemy import types
from sqlalchemy import Unicode
from sqlalchemy import UniqueConstraint
from sqlalchemy.engine.default import DefaultDialect
from sqlalchemy.sql import and_
from sqlalchemy.sql import column
from sqlalchemy.sql import false
from sqlalchemy.sql import literal_column
from sqlalchemy.sql import table
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.types import UserDefinedType

from alembic import autogenerate
from alembic import op  # noqa
from alembic import testing
from alembic.autogenerate import api
from alembic.migration import MigrationContext
from alembic.operations import ops
from alembic.testing import assert_raises
from alembic.testing import assertions
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import eq_ignore_whitespace
from alembic.testing import mock
from alembic.testing import TestBase
from alembic.testing.fixtures import op_fixture


class AutogenRenderTest(TestBase):

    """test individual directives"""

    def setUp(self):
        ctx_opts = {
            "sqlalchemy_module_prefix": "sa.",
            "alembic_module_prefix": "op.",
            "target_metadata": MetaData(),
        }
        context = MigrationContext.configure(
            dialect=DefaultDialect(), opts=ctx_opts
        )

        self.autogen_context = api.AutogenContext(context)

    def test_render_add_index(self):
        """
        autogenerate.render._add_index
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
        )
        idx = Index("test_active_code_idx", t.c.active, t.c.code)
        op_obj = ops.CreateIndexOp.from_index(idx)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_index('test_active_code_idx', 'test', "
            "['active', 'code'], unique=False)",
        )

    @testing.emits_warning("Can't validate argument ")
    def test_render_add_index_custom_kwarg(self):
        t = Table(
            "test",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
        )
        idx = Index(None, t.c.active, t.c.code, somedialect_foobar="option")
        op_obj = ops.CreateIndexOp.from_index(idx)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_index(op.f('ix_test_active'), 'test', "
            "['active', 'code'], unique=False, somedialect_foobar='option')",
        )

    def test_render_add_index_batch(self):
        """
        autogenerate.render._add_index
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
        )
        idx = Index("test_active_code_idx", t.c.active, t.c.code)
        op_obj = ops.CreateIndexOp.from_index(idx)
        with self.autogen_context._within_batch():
            eq_ignore_whitespace(
                autogenerate.render_op_text(self.autogen_context, op_obj),
                "batch_op.create_index('test_active_code_idx', "
                "['active', 'code'], unique=False)",
            )

    def test_render_add_index_schema(self):
        """
        autogenerate.render._add_index using schema
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
            schema="CamelSchema",
        )
        idx = Index("test_active_code_idx", t.c.active, t.c.code)
        op_obj = ops.CreateIndexOp.from_index(idx)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_index('test_active_code_idx', 'test', "
            "['active', 'code'], unique=False, schema='CamelSchema')",
        )

    def test_render_add_index_schema_batch(self):
        """
        autogenerate.render._add_index using schema
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
            schema="CamelSchema",
        )
        idx = Index("test_active_code_idx", t.c.active, t.c.code)
        op_obj = ops.CreateIndexOp.from_index(idx)
        with self.autogen_context._within_batch():
            eq_ignore_whitespace(
                autogenerate.render_op_text(self.autogen_context, op_obj),
                "batch_op.create_index('test_active_code_idx', "
                "['active', 'code'], unique=False)",
            )

    def test_render_add_index_func(self):
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("code", String(255)),
        )
        idx = Index("test_lower_code_idx", func.lower(t.c.code))
        op_obj = ops.CreateIndexOp.from_index(idx)

        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_index('test_lower_code_idx', 'test', "
            "[sa.text('lower(code)')], unique=False)",
        )

    def test_render_add_index_cast(self):
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("code", String(255)),
        )
        idx = Index("test_lower_code_idx", cast(t.c.code, String))
        op_obj = ops.CreateIndexOp.from_index(idx)

        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_index('test_lower_code_idx', 'test', "
            "[sa.text('CAST(code AS VARCHAR)')], unique=False)",
        )

    def test_render_add_index_desc(self):
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("code", String(255)),
        )
        idx = Index("test_desc_code_idx", t.c.code.desc())
        op_obj = ops.CreateIndexOp.from_index(idx)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_index('test_desc_code_idx', 'test', "
            "[sa.text('code DESC')], unique=False)",
        )

    def test_drop_index(self):
        """
        autogenerate.render._drop_index
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
        )
        idx = Index("test_active_code_idx", t.c.active, t.c.code)
        op_obj = ops.DropIndexOp.from_index(idx)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_index('test_active_code_idx', table_name='test')",
        )

    @testing.emits_warning("Can't validate argument ")
    def test_render_drop_index_custom_kwarg(self):
        t = Table(
            "test",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
        )
        idx = Index(None, t.c.active, t.c.code, somedialect_foobar="option")
        op_obj = ops.DropIndexOp.from_index(idx)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_index(op.f('ix_test_active'), table_name='test', "
            "somedialect_foobar='option')",
        )

    def test_drop_index_batch(self):
        """
        autogenerate.render._drop_index
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
        )
        idx = Index("test_active_code_idx", t.c.active, t.c.code)
        op_obj = ops.DropIndexOp.from_index(idx)
        with self.autogen_context._within_batch():
            eq_ignore_whitespace(
                autogenerate.render_op_text(self.autogen_context, op_obj),
                "batch_op.drop_index('test_active_code_idx')",
            )

    def test_drop_index_schema(self):
        """
        autogenerate.render._drop_index using schema
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
            schema="CamelSchema",
        )
        idx = Index("test_active_code_idx", t.c.active, t.c.code)
        op_obj = ops.DropIndexOp.from_index(idx)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_index('test_active_code_idx', "
            + "table_name='test', schema='CamelSchema')",
        )

    def test_drop_index_schema_batch(self):
        """
        autogenerate.render._drop_index using schema
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
            schema="CamelSchema",
        )
        idx = Index("test_active_code_idx", t.c.active, t.c.code)
        op_obj = ops.DropIndexOp.from_index(idx)
        with self.autogen_context._within_batch():
            eq_ignore_whitespace(
                autogenerate.render_op_text(self.autogen_context, op_obj),
                "batch_op.drop_index('test_active_code_idx')",
            )

    def test_add_unique_constraint(self):
        """
        autogenerate.render._add_unique_constraint
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
        )
        uq = UniqueConstraint(t.c.code, name="uq_test_code")
        op_obj = ops.AddConstraintOp.from_constraint(uq)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_unique_constraint('uq_test_code', 'test', ['code'])",
        )

    def test_add_unique_constraint_batch(self):
        """
        autogenerate.render._add_unique_constraint
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
        )
        uq = UniqueConstraint(t.c.code, name="uq_test_code")
        op_obj = ops.AddConstraintOp.from_constraint(uq)
        with self.autogen_context._within_batch():
            eq_ignore_whitespace(
                autogenerate.render_op_text(self.autogen_context, op_obj),
                "batch_op.create_unique_constraint('uq_test_code', ['code'])",
            )

    def test_add_unique_constraint_schema(self):
        """
        autogenerate.render._add_unique_constraint using schema
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
            schema="CamelSchema",
        )
        uq = UniqueConstraint(t.c.code, name="uq_test_code")
        op_obj = ops.AddConstraintOp.from_constraint(uq)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_unique_constraint('uq_test_code', 'test', "
            "['code'], schema='CamelSchema')",
        )

    def test_add_unique_constraint_schema_batch(self):
        """
        autogenerate.render._add_unique_constraint using schema
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
            schema="CamelSchema",
        )
        uq = UniqueConstraint(t.c.code, name="uq_test_code")
        op_obj = ops.AddConstraintOp.from_constraint(uq)
        with self.autogen_context._within_batch():
            eq_ignore_whitespace(
                autogenerate.render_op_text(self.autogen_context, op_obj),
                "batch_op.create_unique_constraint('uq_test_code', "
                "['code'])",
            )

    def test_drop_unique_constraint(self):
        """
        autogenerate.render._drop_constraint
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
        )
        uq = UniqueConstraint(t.c.code, name="uq_test_code")
        op_obj = ops.DropConstraintOp.from_constraint(uq)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_constraint('uq_test_code', 'test', type_='unique')",
        )

    def test_drop_unique_constraint_schema(self):
        """
        autogenerate.render._drop_constraint using schema
        """
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
            schema="CamelSchema",
        )
        uq = UniqueConstraint(t.c.code, name="uq_test_code")
        op_obj = ops.DropConstraintOp.from_constraint(uq)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_constraint('uq_test_code', 'test', "
            "schema='CamelSchema', type_='unique')",
        )

    def test_drop_unique_constraint_schema_reprobj(self):
        """
        autogenerate.render._drop_constraint using schema
        """

        class SomeObj(str):
            def __repr__(self):
                return "foo.camel_schema"

        op_obj = ops.DropConstraintOp(
            "uq_test_code",
            "test",
            type_="unique",
            schema=SomeObj("CamelSchema"),
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_constraint('uq_test_code', 'test', "
            "schema=foo.camel_schema, type_='unique')",
        )

    def test_add_fk_constraint(self):
        m = MetaData()
        Table("a", m, Column("id", Integer, primary_key=True))
        b = Table("b", m, Column("a_id", Integer, ForeignKey("a.id")))
        fk = ForeignKeyConstraint(["a_id"], ["a.id"], name="fk_a_id")
        b.append_constraint(fk)
        op_obj = ops.AddConstraintOp.from_constraint(fk)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_foreign_key('fk_a_id', 'b', 'a', ['a_id'], ['id'])",
        )

    def test_add_fk_constraint_batch(self):
        m = MetaData()
        Table("a", m, Column("id", Integer, primary_key=True))
        b = Table("b", m, Column("a_id", Integer, ForeignKey("a.id")))
        fk = ForeignKeyConstraint(["a_id"], ["a.id"], name="fk_a_id")
        b.append_constraint(fk)
        op_obj = ops.AddConstraintOp.from_constraint(fk)
        with self.autogen_context._within_batch():
            eq_ignore_whitespace(
                autogenerate.render_op_text(self.autogen_context, op_obj),
                "batch_op.create_foreign_key"
                "('fk_a_id', 'a', ['a_id'], ['id'])",
            )

    def test_add_fk_constraint_kwarg(self):
        m = MetaData()
        t1 = Table("t", m, Column("c", Integer))
        t2 = Table("t2", m, Column("c_rem", Integer))

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], onupdate="CASCADE")

        # SQLA 0.9 generates a u'' here for remote cols while 0.8 does not,
        # so just whack out "'u" here from the generated

        op_obj = ops.AddConstraintOp.from_constraint(fk)
        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render_op_text(self.autogen_context, op_obj),
            ),
            "op.create_foreign_key(None, 't', 't2', ['c'], ['c_rem'], "
            "onupdate='CASCADE')",
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], ondelete="CASCADE")

        op_obj = ops.AddConstraintOp.from_constraint(fk)
        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render_op_text(self.autogen_context, op_obj),
            ),
            "op.create_foreign_key(None, 't', 't2', ['c'], ['c_rem'], "
            "ondelete='CASCADE')",
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], deferrable=True)
        op_obj = ops.AddConstraintOp.from_constraint(fk)
        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render_op_text(self.autogen_context, op_obj),
            ),
            "op.create_foreign_key(None, 't', 't2', ['c'], ['c_rem'], "
            "deferrable=True)",
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], initially="XYZ")
        op_obj = ops.AddConstraintOp.from_constraint(fk)
        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render_op_text(self.autogen_context, op_obj),
            ),
            "op.create_foreign_key(None, 't', 't2', ['c'], ['c_rem'], "
            "initially='XYZ')",
        )

        fk = ForeignKeyConstraint(
            [t1.c.c],
            [t2.c.c_rem],
            initially="XYZ",
            ondelete="CASCADE",
            deferrable=True,
        )
        op_obj = ops.AddConstraintOp.from_constraint(fk)
        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render_op_text(self.autogen_context, op_obj),
            ),
            "op.create_foreign_key(None, 't', 't2', ['c'], ['c_rem'], "
            "ondelete='CASCADE', initially='XYZ', deferrable=True)",
        )

    def test_add_fk_constraint_inline_colkeys(self):
        m = MetaData()
        Table("a", m, Column("id", Integer, key="aid", primary_key=True))
        b = Table(
            "b", m, Column("a_id", Integer, ForeignKey("a.aid"), key="baid")
        )

        op_obj = ops.CreateTableOp.from_table(b)
        py_code = autogenerate.render_op_text(self.autogen_context, op_obj)

        eq_ignore_whitespace(
            py_code,
            "op.create_table('b',"
            "sa.Column('a_id', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['a_id'], ['a.id'], ))",
        )

        context = op_fixture()
        eval(py_code)
        context.assert_(
            "CREATE TABLE b (a_id INTEGER, "
            "FOREIGN KEY(a_id) REFERENCES a (id))"
        )

    def test_add_fk_constraint_separate_colkeys(self):
        m = MetaData()
        Table("a", m, Column("id", Integer, key="aid", primary_key=True))
        b = Table("b", m, Column("a_id", Integer, key="baid"))
        fk = ForeignKeyConstraint(["baid"], ["a.aid"], name="fk_a_id")
        b.append_constraint(fk)

        op_obj = ops.CreateTableOp.from_table(b)
        py_code = autogenerate.render_op_text(self.autogen_context, op_obj)

        eq_ignore_whitespace(
            py_code,
            "op.create_table('b',"
            "sa.Column('a_id', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['a_id'], ['a.id'], name='fk_a_id'))",
        )

        context = op_fixture()
        eval(py_code)
        context.assert_(
            "CREATE TABLE b (a_id INTEGER, CONSTRAINT "
            "fk_a_id FOREIGN KEY(a_id) REFERENCES a (id))"
        )

        context = op_fixture()

        op_obj = ops.AddConstraintOp.from_constraint(fk)

        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_foreign_key('fk_a_id', 'b', 'a', ['a_id'], ['id'])",
        )

        py_code = autogenerate.render_op_text(self.autogen_context, op_obj)

        eval(py_code)
        context.assert_(
            "ALTER TABLE b ADD CONSTRAINT fk_a_id "
            "FOREIGN KEY(a_id) REFERENCES a (id)"
        )

    def test_add_fk_constraint_schema(self):
        m = MetaData()
        Table(
            "a",
            m,
            Column("id", Integer, primary_key=True),
            schema="CamelSchemaTwo",
        )
        b = Table(
            "b",
            m,
            Column("a_id", Integer, ForeignKey("a.id")),
            schema="CamelSchemaOne",
        )
        fk = ForeignKeyConstraint(
            ["a_id"], ["CamelSchemaTwo.a.id"], name="fk_a_id"
        )
        b.append_constraint(fk)
        op_obj = ops.AddConstraintOp.from_constraint(fk)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_foreign_key('fk_a_id', 'b', 'a', ['a_id'], ['id'],"
            " source_schema='CamelSchemaOne', "
            "referent_schema='CamelSchemaTwo')",
        )

    def test_add_fk_constraint_schema_batch(self):
        m = MetaData()
        Table(
            "a",
            m,
            Column("id", Integer, primary_key=True),
            schema="CamelSchemaTwo",
        )
        b = Table(
            "b",
            m,
            Column("a_id", Integer, ForeignKey("a.id")),
            schema="CamelSchemaOne",
        )
        fk = ForeignKeyConstraint(
            ["a_id"], ["CamelSchemaTwo.a.id"], name="fk_a_id"
        )
        b.append_constraint(fk)
        op_obj = ops.AddConstraintOp.from_constraint(fk)
        with self.autogen_context._within_batch():
            eq_ignore_whitespace(
                autogenerate.render_op_text(self.autogen_context, op_obj),
                "batch_op.create_foreign_key('fk_a_id', 'a', ['a_id'], ['id'],"
                " referent_schema='CamelSchemaTwo')",
            )

    def test_drop_fk_constraint(self):
        m = MetaData()
        Table("a", m, Column("id", Integer, primary_key=True))
        b = Table("b", m, Column("a_id", Integer, ForeignKey("a.id")))
        fk = ForeignKeyConstraint(["a_id"], ["a.id"], name="fk_a_id")
        b.append_constraint(fk)
        op_obj = ops.DropConstraintOp.from_constraint(fk)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_constraint('fk_a_id', 'b', type_='foreignkey')",
        )

    def test_drop_fk_constraint_batch(self):
        m = MetaData()
        Table("a", m, Column("id", Integer, primary_key=True))
        b = Table("b", m, Column("a_id", Integer, ForeignKey("a.id")))
        fk = ForeignKeyConstraint(["a_id"], ["a.id"], name="fk_a_id")
        b.append_constraint(fk)
        op_obj = ops.DropConstraintOp.from_constraint(fk)
        with self.autogen_context._within_batch():
            eq_ignore_whitespace(
                autogenerate.render_op_text(self.autogen_context, op_obj),
                "batch_op.drop_constraint('fk_a_id', type_='foreignkey')",
            )

    def test_drop_fk_constraint_schema(self):
        m = MetaData()
        Table(
            "a",
            m,
            Column("id", Integer, primary_key=True),
            schema="CamelSchemaTwo",
        )
        b = Table(
            "b",
            m,
            Column("a_id", Integer, ForeignKey("a.id")),
            schema="CamelSchemaOne",
        )
        fk = ForeignKeyConstraint(
            ["a_id"], ["CamelSchemaTwo.a.id"], name="fk_a_id"
        )
        b.append_constraint(fk)
        op_obj = ops.DropConstraintOp.from_constraint(fk)

        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_constraint('fk_a_id', 'b', schema='CamelSchemaOne', "
            "type_='foreignkey')",
        )

    def test_drop_fk_constraint_batch_schema(self):
        m = MetaData()
        Table(
            "a",
            m,
            Column("id", Integer, primary_key=True),
            schema="CamelSchemaTwo",
        )
        b = Table(
            "b",
            m,
            Column("a_id", Integer, ForeignKey("a.id")),
            schema="CamelSchemaOne",
        )
        fk = ForeignKeyConstraint(
            ["a_id"], ["CamelSchemaTwo.a.id"], name="fk_a_id"
        )
        b.append_constraint(fk)
        op_obj = ops.DropConstraintOp.from_constraint(fk)

        with self.autogen_context._within_batch():
            eq_ignore_whitespace(
                autogenerate.render_op_text(self.autogen_context, op_obj),
                "batch_op.drop_constraint('fk_a_id', type_='foreignkey')",
            )

    def test_render_table_upgrade(self):
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("name", Unicode(255)),
            Column("address_id", Integer, ForeignKey("address.id")),
            Column("timestamp", DATETIME, server_default="NOW()"),
            Column("amount", Numeric(5, 2)),
            UniqueConstraint("name", name="uq_name"),
            UniqueConstraint("timestamp"),
        )

        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
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
            ")",
        )

    def test_render_table_w_schema(self):
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("q", Integer, ForeignKey("address.id")),
            schema="foo",
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "schema='foo'"
            ")",
        )

    def test_render_table_w_system(self):
        m = MetaData()
        t = Table(
            "sometable",
            m,
            Column("id", Integer, primary_key=True),
            Column("xmin", Integer, system=True, nullable=False),
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('sometable',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('xmin', sa.Integer(), nullable=False, system=True),"
            "sa.PrimaryKeyConstraint('id'))",
        )

    def test_render_table_w_unicode_name(self):
        m = MetaData()
        t = Table(
            "\u0411\u0435\u0437",
            m,
            Column("id", Integer, primary_key=True),
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table(%r,"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('id'))" % "\u0411\u0435\u0437",
        )

    def test_render_table_w_unicode_schema(self):
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            schema="\u0411\u0435\u0437",
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('id'),"
            "schema=%r)" % "\u0411\u0435\u0437",
        )

    def test_render_table_w_unsupported_constraint(self):
        from sqlalchemy.sql.schema import ColumnCollectionConstraint

        class SomeCustomConstraint(ColumnCollectionConstraint):
            __visit_name__ = "some_custom"

        m = MetaData()

        t = Table("t", m, Column("id", Integer), SomeCustomConstraint("id"))
        op_obj = ops.CreateTableOp.from_table(t)
        with assertions.expect_warnings(
            "No renderer is established for object SomeCustomConstraint"
        ):
            eq_ignore_whitespace(
                autogenerate.render_op_text(self.autogen_context, op_obj),
                "op.create_table('t',"
                "sa.Column('id', sa.Integer(), nullable=True),"
                "[Unknown Python object "
                "SomeCustomConstraint(Column('id', Integer(), table=<t>))])",
            )

    @mock.patch("alembic.autogenerate.render.MAX_PYTHON_ARGS", 3)
    def test_render_table_max_cols(self):
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("a", Integer),
            Column("b", Integer),
            Column("c", Integer),
            Column("d", Integer),
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('test',"
            "*[sa.Column('a', sa.Integer(), nullable=True),"
            "sa.Column('b', sa.Integer(), nullable=True),"
            "sa.Column('c', sa.Integer(), nullable=True),"
            "sa.Column('d', sa.Integer(), nullable=True)])",
        )

        t2 = Table(
            "test2",
            m,
            Column("a", Integer),
            Column("b", Integer),
            Column("c", Integer),
        )
        op_obj = ops.CreateTableOp.from_table(t2)

        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('test2',"
            "sa.Column('a', sa.Integer(), nullable=True),"
            "sa.Column('b', sa.Integer(), nullable=True),"
            "sa.Column('c', sa.Integer(), nullable=True))",
        )

    def test_render_table_w_fk_schema(self):
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("q", Integer, ForeignKey("foo.address.id")),
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['foo.address.id'], ),"
            "sa.PrimaryKeyConstraint('id')"
            ")",
        )

    def test_render_table_w_metadata_schema(self):
        m = MetaData(schema="foo")
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("q", Integer, ForeignKey("address.id")),
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render_op_text(self.autogen_context, op_obj),
            ),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['foo.address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "schema='foo'"
            ")",
        )

    def test_render_table_w_metadata_schema_override(self):
        m = MetaData(schema="foo")
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("q", Integer, ForeignKey("bar.address.id")),
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['bar.address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "schema='foo'"
            ")",
        )

    def test_render_table_w_prefixes(self):
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            prefixes=["TEST", "PREFIXES"],
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('id'),"
            "prefixes=['TEST', 'PREFIXES']"
            ")",
        )

    def test_render_table_w_prefixes_schema(self):
        m = MetaData(schema="foo")
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            prefixes=["TEST", "PREFIXES"],
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('id'),"
            "schema='foo',"
            "prefixes=['TEST', 'PREFIXES']"
            ")",
        )

    def test_render_addtl_args(self):
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("q", Integer, ForeignKey("bar.address.id")),
            sqlite_autoincrement=True,
            mysql_engine="InnoDB",
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['bar.address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "mysql_engine='InnoDB',sqlite_autoincrement=True)",
        )

    def test_render_drop_table(self):
        op_obj = ops.DropTableOp.from_table(Table("sometable", MetaData()))
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_table('sometable')",
        )

    def test_render_drop_table_w_schema(self):
        op_obj = ops.DropTableOp.from_table(
            Table("sometable", MetaData(), schema="foo")
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_table('sometable', schema='foo')",
        )

    def test_render_table_no_implicit_check(self):
        m = MetaData()
        t = Table("test", m, Column("x", Boolean()))

        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('test',"
            "sa.Column('x', sa.Boolean(), nullable=True))",
        )

    def test_render_pk_with_col_name_vs_col_key(self):
        m = MetaData()
        t1 = Table("t1", m, Column("x", Integer, key="y", primary_key=True))

        op_obj = ops.CreateTableOp.from_table(t1)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('t1',"
            "sa.Column('x', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('x'))",
        )

    def test_render_empty_pk_vs_nonempty_pk(self):
        m = MetaData()
        t1 = Table("t1", m, Column("x", Integer))
        t2 = Table("t2", m, Column("x", Integer, primary_key=True))

        op_obj = ops.CreateTableOp.from_table(t1)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('t1',"
            "sa.Column('x', sa.Integer(), nullable=True))",
        )

        op_obj = ops.CreateTableOp.from_table(t2)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('t2',"
            "sa.Column('x', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('x'))",
        )

    def test_render_table_w_autoincrement(self):
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True, autoincrement=True),
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('test',"
            "sa.Column('id1', sa.Integer(), nullable=False),"
            "sa.Column('id2', sa.Integer(), autoincrement=True, "
            "nullable=False),"
            "sa.PrimaryKeyConstraint('id1', 'id2')"
            ")",
        )

    def test_render_add_column(self):
        op_obj = ops.AddColumnOp(
            "foo", Column("x", Integer, server_default="5")
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.add_column('foo', sa.Column('x', sa.Integer(), "
            "server_default='5', nullable=True))",
        )

    @config.requirements.sqlalchemy_13
    @testing.emits_warning("Can't validate argument ")
    def test_render_add_column_custom_kwarg(self):
        col = Column(
            "x", Integer, server_default="5", somedialect_foobar="option"
        )
        Table("foo", MetaData(), col)

        op_obj = ops.AddColumnOp.from_column(col)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.add_column('foo', sa.Column('x', sa.Integer(), "
            "server_default='5', nullable=True, somedialect_foobar='option'))",
        )

    def test_render_add_column_system(self):
        # this would never actually happen since "system" columns
        # can't be added in any case.   Howver it will render as
        # part of op.CreateTableOp.
        op_obj = ops.AddColumnOp("foo", Column("xmin", Integer, system=True))
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.add_column('foo', sa.Column('xmin', sa.Integer(), "
            "nullable=True, system=True))",
        )

    def test_render_add_column_w_schema(self):
        op_obj = ops.AddColumnOp(
            "bar", Column("x", Integer, server_default="5"), schema="foo"
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.add_column('bar', sa.Column('x', sa.Integer(), "
            "server_default='5', nullable=True), schema='foo')",
        )

    def test_render_drop_column(self):
        op_obj = ops.DropColumnOp.from_column_and_tablename(
            None, "foo", Column("x", Integer, server_default="5")
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_column('foo', 'x')",
        )

    def test_render_drop_column_w_schema(self):
        op_obj = ops.DropColumnOp.from_column_and_tablename(
            "foo", "bar", Column("x", Integer, server_default="5")
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_column('bar', 'x', schema='foo')",
        )

    def test_render_quoted_server_default(self):
        eq_(
            autogenerate.render._render_server_default(
                "nextval('group_to_perm_group_to_perm_id_seq'::regclass)",
                self.autogen_context,
            ),
            "\"nextval('group_to_perm_group_to_perm_id_seq'::regclass)\"",
        )

    def test_render_unicode_server_default(self):
        default = (
            "\u0411\u0435\u0437 "
            "\u043d\u0430\u0437\u0432\u0430\u043d\u0438\u044f"
        )

        c = Column("x", Unicode, server_default=text(default))

        eq_ignore_whitespace(
            autogenerate.render._render_server_default(
                c.server_default, self.autogen_context
            ),
            "sa.text(%r)" % default,
        )

    def test_render_col_with_server_default(self):
        c = Column(
            "updated_at",
            TIMESTAMP(),
            server_default='TIMEZONE("utc", CURRENT_TIMESTAMP)',
            nullable=False,
        )
        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_ignore_whitespace(
            result,
            "sa.Column('updated_at', sa.TIMESTAMP(), "
            "server_default='TIMEZONE(\"utc\", CURRENT_TIMESTAMP)', "
            "nullable=False)",
        )

    def test_render_col_with_comment(self):
        c = Column("some_key", Integer, comment="This is a comment")
        Table("some_table", MetaData(), c)
        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_ignore_whitespace(
            result,
            "sa.Column('some_key', sa.Integer(), "
            "nullable=True, "
            "comment='This is a comment')",
        )

    def test_render_col_comment_with_quote(self):
        c = Column("some_key", Integer, comment="This is a john's comment")
        Table("some_table", MetaData(), c)
        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_ignore_whitespace(
            result,
            "sa.Column('some_key', sa.Integer(), "
            "nullable=True, "
            'comment="This is a john\'s comment")',
        )

    def test_render_col_autoinc_false_mysql(self):
        c = Column("some_key", Integer, primary_key=True, autoincrement=False)
        Table("some_table", MetaData(), c)
        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_ignore_whitespace(
            result,
            "sa.Column('some_key', sa.Integer(), "
            "autoincrement=False, "
            "nullable=False)",
        )

    def test_render_custom(self):
        class MySpecialType(Integer):
            pass

        def render(type_, obj, context):
            if type_ == "foreign_key":
                # causes it not to render
                return None
            if type_ == "column":
                if obj.name == "y":
                    return None
                elif obj.name == "q":
                    return False
                else:
                    return "col(%s)" % obj.name
            if type_ == "type" and isinstance(obj, MySpecialType):
                context.imports.add("from mypackage import MySpecialType")
                return "MySpecialType()"

            return "render:%s" % type_

        self.autogen_context.opts.update(
            render_item=render, alembic_module_prefix="sa."
        )

        t = Table(
            "t",
            MetaData(),
            Column("x", Integer),
            Column("y", Integer),
            Column("q", MySpecialType()),
            PrimaryKeyConstraint("x"),
            ForeignKeyConstraint(["x"], ["remote.y"]),
        )
        op_obj = ops.CreateTableOp.from_table(t)
        result = autogenerate.render_op_text(self.autogen_context, op_obj)
        eq_ignore_whitespace(
            result,
            "sa.create_table('t',"
            "col(x),"
            "sa.Column('q', MySpecialType(), nullable=True),"
            "render:primary_key)",
        )
        eq_(
            self.autogen_context.imports,
            {"from mypackage import MySpecialType"},
        )

    def test_render_modify_type(self):
        op_obj = ops.AlterColumnOp(
            "sometable",
            "somecolumn",
            modify_type=CHAR(10),
            existing_type=CHAR(20),
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.CHAR(length=20), type_=sa.CHAR(length=10))",
        )

    def test_render_modify_type_w_schema(self):
        op_obj = ops.AlterColumnOp(
            "sometable",
            "somecolumn",
            modify_type=CHAR(10),
            existing_type=CHAR(20),
            schema="foo",
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.CHAR(length=20), type_=sa.CHAR(length=10), "
            "schema='foo')",
        )

    def test_render_modify_nullable(self):
        op_obj = ops.AlterColumnOp(
            "sometable",
            "somecolumn",
            existing_type=Integer(),
            modify_nullable=True,
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True)",
        )

    def test_render_modify_nullable_no_existing_type(self):
        op_obj = ops.AlterColumnOp(
            "sometable", "somecolumn", modify_nullable=True
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', nullable=True)",
        )

    def test_render_modify_nullable_w_schema(self):
        op_obj = ops.AlterColumnOp(
            "sometable",
            "somecolumn",
            existing_type=Integer(),
            modify_nullable=True,
            schema="foo",
        )

        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True, schema='foo')",
        )

    def test_render_modify_type_w_autoincrement(self):
        op_obj = ops.AlterColumnOp(
            "sometable",
            "somecolumn",
            modify_type=Integer(),
            existing_type=BigInteger(),
            autoincrement=True,
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.BigInteger(), type_=sa.Integer(), "
            "autoincrement=True)",
        )

    def test_render_fk_constraint_kwarg(self):
        m = MetaData()
        t1 = Table("t", m, Column("c", Integer))
        t2 = Table("t2", m, Column("c_rem", Integer))

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], onupdate="CASCADE")

        # SQLA 0.9 generates a u'' here for remote cols while 0.8 does not,
        # so just whack out "'u" here from the generated

        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context, m
                ),
            ),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], onupdate='CASCADE')",
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], ondelete="CASCADE")

        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context, m
                ),
            ),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], ondelete='CASCADE')",
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], deferrable=True)
        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context, m
                ),
            ),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], deferrable=True)",
        )

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], initially="XYZ")
        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context, m
                ),
            ),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], initially='XYZ')",
        )

        fk = ForeignKeyConstraint(
            [t1.c.c],
            [t2.c.c_rem],
            initially="XYZ",
            ondelete="CASCADE",
            deferrable=True,
        )
        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context, m
                ),
            ),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], "
            "ondelete='CASCADE', initially='XYZ', deferrable=True)",
        )

    def test_render_fk_constraint_resolve_key(self):
        m = MetaData()
        t1 = Table("t", m, Column("c", Integer))
        Table("t2", m, Column("c_rem", Integer, key="c_remkey"))

        fk = ForeignKeyConstraint(["c"], ["t2.c_remkey"])
        t1.append_constraint(fk)

        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context, m
                ),
            ),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], )",
        )

    def test_render_fk_constraint_bad_table_resolve(self):
        m = MetaData()
        t1 = Table("t", m, Column("c", Integer))
        Table("t2", m, Column("c_rem", Integer))

        fk = ForeignKeyConstraint(["c"], ["t2.nonexistent"])
        t1.append_constraint(fk)

        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context, m
                ),
            ),
            "sa.ForeignKeyConstraint(['c'], ['t2.nonexistent'], )",
        )

    def test_render_fk_constraint_bad_table_resolve_dont_get_confused(self):
        m = MetaData()
        t1 = Table("t", m, Column("c", Integer))
        Table(
            "t2",
            m,
            Column("c_rem", Integer, key="cr_key"),
            Column("c_rem_2", Integer, key="c_rem"),
        )

        fk = ForeignKeyConstraint(["c"], ["t2.c_rem"], link_to_name=True)
        t1.append_constraint(fk)

        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context, m
                ),
            ),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], )",
        )

    def test_render_fk_constraint_link_to_name(self):
        m = MetaData()
        t1 = Table("t", m, Column("c", Integer))
        Table("t2", m, Column("c_rem", Integer, key="c_remkey"))

        fk = ForeignKeyConstraint(["c"], ["t2.c_rem"], link_to_name=True)
        t1.append_constraint(fk)

        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context, m
                ),
            ),
            "sa.ForeignKeyConstraint(['c'], ['t2.c_rem'], )",
        )

    def test_render_fk_constraint_use_alter(self):
        m = MetaData()
        Table("t", m, Column("c", Integer))
        t2 = Table(
            "t2",
            m,
            Column(
                "c_rem", Integer, ForeignKey("t.c", name="fk1", use_alter=True)
            ),
        )
        const = list(t2.foreign_keys)[0].constraint

        eq_ignore_whitespace(
            autogenerate.render._render_constraint(
                const, self.autogen_context, m
            ),
            "sa.ForeignKeyConstraint(['c_rem'], ['t.c'], "
            "name='fk1', use_alter=True)",
        )

    def test_render_fk_constraint_w_metadata_schema(self):
        m = MetaData(schema="foo")
        t1 = Table("t", m, Column("c", Integer))
        t2 = Table("t2", m, Column("c_rem", Integer))

        fk = ForeignKeyConstraint([t1.c.c], [t2.c.c_rem], onupdate="CASCADE")

        eq_ignore_whitespace(
            re.sub(
                r"u'",
                "'",
                autogenerate.render._render_constraint(
                    fk, self.autogen_context, m
                ),
            ),
            "sa.ForeignKeyConstraint(['c'], ['foo.t2.c_rem'], "
            "onupdate='CASCADE')",
        )

    def test_render_check_constraint_literal(self):
        eq_ignore_whitespace(
            autogenerate.render._render_check_constraint(
                CheckConstraint("im a constraint", name="cc1"),
                self.autogen_context,
                None,
            ),
            "sa.CheckConstraint('im a constraint', name='cc1')",
        )

    def test_render_check_constraint_sqlexpr(self):
        c = column("c")
        five = literal_column("5")
        ten = literal_column("10")
        eq_ignore_whitespace(
            autogenerate.render._render_check_constraint(
                CheckConstraint(and_(c > five, c < ten)),
                self.autogen_context,
                None,
            ),
            "sa.CheckConstraint('c > 5 AND c < 10')",
        )

    def test_render_check_constraint_literal_binds(self):
        c = column("c")
        eq_ignore_whitespace(
            autogenerate.render._render_check_constraint(
                CheckConstraint(and_(c > 5, c < 10)),
                self.autogen_context,
                None,
            ),
            "sa.CheckConstraint('c > 5 AND c < 10')",
        )

    def test_render_unique_constraint_opts(self):
        m = MetaData()
        t = Table("t", m, Column("c", Integer))
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(
                UniqueConstraint(t.c.c, name="uq_1", deferrable="XYZ"),
                self.autogen_context,
                None,
            ),
            "sa.UniqueConstraint('c', deferrable='XYZ', name='uq_1')",
        )

    def test_add_unique_constraint_unicode_schema(self):
        m = MetaData()
        t = Table(
            "t",
            m,
            Column("c", Integer),
            schema="\u0411\u0435\u0437",
        )
        op_obj = ops.AddConstraintOp.from_constraint(UniqueConstraint(t.c.c))
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_unique_constraint(None, 't', ['c'], "
            "schema=%r)" % "\u0411\u0435\u0437",
        )

    def test_render_modify_nullable_w_default(self):
        op_obj = ops.AlterColumnOp(
            "sometable",
            "somecolumn",
            existing_type=Integer(),
            existing_server_default="5",
            modify_nullable=True,
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True, "
            "existing_server_default='5')",
        )

    def test_render_enum(self):
        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                Enum("one", "two", "three", name="myenum"),
                self.autogen_context,
            ),
            "sa.Enum('one', 'two', 'three', name='myenum')",
        )
        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                Enum("one", "two", "three"), self.autogen_context
            ),
            "sa.Enum('one', 'two', 'three')",
        )

    def test_render_non_native_enum(self):
        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                Enum("one", "two", "three", native_enum=False),
                self.autogen_context,
            ),
            "sa.Enum('one', 'two', 'three', native_enum=False)",
        )

    def test_repr_plain_sqla_type(self):
        type_ = Integer()
        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, self.autogen_context),
            "sa.Integer()",
        )

    def test_generic_array_type(self):

        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                types.ARRAY(Integer), self.autogen_context
            ),
            "sa.ARRAY(sa.Integer())",
        )

        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                types.ARRAY(DateTime(timezone=True)), self.autogen_context
            ),
            "sa.ARRAY(sa.DateTime(timezone=True))",
        )

    def test_render_array_no_context(self):
        uo = ops.UpgradeOps(
            ops=[
                ops.CreateTableOp(
                    "sometable", [Column("x", types.ARRAY(Integer))]
                )
            ]
        )

        eq_(
            autogenerate.render_python_code(uo),
            "# ### commands auto generated by Alembic - please adjust! ###\n"
            "    op.create_table('sometable',\n"
            "    sa.Column('x', sa.ARRAY(sa.Integer()), nullable=True)\n"
            "    )\n"
            "    # ### end Alembic commands ###",
        )

    def test_render_server_default_no_context(self):
        uo = ops.UpgradeOps(
            ops=[
                ops.CreateTableOp(
                    "sometable",
                    [Column("x", types.DateTime(), server_default=func.now())],
                )
            ]
        )

        eq_ignore_whitespace(
            autogenerate.render_python_code(uo),
            "# ### commands auto generated by Alembic - please adjust! ###\n"
            "    op.create_table('sometable',\n"
            "    sa.Column('x', sa.DateTime(), "
            "server_default=sa.text('now()'), nullable=True)\n"
            "    )\n"
            "    # ### end Alembic commands ###",
        )

    def test_render_server_default_context_passed(self):
        uo = ops.UpgradeOps(
            ops=[
                ops.CreateTableOp(
                    "sometable",
                    [Column("x", types.DateTime(), server_default=func.now())],
                )
            ]
        )
        context = MigrationContext.configure(dialect_name="sqlite")
        eq_ignore_whitespace(
            autogenerate.render_python_code(uo, migration_context=context),
            "# ### commands auto generated by Alembic - please adjust! ###\n"
            "    op.create_table('sometable',\n"
            "    sa.Column('x', sa.DateTime(), "
            "server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True)\n"
            "    )\n"
            "    # ### end Alembic commands ###",
        )

    def test_repr_custom_type_w_sqla_prefix(self):
        self.autogen_context.opts["user_module_prefix"] = None

        class MyType(UserDefinedType):
            pass

        MyType.__module__ = "sqlalchemy_util.types"

        type_ = MyType()

        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, self.autogen_context),
            "sqlalchemy_util.types.MyType()",
        )

    def test_render_variant(self):
        from sqlalchemy import VARCHAR, CHAR

        self.autogen_context.opts["user_module_prefix"] = None

        type_ = (
            String(5)
            .with_variant(VARCHAR(10), "mysql")
            .with_variant(CHAR(15), "oracle")
        )

        # the new Black formatting will help a lot with this
        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, self.autogen_context),
            "sa.String(length=5)."
            "with_variant(sa.VARCHAR(length=10), 'mysql')."
            "with_variant(sa.CHAR(length=15), 'oracle')",
        )

    def test_repr_user_type_user_prefix_None(self):
        class MyType(UserDefinedType):
            def get_col_spec(self):
                return "MYTYPE"

        type_ = MyType()
        self.autogen_context.opts["user_module_prefix"] = None

        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, self.autogen_context),
            "tests.test_autogen_render.MyType()",
        )

    def test_repr_user_type_user_prefix_present(self):
        from sqlalchemy.types import UserDefinedType

        class MyType(UserDefinedType):
            def get_col_spec(self):
                return "MYTYPE"

        type_ = MyType()

        self.autogen_context.opts["user_module_prefix"] = "user."

        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, self.autogen_context),
            "user.MyType()",
        )

    def test_repr_dialect_type(self):
        from sqlalchemy.dialects.mysql import VARCHAR

        type_ = VARCHAR(20, charset="utf8", national=True)

        self.autogen_context.opts["user_module_prefix"] = None

        eq_ignore_whitespace(
            autogenerate.render._repr_type(type_, self.autogen_context),
            "mysql.VARCHAR(charset='utf8', national=True, length=20)",
        )
        eq_(
            self.autogen_context.imports,
            {"from sqlalchemy.dialects import mysql"},
        )

    def test_render_server_default_text(self):
        c = Column(
            "updated_at",
            TIMESTAMP(),
            server_default=text("now()"),
            nullable=False,
        )
        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_ignore_whitespace(
            result,
            "sa.Column('updated_at', sa.TIMESTAMP(), "
            "server_default=sa.text('now()'), "
            "nullable=False)",
        )

    def test_render_server_default_non_native_boolean(self):
        c = Column(
            "updated_at", Boolean(), server_default=false(), nullable=False
        )

        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_ignore_whitespace(
            result,
            "sa.Column('updated_at', sa.Boolean(), "
            "server_default=sa.text('0'), "
            "nullable=False)",
        )

    def test_render_server_default_func(self):
        c = Column(
            "updated_at",
            TIMESTAMP(),
            server_default=func.now(),
            nullable=False,
        )
        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_ignore_whitespace(
            result,
            "sa.Column('updated_at', sa.TIMESTAMP(), "
            "server_default=sa.text('now()'), "
            "nullable=False)",
        )

    def test_render_server_default_int(self):
        c = Column("value", Integer, server_default="0")
        result = autogenerate.render._render_column(c, self.autogen_context)
        eq_(
            result,
            "sa.Column('value', sa.Integer(), "
            "server_default='0', nullable=True)",
        )

    def test_render_modify_reflected_int_server_default(self):
        op_obj = ops.AlterColumnOp(
            "sometable",
            "somecolumn",
            existing_type=Integer(),
            existing_server_default=DefaultClause(text("5")),
            modify_nullable=True,
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_type=sa.Integer(), nullable=True, "
            "existing_server_default=sa.text('5'))",
        )

    def test_render_executesql_plaintext(self):
        op_obj = ops.ExecuteSQLOp("drop table foo")
        eq_(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.execute('drop table foo')",
        )

    def test_render_executesql_sqlexpr_notimplemented(self):
        sql = table("x", column("q")).insert()
        op_obj = ops.ExecuteSQLOp(sql)
        assert_raises(
            NotImplementedError,
            autogenerate.render_op_text,
            self.autogen_context,
            op_obj,
        )

    def test_render_alter_column_modify_comment(self):
        op_obj = ops.AlterColumnOp(
            "sometable", "somecolumn", modify_comment="This is a comment"
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "comment='This is a comment')",
        )

    def test_render_alter_column_existing_comment(self):
        op_obj = ops.AlterColumnOp(
            "sometable", "somecolumn", existing_comment="This is a comment"
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_comment='This is a comment')",
        )

    def test_render_col_drop_comment(self):
        op_obj = ops.AlterColumnOp(
            "sometable",
            "somecolumn",
            existing_comment="This is a comment",
            modify_comment=None,
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "comment=None, "
            "existing_comment='This is a comment')",
        )

    def test_render_table_with_comment(self):
        m = MetaData()
        t = Table(
            "test",
            m,
            Column("id", Integer, primary_key=True),
            Column("q", Integer, ForeignKey("address.id")),
            comment="test comment",
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('test',"
            "sa.Column('id', sa.Integer(), nullable=False),"
            "sa.Column('q', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['q'], ['address.id'], ),"
            "sa.PrimaryKeyConstraint('id'),"
            "comment='test comment'"
            ")",
        )

    def test_render_add_column_with_comment(self):
        op_obj = ops.AddColumnOp(
            "foo", Column("x", Integer, comment="This is a Column")
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.add_column('foo', sa.Column('x', sa.Integer(), "
            "nullable=True, comment='This is a Column'))",
        )

    def test_render_create_table_comment_op(self):
        op_obj = ops.CreateTableCommentOp("table_name", "comment")
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table_comment("
            "   'table_name',"
            "   'comment',"
            "   existing_comment=None,"
            "   schema=None"
            ")",
        )

    def test_render_create_table_comment_with_quote_op(self):
        op_obj = ops.CreateTableCommentOp(
            "table_name",
            "This is john's comment",
            existing_comment='This was john\'s "comment"',
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table_comment("
            "   'table_name',"
            '   "This is john\'s comment",'
            "   existing_comment='This was john\\'s \"comment\"',"
            "   schema=None"
            ")",
        )

    def test_render_create_table_comment_op_with_existing_comment(self):
        op_obj = ops.CreateTableCommentOp(
            "table_name", "comment", existing_comment="old comment"
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table_comment("
            "   'table_name',"
            "   'comment',"
            "   existing_comment='old comment',"
            "   schema=None"
            ")",
        )

    def test_render_create_table_comment_op_with_schema(self):
        op_obj = ops.CreateTableCommentOp(
            "table_name", "comment", schema="SomeSchema"
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table_comment("
            "   'table_name',"
            "   'comment',"
            "   existing_comment=None,"
            "   schema='SomeSchema'"
            ")",
        )

    def test_render_drop_table_comment_op(self):
        op_obj = ops.DropTableCommentOp("table_name")
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_table_comment("
            "   'table_name',"
            "   existing_comment=None,"
            "   schema=None"
            ")",
        )

    def test_render_drop_table_comment_op_existing_with_quote(self):
        op_obj = ops.DropTableCommentOp(
            "table_name", existing_comment="This was john's comment"
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_table_comment("
            "   'table_name',"
            '   existing_comment="This was john\'s comment",'
            "   schema=None"
            ")",
        )

    @config.requirements.computed_columns_api
    def test_render_add_column_computed(self):
        c = sa.Computed("5")
        op_obj = ops.AddColumnOp("foo", Column("x", Integer, c))
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.add_column('foo', sa.Column('x', sa.Integer(), "
            "sa.Computed('5', ), nullable=True))",
        )

    @config.requirements.computed_columns_api
    @testing.combinations((True,), (False,))
    def test_render_add_column_computed_persisted(self, persisted):
        op_obj = ops.AddColumnOp(
            "foo", Column("x", Integer, sa.Computed("5", persisted=persisted))
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.add_column('foo', sa.Column('x', sa.Integer(), "
            "sa.Computed('5', persisted=%s), nullable=True))" % persisted,
        )

    @config.requirements.computed_columns_api
    def test_render_alter_column_computed_modify_default(self):
        op_obj = ops.AlterColumnOp(
            "sometable", "somecolumn", modify_server_default=sa.Computed("7")
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "server_default=sa.Computed('7', ))",
        )

    @config.requirements.computed_columns_api
    def test_render_alter_column_computed_existing_default(self):
        op_obj = ops.AlterColumnOp(
            "sometable",
            "somecolumn",
            existing_server_default=sa.Computed("42"),
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_server_default=sa.Computed('42', ))",
        )

    @config.requirements.computed_columns_api
    @testing.combinations((True,), (False,))
    def test_render_alter_column_computed_modify_default_perisisted(
        self, persisted
    ):
        op_obj = ops.AlterColumnOp(
            "sometable",
            "somecolumn",
            modify_server_default=sa.Computed("7", persisted=persisted),
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', server_default"
            "=sa.Computed('7', persisted=%s))" % persisted,
        )

    @config.requirements.computed_columns_api
    @testing.combinations((True,), (False,))
    def test_render_alter_column_computed_existing_default_perisisted(
        self, persisted
    ):
        c = sa.Computed("42", persisted=persisted)
        op_obj = ops.AlterColumnOp(
            "sometable", "somecolumn", existing_server_default=c
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('sometable', 'somecolumn', "
            "existing_server_default=sa.Computed('42', persisted=%s))"
            % persisted,
        )

    @config.requirements.identity_columns_api
    @testing.combinations(
        ({}, "sa.Identity(always=False)"),
        (dict(always=None), "sa.Identity(always=None)"),
        (dict(always=True), "sa.Identity(always=True)"),
        (
            dict(
                always=False,
                on_null=True,
                start=2,
                increment=4,
                minvalue=-3,
                maxvalue=99,
                nominvalue=True,
                nomaxvalue=True,
                cycle=True,
                cache=42,
                order=True,
            ),
            "sa.Identity(always=False, on_null=True, start=2, increment=4, "
            "minvalue=-3, maxvalue=99, nominvalue=True, nomaxvalue=True, "
            "cycle=True, cache=42, order=True)",
        ),
    )
    def test_render_add_column_identity(self, kw, text):
        col = Column("x", Integer, sa.Identity(**kw))
        op_obj = ops.AddColumnOp("foo", col)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.add_column('foo', sa.Column('x', sa.Integer(), "
            "%s, nullable=%r))" % (text, col.nullable),
        )

    @config.requirements.identity_columns_api
    @testing.combinations(
        ({}, "sa.Identity(always=False)"),
        (dict(always=None), "sa.Identity(always=None)"),
        (dict(always=True), "sa.Identity(always=True)"),
        (
            dict(
                always=False,
                on_null=True,
                start=2,
                increment=4,
                minvalue=-3,
                maxvalue=99,
                nominvalue=True,
                nomaxvalue=True,
                cycle=True,
                cache=42,
                order=True,
            ),
            "sa.Identity(always=False, on_null=True, start=2, increment=4, "
            "minvalue=-3, maxvalue=99, nominvalue=True, nomaxvalue=True, "
            "cycle=True, cache=42, order=True)",
        ),
    )
    def test_render_alter_column_add_identity(self, kw, text):
        op_obj = ops.AlterColumnOp(
            "foo",
            "x",
            existing_type=Integer(),
            existing_server_default=None,
            modify_server_default=sa.Identity(**kw),
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('foo', 'x', existing_type=sa.Integer(), "
            "server_default=%s)" % text,
        )

    @config.requirements.identity_columns_api
    def test_render_alter_column_drop_identity(self):
        op_obj = ops.AlterColumnOp(
            "foo",
            "x",
            existing_type=Integer(),
            existing_server_default=sa.Identity(),
            modify_server_default=None,
        )
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.alter_column('foo', 'x', existing_type=sa.Integer(), "
            "server_default=None)",
        )


class RenderNamingConventionTest(TestBase):
    def setUp(self):

        convention = {
            "ix": "ix_%(custom)s_%(column_0_label)s",
            "uq": "uq_%(custom)s_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(custom)s_%(table_name)s",
            "fk": "fk_%(custom)s_%(table_name)s_"
            "%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(custom)s_%(table_name)s",
            "custom": lambda const, table: "ct",
        }

        self.metadata = MetaData(naming_convention=convention)

        ctx_opts = {
            "sqlalchemy_module_prefix": "sa.",
            "alembic_module_prefix": "op.",
            "target_metadata": MetaData(),
        }
        context = MigrationContext.configure(
            dialect_name="postgresql", opts=ctx_opts
        )
        self.autogen_context = api.AutogenContext(context)

    def test_schema_type_boolean(self):
        t = Table("t", self.metadata, Column("c", Boolean(name="xyz")))
        op_obj = ops.AddColumnOp.from_column(t.c.c)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.add_column('t', "
            "sa.Column('c', sa.Boolean(name='xyz'), nullable=True))",
        )

    def test_explicit_unique_constraint(self):
        t = Table("t", self.metadata, Column("c", Integer))
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(
                UniqueConstraint(t.c.c, deferrable="XYZ"),
                self.autogen_context,
                None,
            ),
            "sa.UniqueConstraint('c', deferrable='XYZ', "
            "name=op.f('uq_ct_t_c'))",
        )

    def test_explicit_named_unique_constraint(self):
        t = Table("t", self.metadata, Column("c", Integer))
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(
                UniqueConstraint(t.c.c, name="q"), self.autogen_context, None
            ),
            "sa.UniqueConstraint('c', name='q')",
        )

    def test_render_add_index(self):
        t = Table(
            "test",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
        )
        idx = Index(None, t.c.active, t.c.code)
        op_obj = ops.CreateIndexOp.from_index(idx)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_index(op.f('ix_ct_test_active'), 'test', "
            "['active', 'code'], unique=False)",
        )

    def test_render_drop_index(self):
        t = Table(
            "test",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
        )
        idx = Index(None, t.c.active, t.c.code)
        op_obj = ops.DropIndexOp.from_index(idx)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_index(op.f('ix_ct_test_active'), table_name='test')",
        )

    def test_render_add_index_schema(self):
        t = Table(
            "test",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("active", Boolean()),
            Column("code", String(255)),
            schema="CamelSchema",
        )
        idx = Index(None, t.c.active, t.c.code)
        op_obj = ops.CreateIndexOp.from_index(idx)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_index(op.f('ix_ct_CamelSchema_test_active'), 'test', "
            "['active', 'code'], unique=False, schema='CamelSchema')",
        )

    def test_implicit_unique_constraint(self):
        t = Table("t", self.metadata, Column("c", Integer, unique=True))
        uq = [c for c in t.constraints if isinstance(c, UniqueConstraint)][0]
        eq_ignore_whitespace(
            autogenerate.render._render_unique_constraint(
                uq, self.autogen_context, None
            ),
            "sa.UniqueConstraint('c', name=op.f('uq_ct_t_c'))",
        )

    def test_inline_pk_constraint(self):
        t = Table("t", self.metadata, Column("c", Integer, primary_key=True))
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('t',sa.Column('c', sa.Integer(), nullable=False),"
            "sa.PrimaryKeyConstraint('c', name=op.f('pk_ct_t')))",
        )

    def test_inline_ck_constraint(self):
        t = Table(
            "t", self.metadata, Column("c", Integer), CheckConstraint("c > 5")
        )
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('t',sa.Column('c', sa.Integer(), nullable=True),"
            "sa.CheckConstraint('c > 5', name=op.f('ck_ct_t')))",
        )

    def test_inline_fk(self):
        t = Table("t", self.metadata, Column("c", Integer, ForeignKey("q.id")))
        op_obj = ops.CreateTableOp.from_table(t)
        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_table('t',sa.Column('c', sa.Integer(), nullable=True),"
            "sa.ForeignKeyConstraint(['c'], ['q.id'], "
            "name=op.f('fk_ct_t_c_q')))",
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
        m1 = MetaData(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )
        ck = CheckConstraint("im a constraint", name="cc1")
        Table("t", m1, Column("x"), ck)

        eq_ignore_whitespace(
            autogenerate.render._render_check_constraint(
                ck, self.autogen_context, None
            ),
            "sa.CheckConstraint('im a constraint', name=op.f('ck_t_cc1'))",
        )

    def test_create_table_plus_add_index_in_modify(self):
        uo = ops.UpgradeOps(
            ops=[
                ops.CreateTableOp(
                    "sometable", [Column("x", Integer), Column("y", Integer)]
                ),
                ops.ModifyTableOps(
                    "sometable",
                    ops=[ops.CreateIndexOp("ix1", "sometable", ["x", "y"])],
                ),
            ]
        )

        eq_(
            autogenerate.render_python_code(uo, render_as_batch=True),
            "# ### commands auto generated by Alembic - please adjust! ###\n"
            "    op.create_table('sometable',\n"
            "    sa.Column('x', sa.Integer(), nullable=True),\n"
            "    sa.Column('y', sa.Integer(), nullable=True)\n"
            "    )\n"
            "    with op.batch_alter_table('sometable', schema=None) "
            "as batch_op:\n"
            "        batch_op.create_index("
            "'ix1', ['x', 'y'], unique=False)\n\n"
            "    # ### end Alembic commands ###",
        )
