import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table

from alembic.testing import eq_
from alembic.testing import TestBase
from ._autogen_fixtures import AutogenFixtureTest


class AutogenerateComputedNoBackendTest(AutogenFixtureTest, TestBase):
    __requires__ = ("sa_computed_column",)

    def test_add_computed_column(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "user", m1, Column("id", Integer, primary_key=True),
        )

        Table(
            "user",
            m2,
            Column("id", Integer, primary_key=True),
            Column("foo", Integer, sa.Computed("5")),
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_column")
        eq_(diffs[0][2], "user")
        eq_(diffs[0][3].name, "foo")
        c = diffs[0][3].computed

        assert isinstance(c, sa.Computed)
        assert c.persisted is None
        eq_(str(c.sqltext), "5")

