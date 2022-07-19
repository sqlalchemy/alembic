from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy.sql import column
from sqlalchemy.sql import func

from alembic import op
from alembic.testing.fixtures import op_fixture
from alembic.testing.fixtures import TestBase


class AutoNamingConventionTest(TestBase):
    def test_add_check_constraint(self):
        context = op_fixture(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )
        op.create_check_constraint(
            "foo", "user_table", func.len(column("name")) > 5
        )
        context.assert_(
            "ALTER TABLE user_table ADD CONSTRAINT ck_user_table_foo "
            "CHECK (len(name) > 5)"
        )

    def test_add_check_constraint_name_is_none(self):
        context = op_fixture(naming_convention={"ck": "ck_%(table_name)s_foo"})
        op.create_check_constraint(
            None, "user_table", func.len(column("name")) > 5
        )
        context.assert_(
            "ALTER TABLE user_table ADD CONSTRAINT ck_user_table_foo "
            "CHECK (len(name) > 5)"
        )

    def test_add_unique_constraint_name_is_none(self):
        context = op_fixture(naming_convention={"uq": "uq_%(table_name)s_foo"})
        op.create_unique_constraint(None, "user_table", "x")
        context.assert_(
            "ALTER TABLE user_table "
            "ADD CONSTRAINT uq_user_table_foo UNIQUE (x)"
        )

    def test_add_index_name_is_none(self):
        context = op_fixture(naming_convention={"ix": "ix_%(table_name)s_foo"})
        op.create_index(None, "user_table", "x")
        context.assert_("CREATE INDEX ix_user_table_foo ON user_table (x)")

    def test_add_check_constraint_already_named_from_schema(self):
        m1 = MetaData(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )
        ck = CheckConstraint("im a constraint", name="cc1")
        Table("t", m1, Column("x"), ck)

        context = op_fixture(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )

        op.create_table("some_table", Column("x", Integer, ck))
        context.assert_(
            "CREATE TABLE some_table "
            "(x INTEGER CONSTRAINT ck_t_cc1 CHECK (im a constraint))"
        )

    def test_add_check_constraint_inline_on_table(self):
        context = op_fixture(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )
        op.create_table(
            "some_table",
            Column("x", Integer),
            CheckConstraint("im a constraint", name="cc1"),
        )
        context.assert_(
            "CREATE TABLE some_table "
            "(x INTEGER, CONSTRAINT ck_some_table_cc1 CHECK (im a constraint))"
        )

    def test_add_check_constraint_inline_on_table_w_f(self):
        context = op_fixture(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )
        op.create_table(
            "some_table",
            Column("x", Integer),
            CheckConstraint("im a constraint", name=op.f("ck_some_table_cc1")),
        )
        context.assert_(
            "CREATE TABLE some_table "
            "(x INTEGER, CONSTRAINT ck_some_table_cc1 CHECK (im a constraint))"
        )

    def test_add_check_constraint_inline_on_column(self):
        context = op_fixture(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )
        op.create_table(
            "some_table",
            Column(
                "x", Integer, CheckConstraint("im a constraint", name="cc1")
            ),
        )
        context.assert_(
            "CREATE TABLE some_table "
            "(x INTEGER CONSTRAINT ck_some_table_cc1 CHECK (im a constraint))"
        )

    def test_add_check_constraint_inline_on_column_w_f(self):
        context = op_fixture(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )
        op.create_table(
            "some_table",
            Column(
                "x",
                Integer,
                CheckConstraint("im a constraint", name=op.f("ck_q_cc1")),
            ),
        )
        context.assert_(
            "CREATE TABLE some_table "
            "(x INTEGER CONSTRAINT ck_q_cc1 CHECK (im a constraint))"
        )

    def test_add_column_schema_type(self):
        context = op_fixture(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )
        op.add_column(
            "t1",
            Column(
                "c1",
                Boolean(name="foo", create_constraint=True),
                nullable=False,
            ),
        )
        context.assert_(
            "ALTER TABLE t1 ADD COLUMN c1 BOOLEAN NOT NULL",
            "ALTER TABLE t1 ADD CONSTRAINT ck_t1_foo CHECK (c1 IN (0, 1))",
        )

    def test_add_column_schema_type_w_f(self):
        context = op_fixture(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )
        op.add_column(
            "t1",
            Column(
                "c1",
                Boolean(name=op.f("foo"), create_constraint=True),
                nullable=False,
            ),
        )
        context.assert_(
            "ALTER TABLE t1 ADD COLUMN c1 BOOLEAN NOT NULL",
            "ALTER TABLE t1 ADD CONSTRAINT foo CHECK (c1 IN (0, 1))",
        )

    def test_drop_check_constraint_plain(self):
        context = op_fixture(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )

        op.drop_constraint("foo_bar_bat", "t1", type_="check")
        context.assert_("ALTER TABLE t1 DROP CONSTRAINT ck_t1_foo_bar_bat")

    def test_drop_check_constraint_opf(self):
        context = op_fixture(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )

        op.drop_constraint(
            op.f("some_specific_foo_bar_bat"), "t1", type_="check"
        )
        context.assert_(
            "ALTER TABLE t1 DROP CONSTRAINT some_specific_foo_bar_bat"
        )
