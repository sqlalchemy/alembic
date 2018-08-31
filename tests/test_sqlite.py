from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy.sql import column

from alembic import op
from alembic.testing import assert_raises_message
from alembic.testing import config
from alembic.testing.fixtures import op_fixture
from alembic.testing.fixtures import TestBase


class SQLiteTest(TestBase):
    def test_add_column(self):
        context = op_fixture("sqlite")
        op.add_column("t1", Column("c1", Integer))
        context.assert_("ALTER TABLE t1 ADD COLUMN c1 INTEGER")

    def test_add_column_implicit_constraint(self):
        context = op_fixture("sqlite")
        op.add_column("t1", Column("c1", Boolean))
        context.assert_("ALTER TABLE t1 ADD COLUMN c1 BOOLEAN")

    def test_add_explicit_constraint(self):
        op_fixture("sqlite")
        assert_raises_message(
            NotImplementedError,
            "No support for ALTER of constraints in SQLite dialect",
            op.create_check_constraint,
            "foo",
            "sometable",
            column("name") > 5,
        )

    def test_drop_explicit_constraint(self):
        op_fixture("sqlite")
        assert_raises_message(
            NotImplementedError,
            "No support for ALTER of constraints in SQLite dialect",
            op.drop_constraint,
            "foo",
            "sometable",
        )

    @config.requirements.comments
    def test_create_table_with_comment_ignored(self):

        context = op_fixture("sqlite")
        op.create_table(
            "t2",
            Column("c1", Integer, primary_key=True),
            Column("c2", Integer),
            comment="This is a table comment",
        )
        context.assert_(
            "CREATE TABLE t2 (c1 INTEGER NOT NULL, "
            "c2 INTEGER, PRIMARY KEY (c1))"
        )

    @config.requirements.comments
    def test_add_column_with_comment_ignored(self):

        context = op_fixture("sqlite")
        op.add_column("t1", Column("c1", Integer, comment="c1 comment"))
        context.assert_("ALTER TABLE t1 ADD COLUMN c1 INTEGER")
