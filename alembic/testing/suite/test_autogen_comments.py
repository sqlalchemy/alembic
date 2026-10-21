from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table

from ._autogen_fixtures import AutogenFixtureTest
from ... import testing
from ...testing import eq_
from ...testing import mock
from ...testing import TestBase


class AutogenerateCommentsTest(AutogenFixtureTest, TestBase):
    __backend__ = True

    __requires__ = ("comments",)

    def test_existing_table_comment_no_change(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("test", String(10), primary_key=True),
            comment="this is some table",
        )

        Table(
            "some_table",
            m2,
            Column("test", String(10), primary_key=True),
            comment="this is some table",
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_add_table_comment(self):
        m1 = MetaData()
        m2 = MetaData()

        Table("some_table", m1, Column("test", String(10), primary_key=True))

        Table(
            "some_table",
            m2,
            Column("test", String(10), primary_key=True),
            comment="this is some table",
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table_comment")
        eq_(diffs[0][1].comment, "this is some table")
        eq_(diffs[0][2], None)

    def test_remove_table_comment(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("test", String(10), primary_key=True),
            comment="this is some table",
        )

        Table("some_table", m2, Column("test", String(10), primary_key=True))

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "remove_table_comment")
        eq_(diffs[0][1].comment, None)

    def test_alter_table_comment(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("test", String(10), primary_key=True),
            comment="this is some table",
        )

        Table(
            "some_table",
            m2,
            Column("test", String(10), primary_key=True),
            comment="this is also some table",
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table_comment")
        eq_(diffs[0][1].comment, "this is also some table")
        eq_(diffs[0][2], "this is some table")

    def test_existing_column_comment_no_change(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("test", String(10), primary_key=True),
            Column("amount", Float, comment="the amount"),
        )

        Table(
            "some_table",
            m2,
            Column("test", String(10), primary_key=True),
            Column("amount", Float, comment="the amount"),
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_add_column_comment(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("test", String(10), primary_key=True),
            Column("amount", Float),
        )

        Table(
            "some_table",
            m2,
            Column("test", String(10), primary_key=True),
            Column("amount", Float, comment="the amount"),
        )

        diffs = self._fixture(m1, m2)
        eq_(
            diffs,
            [
                [
                    (
                        "modify_comment",
                        None,
                        "some_table",
                        "amount",
                        {
                            "existing_nullable": True,
                            "existing_type": mock.ANY,
                            "existing_server_default": False,
                        },
                        None,
                        "the amount",
                    )
                ]
            ],
        )

    def test_remove_column_comment(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("test", String(10), primary_key=True),
            Column("amount", Float, comment="the amount"),
        )

        Table(
            "some_table",
            m2,
            Column("test", String(10), primary_key=True),
            Column("amount", Float),
        )

        diffs = self._fixture(m1, m2)
        eq_(
            diffs,
            [
                [
                    (
                        "modify_comment",
                        None,
                        "some_table",
                        "amount",
                        {
                            "existing_nullable": True,
                            "existing_type": mock.ANY,
                            "existing_server_default": False,
                        },
                        "the amount",
                        None,
                    )
                ]
            ],
        )

    def test_alter_column_comment(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("test", String(10), primary_key=True),
            Column("amount", Float, comment="the amount"),
        )

        Table(
            "some_table",
            m2,
            Column("test", String(10), primary_key=True),
            Column("amount", Float, comment="the adjusted amount"),
        )

        diffs = self._fixture(m1, m2)

        eq_(
            diffs,
            [
                [
                    (
                        "modify_comment",
                        None,
                        "some_table",
                        "amount",
                        {
                            "existing_nullable": True,
                            "existing_type": mock.ANY,
                            "existing_server_default": False,
                        },
                        "the amount",
                        "the adjusted amount",
                    )
                ]
            ],
        )


class AutogenerateEmptyCommentsTest(AutogenFixtureTest, TestBase):
    """test that an empty string comment is treated the same as no comment,
    as most backends don't store them distinctly"""

    __backend__ = True

    __requires__ = ("comments",)

    @testing.combinations(
        ("", ""), (None, ""), ("", None), argnames="conn_comment,md_comment"
    )
    def test_column_empty_comment_no_change(self, conn_comment, md_comment):
        m1 = MetaData()
        m2 = MetaData()

        Table("some_table", m1, Column("amount", Float, comment=conn_comment))
        Table("some_table", m2, Column("amount", Float, comment=md_comment))

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    @testing.combinations(
        ("", ""), (None, ""), ("", None), argnames="conn_comment,md_comment"
    )
    def test_table_empty_comment_no_change(self, conn_comment, md_comment):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("test", String(10), primary_key=True),
            comment=conn_comment,
        )
        Table(
            "some_table",
            m2,
            Column("test", String(10), primary_key=True),
            comment=md_comment,
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_column_empty_to_nonempty_comment(self):
        m1 = MetaData()
        m2 = MetaData()

        Table("some_table", m1, Column("amount", Float, comment=""))
        Table("some_table", m2, Column("amount", Float, comment="the amount"))

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0][0], "modify_comment")
        eq_(diffs[0][0][5], None)
        eq_(diffs[0][0][6], "the amount")

    def test_column_nonempty_to_empty_comment(self):
        m1 = MetaData()
        m2 = MetaData()

        Table("some_table", m1, Column("amount", Float, comment="the amount"))
        Table("some_table", m2, Column("amount", Float, comment=""))

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0][0], "modify_comment")
        eq_(diffs[0][0][5], "the amount")
        eq_(diffs[0][0][6], None)

    def test_table_empty_to_nonempty_comment(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("test", String(10), primary_key=True),
            comment="",
        )
        Table(
            "some_table",
            m2,
            Column("test", String(10), primary_key=True),
            comment="this is some table",
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table_comment")
        eq_(diffs[0][1].comment, "this is some table")
        eq_(diffs[0][2], None)

    def test_table_nonempty_to_empty_comment(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("test", String(10), primary_key=True),
            comment="this is some table",
        )
        Table(
            "some_table",
            m2,
            Column("test", String(10), primary_key=True),
            comment="",
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "remove_table_comment")
        eq_(diffs[0][1].comment, None)
