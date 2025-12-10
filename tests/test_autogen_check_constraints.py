from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table

from alembic.testing import assert_raises_message
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import is_true
from alembic.testing import TestBase
from alembic.testing.suite._autogen_fixtures import AutogenFixtureTest


class AutogenerateCheckConstraintsTest(AutogenFixtureTest, TestBase):
    __backend__ = True
    __only_on__ = "postgresql"

    def test_add_check_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
        )

        Table(
            "some_table",
            m2,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
            CheckConstraint("value > 0", name="ck_value_positive"),
        )

        diffs = self._fixture(m1, m2, opts={"compare_check_constraints": True})

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "ck_value_positive")

    def test_remove_check_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
            CheckConstraint("value > 0", name="ck_value_positive"),
        )

        Table(
            "some_table",
            m2,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
        )

        diffs = self._fixture(m1, m2, opts={"compare_check_constraints": True})

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "remove_constraint")
        eq_(diffs[0][1].name, "ck_value_positive")

    def test_no_change_when_constraint_matches(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
            CheckConstraint("value > 0", name="ck_value_positive"),
        )

        Table(
            "some_table",
            m2,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
            CheckConstraint("value > 0", name="ck_value_positive"),
        )

        diffs = self._fixture(m1, m2, opts={"compare_check_constraints": True})

        eq_(len(diffs), 0)

    def test_no_diff_when_compare_check_constraints_false(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
        )

        Table(
            "some_table",
            m2,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
            CheckConstraint("value > 0", name="ck_value_positive"),
        )

        diffs = self._fixture(
            m1, m2, opts={"compare_check_constraints": False}
        )

        eq_(len(diffs), 0)

    def test_unnamed_constraint_raises(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
        )

        Table(
            "some_table",
            m2,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
            CheckConstraint("value > 0"),
        )

        assert_raises_message(
            ValueError,
            r"Unnamed check constraint on table 'some_table' cannot be compared",
            self._fixture,
            m1,
            m2,
            opts={"compare_check_constraints": True},
        )

    def test_multiple_constraints(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
            Column("status", String(20)),
            CheckConstraint("value > 0", name="ck_value_positive"),
        )

        Table(
            "some_table",
            m2,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
            Column("status", String(20)),
            CheckConstraint("value >= 0", name="ck_value_non_negative"),
            CheckConstraint("status IS NOT NULL", name="ck_status_not_null"),
        )

        diffs = self._fixture(m1, m2, opts={"compare_check_constraints": True})

        eq_(len(diffs), 3)

        diff_types = {(d[0], d[1].name) for d in diffs}
        eq_(
            diff_types,
            {
                ("remove_constraint", "ck_value_positive"),
                ("add_constraint", "ck_value_non_negative"),
                ("add_constraint", "ck_status_not_null"),
            },
        )

    def test_enum_type_bound_constraint_ignored(self):
        import enum

        class Status(enum.Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("id", Integer, primary_key=True),
            Column(
                "status",
                Enum(Status, name="status_enum", create_constraint=True),
            ),
        )

        Table(
            "some_table",
            m2,
            Column("id", Integer, primary_key=True),
            Column(
                "status",
                Enum(Status, name="status_enum", create_constraint=True),
            ),
        )

        diffs = self._fixture(m1, m2, opts={"compare_check_constraints": True})

        enum_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(len(enum_diffs), 0)

    def test_constraint_with_bound_parameter(self):
        import sqlalchemy as sa

        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("id", Integer, primary_key=True),
            Column("source", String(50)),
        )

        source_col = sa.column("source")
        Table(
            "some_table",
            m2,
            Column("id", Integer, primary_key=True),
            Column("source", String(50)),
            CheckConstraint(
                source_col == "MANUAL",
                name="ck_source_manual",
            ),
        )

        diffs = self._fixture(m1, m2, opts={"compare_check_constraints": True})

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "ck_source_manual")

    def test_constraint_name_with_spaces_raises(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
        )

        Table(
            "some_table",
            m2,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
            CheckConstraint("value > 0", name="invalid name with spaces"),
        )

        assert_raises_message(
            ValueError,
            r"Check constraint name 'invalid name with spaces' on table "
            r"'some_table' contains invalid characters",
            self._fixture,
            m1,
            m2,
            opts={"compare_check_constraints": True},
        )

    def test_constraint_name_with_special_chars_raises(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
        )

        Table(
            "some_table",
            m2,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
            CheckConstraint("value > 0", name="invalid-name-with-dashes"),
        )

        assert_raises_message(
            ValueError,
            r"Check constraint name 'invalid-name-with-dashes' on table "
            r"'some_table' contains invalid characters",
            self._fixture,
            m1,
            m2,
            opts={"compare_check_constraints": True},
        )
