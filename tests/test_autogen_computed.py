import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table

from alembic.testing import eq_
from alembic.testing import exclusions
from alembic.testing import TestBase
from ._autogen_fixtures import AutogenFixtureTest

default_on_computed_backends = ["postgresql", "oracle"]
default_on_computed_reason = (
    "sqlalchemy on %s detects a computed column "
    "as a normal server default during inspection"
) % (", ".join(default_on_computed_backends))


class AutogenerateComputedTest(AutogenFixtureTest, TestBase):
    __requires__ = ("sa_computed_column", "db_computed_columns")
    __backend__ = True

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

    def _test_remove_computed_column(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "user",
            m1,
            Column("id", Integer, primary_key=True),
            Column("foo", Integer, sa.Computed("5")),
        )

        Table(
            "user", m2, Column("id", Integer, primary_key=True),
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "remove_column")
        eq_(diffs[0][2], "user")
        c = diffs[0][3]
        eq_(c.name, "foo")

        assert c.computed is None
        return c

    @exclusions.skip_if(
        default_on_computed_backends, default_on_computed_reason
    )
    def test_remove_computed_column(self):
        column = self._test_remove_computed_column()
        assert column.server_default is None

    @exclusions.only_if(
        default_on_computed_backends, default_on_computed_reason
    )
    def test_remove_computed_column_default_on_computed(self):
        column = self._test_remove_computed_column()
        assert isinstance(column.server_default, sa.DefaultClause)
        eq_(str(column.server_default.arg.text), "5")

    def _test_computed_unchanged(self, argBefore, argAfter):
        # no combination until sqlalchemy 1.3.7
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "user",
            m1,
            Column("id", Integer, primary_key=True),
            Column("bar", Integer),
            Column("foo", Integer, *argBefore),
        )

        Table(
            "user",
            m2,
            Column("id", Integer, primary_key=True),
            Column("bar", Integer),
            Column("foo", Integer, *argAfter),
        )

        diffs = self._fixture(m1, m2)

        eq_(len(diffs), 0)

    def test_unchanged_same_text(self):
        self._test_computed_unchanged([sa.Computed("5")], [sa.Computed("5")])

    def test_unchanged_same_text_column(self):
        self._test_computed_unchanged(
            [sa.Computed("bar*5")], [sa.Computed("bar*5")]
        )

    def test_unchanged_change_expression(self):
        self._test_computed_unchanged(
            [sa.Computed("bar*5")], [sa.Computed("bar * 42")]
        )

    def test_unchanged_change_persisted(self):
        self._test_computed_unchanged(
            [sa.Computed("bar*5")], [sa.Computed("bar * 42", persisted=True)]
        )

    def test_unchanged_add_computed(self):
        self._test_computed_unchanged([], [sa.Computed("bar*5")])

    @exclusions.skip_if(
        default_on_computed_backends, default_on_computed_reason
    )
    def test_unchanged_remove_computed(self):
        self._test_computed_unchanged([sa.Computed("bar*5")], [])

    @exclusions.only_if(
        default_on_computed_backends, default_on_computed_reason
    )
    def test_remove_computed_default_on_computed(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "user",
            m1,
            Column("id", Integer, primary_key=True),
            Column("bar", Integer),
            Column("foo", Integer, sa.Computed("bar+42")),
        )

        Table(
            "user",
            m2,
            Column("id", Integer, primary_key=True),
            Column("bar", Integer),
            Column("foo", Integer),
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0][0], "modify_default")
        eq_(diffs[0][0][2], "user")
        eq_(diffs[0][0][3], "foo")
        old = diffs[0][0][-2]
        new = diffs[0][0][-1]

        assert new is None
        assert isinstance(old, sa.DefaultClause)
        eq_(str(old.arg.text), "(bar + 42)")
