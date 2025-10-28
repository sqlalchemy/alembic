from contextlib import nullcontext
import itertools

from sqlalchemy import Column
from sqlalchemy import Float
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
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.sql.expression import asc
from sqlalchemy.sql.expression import column
from sqlalchemy.sql.expression import desc
from sqlalchemy.sql.expression import nullsfirst
from sqlalchemy.sql.expression import nullslast

from alembic import testing
from alembic.testing import combinations
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import exclusions
from alembic.testing import resolve_lambda
from alembic.testing import schemacompare
from alembic.testing import TestBase
from alembic.testing import util
from alembic.testing.assertions import expect_warnings
from alembic.testing.env import staging_env
from alembic.testing.suite._autogen_fixtures import AutogenFixtureTest
from alembic.util import sqla_compat


class NoUqReflection:
    """mixin used to simulate dialects where unique constraints are
    not reflected."""

    __requires__ = ()

    reports_unique_constraints = False

    def setUp(self):
        staging_env()
        self.bind = eng = util.testing_engine()

        def unimpl(*arg, **kw):
            raise NotImplementedError()

        eng.dialect.get_unique_constraints = unimpl


class AutogenerateUniqueIndexTest(AutogenFixtureTest, TestBase):
    """tests that involve unique constraint reflection, or the lack of
    this feature and the expected behaviors, and its interaction with index
    reflection.

    Tests that do not involve unique constraint reflection, but involve
    indexes, should go into AutogenerateIndexTest.

    """

    __backend__ = True

    @property
    def reports_unique_constraints(self):
        return config.requirements.unique_constraint_reflection.enabled

    @property
    def reports_unique_constraints_as_indexes(self):
        return (
            config.requirements.reports_unique_constraints_as_indexes.enabled
        )

    @property
    def reports_unnamed_constraints(self):
        return config.requirements.reports_unnamed_constraints.enabled

    def test_index_flag_becomes_named_unique_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "user",
            m1,
            Column("id", Integer, primary_key=True),
            Column("name", String(50), nullable=False, index=True),
            Column("a1", String(10), server_default="x"),
        )

        Table(
            "user",
            m2,
            Column("id", Integer, primary_key=True),
            Column("name", String(50), nullable=False),
            Column("a1", String(10), server_default="x"),
            UniqueConstraint("name", name="uq_user_name"),
        )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            eq_(diffs[0][0], "remove_index")
            eq_(diffs[0][1].name, "ix_user_name")

            eq_(diffs[1][0], "add_constraint")
            eq_(diffs[1][1].name, "uq_user_name")

        else:
            eq_(diffs[0][0], "remove_index")
            eq_(diffs[0][1].name, "ix_user_name")

    def test_add_unique_constraint(self):
        m1 = MetaData()
        m2 = MetaData()
        Table(
            "address",
            m1,
            Column("id", Integer, primary_key=True),
            Column("email_address", String(100), nullable=False),
            Column("qpr", String(10), index=True),
        )
        Table(
            "address",
            m2,
            Column("id", Integer, primary_key=True),
            Column("email_address", String(100), nullable=False),
            Column("qpr", String(10), index=True),
            UniqueConstraint("email_address", name="uq_email_address"),
        )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            eq_(diffs[0][0], "add_constraint")
            eq_(diffs[0][1].name, "uq_email_address")
        else:
            eq_(diffs, [])

    def test_unique_flag_nothing_changed(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "unq_idx",
            m1,
            Column("id", Integer, primary_key=True),
            Column("x", String(20)),
            Index("x", "x", unique=True),
        )

        Table(
            "unq_idx",
            m2,
            Column("id", Integer, primary_key=True),
            Column("x", String(20)),
            Index("x", "x", unique=True),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_index_becomes_unique(self):
        m1 = MetaData()
        m2 = MetaData()
        Table(
            "order",
            m1,
            Column("order_id", Integer, primary_key=True),
            Column("amount", Numeric(10, 2), nullable=True),
            Column("user_id", Integer),
            UniqueConstraint(
                "order_id", "user_id", name="order_order_id_user_id_unique"
            ),
            Index("order_user_id_amount_idx", "user_id", "amount"),
        )

        Table(
            "order",
            m2,
            Column("order_id", Integer, primary_key=True),
            Column("amount", Numeric(10, 2), nullable=True),
            Column("user_id", Integer),
            UniqueConstraint(
                "order_id", "user_id", name="order_order_id_user_id_unique"
            ),
            Index(
                "order_user_id_amount_idx", "user_id", "amount", unique=True
            ),
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
        Table(
            "item",
            m1,
            Column("x", Integer),
            UniqueConstraint("x", name="db_generated_name"),
        )

        # test mismatch between unique=True and
        # named uq constraint
        Table("item", m2, Column("x", Integer, unique=True))

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_named_cols_changed(self):
        m1 = MetaData()
        m2 = MetaData()
        Table(
            "col_change",
            m1,
            Column("x", Integer),
            Column("y", Integer),
            UniqueConstraint("x", name="nochange"),
        )
        Table(
            "col_change",
            m2,
            Column("x", Integer),
            Column("y", Integer),
            UniqueConstraint("x", "y", name="nochange"),
        )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            eq_(diffs[0][0], "remove_constraint")
            eq_(diffs[0][1].name, "nochange")

            eq_(diffs[1][0], "add_constraint")
            eq_(diffs[1][1].name, "nochange")
        else:
            eq_(diffs, [])

    def test_nothing_changed_one(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "nothing_changed",
            m1,
            Column("x", String(20), unique=True, index=True),
        )

        Table(
            "nothing_changed",
            m2,
            Column("x", String(20), unique=True, index=True),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_nothing_changed_implicit_uq_w_naming_conv(self):
        m1 = MetaData(
            naming_convention={
                "ix": "ix_%(column_0_label)s",
                "uq": "uq_%(column_0_label)s",
            }
        )
        m2 = MetaData(
            naming_convention={
                "ix": "ix_%(column_0_label)s",
                "uq": "uq_%(column_0_label)s",
            }
        )

        Table(
            "nothing_changed",
            m1,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("x", String(20), unique=True),
            mysql_engine="InnoDB",
        )

        Table(
            "nothing_changed",
            m2,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("x", String(20), unique=True),
            mysql_engine="InnoDB",
        )
        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_nothing_uq_changed_labels_were_truncated(self):
        m1 = MetaData(
            naming_convention={
                "ix": "index_%(table_name)s_%(column_0_label)s",
                "uq": "unique_%(table_name)s_%(column_0_label)s",
            }
        )
        m2 = MetaData(
            naming_convention={
                "ix": "index_%(table_name)s_%(column_0_label)s",
                "uq": "unique_%(table_name)s_%(column_0_label)s",
            }
        )

        Table(
            "nothing_changed",
            m1,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("a_long_name", String(20), unique=True),
            mysql_engine="InnoDB",
        )

        Table(
            "nothing_changed",
            m2,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("a_long_name", String(20), unique=True),
            mysql_engine="InnoDB",
        )
        diffs = self._fixture(m1, m2, max_identifier_length=30)
        eq_(diffs, [])

    @config.requirements.long_names
    def test_nothing_changed_uq_w_mixed_case_nconv_name(self):
        m1 = MetaData(
            naming_convention={
                "ix": "index_%(table_name)s_%(column_0_label)s",
                "uq": "unique_%(table_name)s_%(column_0_label)s",
            }
        )
        m2 = MetaData(
            naming_convention={
                "ix": "index_%(table_name)s_%(column_0_label)s",
                "uq": "unique_%(table_name)s_%(column_0_label)s",
            }
        )

        Table(
            "NothingChanged",
            m1,
            Column("id", Integer, primary_key=True),
            Column("XCol", Integer),
            UniqueConstraint("XCol"),
            mysql_engine="InnoDB",
        )

        Table(
            "NothingChanged",
            m2,
            Column("id", Integer, primary_key=True),
            Column("XCol", Integer),
            UniqueConstraint("XCol"),
            mysql_engine="InnoDB",
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_nothing_changed_uq_w_mixed_case_plain_name(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "nothing_changed",
            m1,
            Column("id", Integer, primary_key=True),
            Column("x", Integer),
            UniqueConstraint("x", name="SomeConstraint"),
            mysql_engine="InnoDB",
        )

        Table(
            "nothing_changed",
            m2,
            Column("id", Integer, primary_key=True),
            Column("x", Integer),
            UniqueConstraint("x", name="SomeConstraint"),
            mysql_engine="InnoDB",
        )
        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_nothing_changed_two(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "nothing_changed",
            m1,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("x", String(20), unique=True),
            mysql_engine="InnoDB",
        )
        Table(
            "nothing_changed_related",
            m1,
            Column("id1", Integer),
            Column("id2", Integer),
            ForeignKeyConstraint(
                ["id1", "id2"], ["nothing_changed.id1", "nothing_changed.id2"]
            ),
            mysql_engine="InnoDB",
        )

        Table(
            "nothing_changed",
            m2,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("x", String(20), unique=True),
            mysql_engine="InnoDB",
        )
        Table(
            "nothing_changed_related",
            m2,
            Column("id1", Integer),
            Column("id2", Integer),
            ForeignKeyConstraint(
                ["id1", "id2"], ["nothing_changed.id1", "nothing_changed.id2"]
            ),
            mysql_engine="InnoDB",
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_nothing_changed_unique_w_colkeys(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "nothing_changed",
            m1,
            Column("x", String(20), key="nx"),
            UniqueConstraint("nx"),
        )

        Table(
            "nothing_changed",
            m2,
            Column("x", String(20), key="nx"),
            UniqueConstraint("nx"),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    @config.requirements.unique_constraint_reflection
    def test_nothing_changed_cols_unsorted(self):
        """test #1240


        MySQL doubles unique constraints as indexes, so we need to make
        sure we aren't comparing index sigs to unique constraint sigs,
        which we were doing previously by mistake.  As their signatures
        were compatible, things "worked" but once index sigs changed
        col name sorting order, it broke.

        """

        m1 = MetaData()
        m2 = MetaData()

        Table(
            "nothing_changed",
            m1,
            Column("id", Integer, primary_key=True),
            Column("sid", Integer, nullable=False),
            Column("label", String(30), nullable=False),
            Column("fid", Integer, nullable=False),
            UniqueConstraint("sid", "label"),
            UniqueConstraint("sid", "fid"),
        )

        Table(
            "nothing_changed",
            m2,
            Column("id", Integer, primary_key=True),
            Column("sid", Integer, nullable=False),
            Column("label", String(30), nullable=False),
            Column("fid", Integer, nullable=False),
            UniqueConstraint("sid", "label"),
            UniqueConstraint("sid", "fid"),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    @config.requirements.unique_constraint_reflection
    @config.requirements.reports_unnamed_constraints
    def test_remove_uq_constraint(self):
        """supplementary test for codepath in #1240"""

        m1 = MetaData()
        m2 = MetaData()

        Table(
            "something_changed",
            m1,
            Column("id", Integer, primary_key=True),
            Column("sid", Integer, nullable=False),
            Column("label", String(30), nullable=False),
            Column("fid", Integer, nullable=False),
            UniqueConstraint("sid", "label"),
            UniqueConstraint("sid", "fid"),
        )

        Table(
            "something_changed",
            m2,
            Column("id", Integer, primary_key=True),
            Column("sid", Integer, nullable=False),
            Column("label", String(30), nullable=False),
            Column("fid", Integer, nullable=False),
            UniqueConstraint("sid", "fid"),
        )

        diffs = self._fixture(m1, m2)
        assert len(diffs) == 1
        assert diffs[0][0] in ("remove_index", "remove_constraint")

    @config.requirements.unique_constraint_reflection
    def test_uq_casing_convention_changed_so_put_drops_first(self):
        m1 = MetaData()
        m2 = MetaData()

        uq1 = UniqueConstraint("x", name="SomeCasingConvention")
        Table(
            "new_idx",
            m1,
            Column("id1", Integer, primary_key=True),
            Column("x", String(20)),
            uq1,
        )

        uq2 = UniqueConstraint("x", name="somecasingconvention")
        Table(
            "new_idx",
            m2,
            Column("id1", Integer, primary_key=True),
            Column("x", String(20)),
            uq2,
        )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints_as_indexes:
            eq_(
                [(d[0], d[1].name) for d in diffs],
                [
                    ("remove_index", "SomeCasingConvention"),
                    ("add_constraint", "somecasingconvention"),
                ],
            )
        else:
            eq_(
                [(d[0], d[1].name) for d in diffs],
                [
                    ("remove_constraint", "SomeCasingConvention"),
                    ("add_constraint", "somecasingconvention"),
                ],
            )

    def test_drop_table_w_uq_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "some_table",
            m1,
            Column("id", Integer, primary_key=True),
            Column("x", String(20)),
            Column("y", String(20)),
            UniqueConstraint("y", name="uq_y"),
        )

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints_as_indexes:
            # for MySQL this UQ will look like an index, so
            # make sure it at least sets it up correctly
            eq_(diffs[0][0], "remove_index")
            eq_(diffs[1][0], "remove_table")
            eq_(len(diffs), 2)

            constraints = [
                c
                for c in diffs[1][1].constraints
                if isinstance(c, UniqueConstraint)
            ]
            eq_(len(constraints), 0)
        else:
            eq_(diffs[0][0], "remove_table")
            eq_(len(diffs), 1)
            constraints = [
                c
                for c in diffs[0][1].constraints
                if isinstance(c, UniqueConstraint)
            ]
            if self.reports_unique_constraints:
                eq_(len(constraints), 1)

    @config.requirements.unique_constraint_reflection
    def test_unnamed_cols_changed(self):
        m1 = MetaData()
        m2 = MetaData()
        Table(
            "col_change",
            m1,
            Column("x", Integer),
            Column("y", Integer),
            UniqueConstraint("x"),
        )
        Table(
            "col_change",
            m2,
            Column("x", Integer),
            Column("y", Integer),
            UniqueConstraint("x", "y"),
        )

        diffs = self._fixture(m1, m2)

        diffs = {
            (
                cmd,
                (
                    isinstance(obj, (UniqueConstraint, Index))
                    if obj.name is not None
                    else False
                ),
            )
            for cmd, obj in diffs
        }

        if self.reports_unnamed_constraints:
            if self.reports_unique_constraints_as_indexes:
                eq_(
                    diffs,
                    {("remove_index", True), ("add_constraint", False)},
                )
            else:
                eq_(
                    diffs,
                    {
                        ("remove_constraint", True),
                        ("add_constraint", False),
                    },
                )

    def test_remove_named_unique_index(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "remove_idx",
            m1,
            Column("x", Integer),
            Index("xidx", "x", unique=True),
        )
        Table("remove_idx", m2, Column("x", Integer))

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            diffs = {(cmd, obj.name) for cmd, obj in diffs}
            eq_(diffs, {("remove_index", "xidx")})
        else:
            eq_(diffs, [])

    def test_remove_named_unique_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "remove_idx",
            m1,
            Column("x", Integer),
            UniqueConstraint("x", name="xidx"),
        )
        Table("remove_idx", m2, Column("x", Integer))

        diffs = self._fixture(m1, m2)

        if self.reports_unique_constraints:
            diffs = {(cmd, obj.name) for cmd, obj in diffs}
            if self.reports_unique_constraints_as_indexes:
                eq_(diffs, {("remove_index", "xidx")})
            else:
                eq_(diffs, {("remove_constraint", "xidx")})
        else:
            eq_(diffs, [])

    def test_dont_add_uq_on_table_create(self):
        m1 = MetaData()
        m2 = MetaData()
        Table("no_uq", m2, Column("x", String(50), unique=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 1)

        # checking for dupes also
        eq_(
            sorted(
                [type(cons) for cons in diffs[0][1].constraints],
                key=lambda c: c.__name__,
            ),
            [PrimaryKeyConstraint, UniqueConstraint],
        )

    @config.requirements.reflects_unique_constraints_unambiguously
    def test_dont_add_uq_on_reverse_table_drop(self):
        m1 = MetaData()
        m2 = MetaData()
        Table("no_uq", m1, Column("x", String(50), unique=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "remove_table")
        eq_(len(diffs), 1)

        # because the drop comes from reflection, the "unique=True" flag
        # is lost in any case.
        eq_(
            sorted(
                [type(cons) for cons in diffs[0][1].constraints],
                key=lambda c: c.__name__,
            ),
            [PrimaryKeyConstraint, UniqueConstraint],
        )

    def test_add_uq_ix_on_table_create(self):
        m1 = MetaData()
        m2 = MetaData()
        Table("add_ix", m2, Column("x", String(50), unique=True, index=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 2)
        assert UniqueConstraint not in {
            type(c) for c in diffs[0][1].constraints
        }

        eq_(diffs[1][0], "add_index")
        d_table = diffs[0][1]
        d_idx = diffs[1][1]
        eq_(d_idx.unique, True)

        # check for dupes
        eq_(len(diffs), 2)
        assert not d_table.indexes


class AutogenerateIndexTest(AutogenFixtureTest, TestBase):
    """tests involving indexes but not unique constraints, as mssql
    doesn't have these (?)...at least the dialect seems to not
    reflect unique constraints which seems odd

    """

    __backend__ = True

    def test_nothing_changed_one(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "nothing_changed",
            m1,
            Column("x", String(20), index=True),
        )

        Table(
            "nothing_changed",
            m2,
            Column("x", String(20), index=True),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    @config.requirements.long_names
    def test_nothing_ix_changed_labels_were_truncated(self):
        m1 = MetaData(
            naming_convention={
                "ix": "index_%(table_name)s_%(column_0_label)s",
                "uq": "unique_%(table_name)s_%(column_0_label)s",
            }
        )
        m2 = MetaData(
            naming_convention={
                "ix": "index_%(table_name)s_%(column_0_label)s",
                "uq": "unique_%(table_name)s_%(column_0_label)s",
            }
        )

        Table(
            "nothing_changed",
            m1,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("a_particularly_long_column_name", String(20), index=True),
            mysql_engine="InnoDB",
        )

        Table(
            "nothing_changed",
            m2,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("a_particularly_long_column_name", String(20), index=True),
            mysql_engine="InnoDB",
        )
        diffs = self._fixture(m1, m2, max_identifier_length=30)
        eq_(diffs, [])

    def test_nothing_changed_ix_w_mixed_case_plain_name(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "nothing_changed",
            m1,
            Column("id", Integer, primary_key=True),
            Column("x", Integer),
            Index("SomeIndex", "x"),
            mysql_engine="InnoDB",
        )

        Table(
            "nothing_changed",
            m2,
            Column("id", Integer, primary_key=True),
            Column("x", Integer),
            Index("SomeIndex", "x"),
            mysql_engine="InnoDB",
        )
        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    @config.requirements.long_names
    def test_nothing_changed_ix_w_mixed_case_nconv_name(self):
        m1 = MetaData(
            naming_convention={
                "ix": "index_%(table_name)s_%(column_0_label)s",
                "uq": "unique_%(table_name)s_%(column_0_label)s",
            }
        )
        m2 = MetaData(
            naming_convention={
                "ix": "index_%(table_name)s_%(column_0_label)s",
                "uq": "unique_%(table_name)s_%(column_0_label)s",
            }
        )

        Table(
            "NothingChanged",
            m1,
            Column("id", Integer, primary_key=True),
            Column("XCol", Integer, index=True),
            mysql_engine="InnoDB",
        )

        Table(
            "NothingChanged",
            m2,
            Column("id", Integer, primary_key=True),
            Column("XCol", Integer, index=True),
            mysql_engine="InnoDB",
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_new_table_added(self):
        m1 = MetaData()
        m2 = MetaData()
        Table(
            "extra",
            m2,
            Column("foo", Integer, index=True),
            Column("bar", Integer),
            Index("newtable_idx", "bar"),
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")

        eq_(diffs[1][0], "add_index")
        eq_(
            sqla_compat._get_constraint_final_name(
                diffs[1][1], config.db.dialect
            ),
            "ix_extra_foo",
        )

        eq_(diffs[2][0], "add_index")
        eq_(diffs[2][1].name, "newtable_idx")

    def test_nothing_changed_index_w_colkeys(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "nothing_changed",
            m1,
            Column("x", String(20), key="nx"),
            Index("foobar", "nx"),
        )

        Table(
            "nothing_changed",
            m2,
            Column("x", String(20), key="nx"),
            Index("foobar", "nx"),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_nothing_changed_index_named_as_column(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "nothing_changed",
            m1,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("x", String(20)),
            Index("x", "x"),
        )

        Table(
            "nothing_changed",
            m2,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("x", String(20)),
            Index("x", "x"),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_nothing_changed_implicit_fk_index_named(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "nothing_changed",
            m1,
            Column("id", Integer, primary_key=True),
            Column(
                "other_id",
                ForeignKey("nc2.id", name="fk_my_table_other_table"),
                nullable=False,
            ),
            Column("foo", Integer),
            mysql_engine="InnoDB",
        )
        Table(
            "nc2",
            m1,
            Column("id", Integer, primary_key=True),
            mysql_engine="InnoDB",
        )

        Table(
            "nothing_changed",
            m2,
            Column("id", Integer, primary_key=True),
            Column(
                "other_id",
                ForeignKey("nc2.id", name="fk_my_table_other_table"),
                nullable=False,
            ),
            Column("foo", Integer),
            mysql_engine="InnoDB",
        )
        Table(
            "nc2",
            m2,
            Column("id", Integer, primary_key=True),
            mysql_engine="InnoDB",
        )
        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_nothing_changed_implicit_composite_fk_index_named(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "nothing_changed",
            m1,
            Column("id", Integer, primary_key=True),
            Column("other_id_1", Integer),
            Column("other_id_2", Integer),
            Column("foo", Integer),
            ForeignKeyConstraint(
                ["other_id_1", "other_id_2"],
                ["nc2.id1", "nc2.id2"],
                name="fk_my_table_other_table",
            ),
            mysql_engine="InnoDB",
        )
        Table(
            "nc2",
            m1,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            mysql_engine="InnoDB",
        )

        Table(
            "nothing_changed",
            m2,
            Column("id", Integer, primary_key=True),
            Column("other_id_1", Integer),
            Column("other_id_2", Integer),
            Column("foo", Integer),
            ForeignKeyConstraint(
                ["other_id_1", "other_id_2"],
                ["nc2.id1", "nc2.id2"],
                name="fk_my_table_other_table",
            ),
            mysql_engine="InnoDB",
        )
        Table(
            "nc2",
            m2,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            mysql_engine="InnoDB",
        )
        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_ix_casing_convention_changed_so_put_drops_first(self):
        m1 = MetaData()
        m2 = MetaData()

        ix1 = Index("SomeCasingConvention", "x")
        Table(
            "new_idx",
            m1,
            Column("id1", Integer, primary_key=True),
            Column("x", String(20)),
            ix1,
        )

        ix2 = Index("somecasingconvention", "x")
        Table(
            "new_idx",
            m2,
            Column("id1", Integer, primary_key=True),
            Column("x", String(20)),
            ix2,
        )

        diffs = self._fixture(m1, m2)

        eq_(
            [(d[0], d[1].name) for d in diffs],
            [
                ("remove_index", "SomeCasingConvention"),
                ("add_index", "somecasingconvention"),
            ],
        )

    def test_new_idx_index_named_as_column(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "new_idx",
            m1,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("x", String(20)),
        )

        idx = Index("x", "x")
        Table(
            "new_idx",
            m2,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("x", String(20)),
            idx,
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [("add_index", schemacompare.CompareIndex(idx))])

    @exclusions.fails_on(["mysql", "mariadb"])
    def test_removed_idx_index_named_as_column(self):
        m1 = MetaData()
        m2 = MetaData()

        idx = Index("x", "x")
        Table(
            "new_idx",
            m1,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("x", String(20)),
            idx,
        )

        Table(
            "new_idx",
            m2,
            Column("id1", Integer, primary_key=True),
            Column("id2", Integer, primary_key=True),
            Column("x", String(20)),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs[0][0], "remove_index")

    def test_drop_table_w_indexes(self):
        m1 = MetaData()
        m2 = MetaData()

        t = Table(
            "some_table",
            m1,
            Column("id", Integer, primary_key=True),
            Column("x", String(20)),
            Column("y", String(20)),
        )
        Index("xy_idx", t.c.x, t.c.y)
        Index("y_idx", t.c.y)

        diffs = self._fixture(m1, m2)
        eq_(diffs[0][0], "remove_index")
        eq_(diffs[1][0], "remove_index")
        eq_(diffs[2][0], "remove_table")

        eq_({diffs[0][1].name, diffs[1][1].name}, {"xy_idx", "y_idx"})

    def test_add_ix_on_table_create(self):
        m1 = MetaData()
        m2 = MetaData()
        Table("add_ix", m2, Column("x", String(50), index=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_table")
        eq_(len(diffs), 2)
        assert UniqueConstraint not in {
            type(c) for c in diffs[0][1].constraints
        }
        eq_(diffs[1][0], "add_index")
        eq_(diffs[1][1].unique, False)

    def test_add_idx_non_col(self):
        m1 = MetaData()
        m2 = MetaData()
        Table("add_ix", m1, Column("x", String(50)))
        t2 = Table("add_ix", m2, Column("x", String(50)))
        Index("foo_idx", t2.c.x.desc())
        diffs = self._fixture(m1, m2)

        eq_(diffs[0][0], "add_index")

    @config.requirements.reflects_indexes_w_sorting
    def test_idx_string_col_in_fn_no_change(self):
        """test #880"""
        m1 = MetaData()
        m2 = MetaData()
        t1 = Table("add_ix", m1, Column("x", String(50)))
        t1.append_constraint(Index("foo_idx", desc(column("x"))))

        t2 = Table("add_ix", m2, Column("x", String(50)))
        t2.append_constraint(Index("foo_idx", desc(column("x"))))
        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    @config.requirements.reflects_indexes_w_sorting
    def test_unchanged_idx_non_col(self):
        m1 = MetaData()
        m2 = MetaData()
        t1 = Table("add_ix", m1, Column("x", String(50)))
        Index("foo_idx", t1.c.x.desc())
        t2 = Table("add_ix", m2, Column("x", String(50)))
        Index("foo_idx", t2.c.x.desc())
        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_unchanged_case_sensitive_implicit_idx(self):
        m1 = MetaData()
        m2 = MetaData()
        Table("add_ix", m1, Column("regNumber", String(50), index=True))
        Table("add_ix", m2, Column("regNumber", String(50), index=True))
        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_unchanged_case_sensitive_explicit_idx(self):
        m1 = MetaData()
        m2 = MetaData()
        t1 = Table("add_ix", m1, Column("reg_number", String(50)))
        Index("regNumber_idx", t1.c.reg_number)
        t2 = Table("add_ix", m2, Column("reg_number", String(50)))
        Index("regNumber_idx", t2.c.reg_number)

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    @config.requirements.covering_indexes
    def test_nothing_changed_covering_index(self):
        m1 = MetaData()
        m2 = MetaData()

        cov_opt = {f"{config.db.name}_include": ["y"]}

        Table(
            "nothing_changed",
            m1,
            Column("id", Integer, primary_key=True),
            Column("x", Integer),
            Column("y", Integer),
            Index("SomeIndex", "x", **cov_opt),
        )

        Table(
            "nothing_changed",
            m2,
            Column("id", Integer, primary_key=True),
            Column("x", Integer),
            Column("y", Integer),
            Index("SomeIndex", "x", **cov_opt),
        )
        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_column_order_changed(self):
        m1 = MetaData()
        m2 = MetaData()

        old = Index("SomeIndex", "x", "y")
        Table(
            "order_change",
            m1,
            Column("id", Integer, primary_key=True),
            Column("x", Integer),
            Column("y", Integer),
            old,
        )

        new = Index("SomeIndex", "y", "x")
        Table(
            "order_change",
            m2,
            Column("id", Integer, primary_key=True),
            Column("x", Integer),
            Column("y", Integer),
            new,
        )
        diffs = self._fixture(m1, m2)
        eq_(
            diffs,
            [
                ("remove_index", schemacompare.CompareIndex(old)),
                ("add_index", schemacompare.CompareIndex(new)),
            ],
        )

    @config.requirements.reflects_indexes_column_sorting
    @testing.combinations(
        (desc, asc),
        (asc, desc),
        (desc, lambda x: nullslast(desc(x))),
        (nullslast, nullsfirst),
        (nullsfirst, nullslast),
        (lambda x: nullslast(desc(x)), lambda x: nullsfirst(asc(x))),
    )
    def test_column_sort_changed(self, old_fn, new_fn):
        m1 = MetaData()
        m2 = MetaData()

        old = Index("SomeIndex", old_fn("y"))
        Table("order_change", m1, Column("y", Integer), old)

        new = Index("SomeIndex", new_fn("y"))
        Table("order_change", m2, Column("y", Integer), new)
        diffs = self._fixture(m1, m2)
        eq_(
            diffs,
            [
                (
                    "remove_index",
                    schemacompare.CompareIndex(old, name_only=True),
                ),
                ("add_index", schemacompare.CompareIndex(new, name_only=True)),
            ],
        )

    @config.requirements.reflects_indexes_column_sorting
    @testing.combinations(
        (asc, asc),
        (desc, desc),
        (nullslast, nullslast),
        (nullsfirst, nullsfirst),
        (lambda x: x, asc),
        (lambda x: x, nullslast),
        (desc, lambda x: nullsfirst(desc(x))),
        (lambda x: nullslast(asc(x)), lambda x: x),
    )
    def test_column_sort_not_changed(self, old_fn, new_fn):
        m1 = MetaData()
        m2 = MetaData()

        old = Index("SomeIndex", old_fn("y"))
        Table("order_change", m1, Column("y", Integer), old)

        new = Index("SomeIndex", new_fn("y"))
        Table("order_change", m2, Column("y", Integer), new)
        diffs = self._fixture(m1, m2)
        eq_(diffs, [])


def _lots_of_indexes(flatten: bool = False):
    diff_pairs = [
        (
            lambda t: Index("idx", "y", func.lower(t.c.x)),
            lambda t: Index("idx", func.lower(t.c.x)),
        ),
        (
            lambda CapT: Index("idx", "y", func.lower(CapT.c.XCol)),
            lambda CapT: Index("idx", func.lower(CapT.c.XCol)),
        ),
        (
            lambda t: Index("idx", "y", func.lower(column("x")), _table=t),
            lambda t: Index("idx", func.lower(column("x")), _table=t),
        ),
        (
            lambda t: Index("idx", t.c.y, func.lower(t.c.x)),
            lambda t: Index("idx", func.lower(t.c.x), t.c.y),
        ),
        (
            lambda t: Index("idx", t.c.y, func.lower(t.c.x)),
            lambda t: Index("idx", t.c.y, func.lower(t.c.q)),
        ),
        (
            lambda t: Index("idx", t.c.z, func.lower(t.c.x)),
            lambda t: Index("idx", t.c.y, func.lower(t.c.x)),
        ),
        (
            lambda t: Index("idx", func.lower(t.c.x)),
            lambda t: Index("idx", t.c.y, func.lower(t.c.x)),
        ),
        (
            lambda t: Index("idx", t.c.y, func.upper(t.c.x)),
            lambda t: Index("idx", t.c.y, func.lower(t.c.x)),
        ),
        (
            lambda t: Index("idx", t.c.y, t.c.ff + 1),
            lambda t: Index("idx", t.c.y, t.c.ff + 3),
        ),
        (
            lambda t: Index("idx", t.c.y, func.lower(t.c.x)),
            lambda t: Index("idx", t.c.y, func.lower(t.c.x + t.c.q)),
        ),
        (
            lambda t: Index("idx", t.c.y, t.c.z + 3),
            lambda t: Index("idx", t.c.y, t.c.z * 3),
        ),
        (
            lambda t: Index("idx", func.lower(t.c.x), t.c.q + "42"),
            lambda t: Index("idx", func.lower(t.c.q), t.c.x + "42"),
        ),
        (
            lambda t: Index("idx", func.lower(t.c.x), t.c.z + 42),
            lambda t: Index("idx", t.c.z + 42, func.lower(t.c.q)),
        ),
        (
            lambda t: Index("idx", t.c.ff + 42),
            lambda t: Index("idx", 42 + t.c.ff),
        ),
        (
            lambda t: Index("idx", text("coalesce(z, -1)"), _table=t),
            lambda t: Index("idx", text("coalesce(q, '-1')"), _table=t),
        ),
        (
            lambda t: Index("idx", t.c.y.cast(Integer)),
            lambda t: Index("idx", t.c.x.cast(Integer)),
        ),
    ]

    with_sort = [
        (
            lambda t: Index("idx", "y", func.lower(t.c.x)),
            lambda t: Index("idx", "y", desc(func.lower(t.c.x))),
        ),
        (
            lambda t: Index("idx", "y", func.lower(t.c.x)),
            lambda t: Index("idx", desc("y"), func.lower(t.c.x)),
        ),
        (
            lambda t: Index("idx", "y", func.lower(t.c.x)),
            lambda t: Index("idx", "y", nullsfirst(func.lower(t.c.x))),
        ),
        (
            lambda t: Index("idx", "y", func.lower(t.c.x)),
            lambda t: Index("idx", nullsfirst("y"), func.lower(t.c.x)),
        ),
        (
            lambda t: Index("idx", asc(func.lower(t.c.x))),
            lambda t: Index("idx", desc(func.lower(t.c.x))),
        ),
        (
            lambda t: Index("idx", desc(func.lower(t.c.x))),
            lambda t: Index("idx", asc(func.lower(t.c.x))),
        ),
        (
            lambda t: Index("idx", nullslast(asc(func.lower(t.c.x)))),
            lambda t: Index("idx", nullslast(desc(func.lower(t.c.x)))),
        ),
        (
            lambda t: Index("idx", nullslast(desc(func.lower(t.c.x)))),
            lambda t: Index("idx", nullsfirst(desc(func.lower(t.c.x)))),
        ),
        (
            lambda t: Index("idx", nullsfirst(func.lower(t.c.x))),
            lambda t: Index("idx", desc(func.lower(t.c.x))),
        ),
        (
            lambda t: Index(
                "idx", text("x nulls first"), text("lower(y)"), _table=t
            ),
            lambda t: Index(
                "idx", text("x nulls last"), text("lower(y)"), _table=t
            ),
        ),
        (
            lambda t: Index(
                "idx", text("x nulls last"), text("lower(y)"), _table=t
            ),
            lambda t: Index(
                "idx", text("x nulls first"), text("lower(y)"), _table=t
            ),
        ),
        (
            lambda t: Index(
                "idx", text("x nulls first"), text("lower(y)"), _table=t
            ),
            lambda t: Index(
                "idx", text("y nulls first"), text("lower(x)"), _table=t
            ),
        ),
        (
            lambda t: Index(
                "idx", text("x nulls last"), text("lower(y)"), _table=t
            ),
            lambda t: Index(
                "idx", text("y nulls last"), text("lower(x)"), _table=t
            ),
        ),
    ]

    req = config.requirements.reflects_indexes_column_sorting

    if flatten:
        flat = list(itertools.chain.from_iterable(diff_pairs))
        for f1, f2 in with_sort:
            flat.extend([(f1, req), (f2, req)])
        return flat
    else:
        return diff_pairs + [(f1, f2, req) for f1, f2 in with_sort]


def _lost_of_equal_indexes(_lots_of_indexes):
    equal_pairs = [
        (fn, fn) if not isinstance(fn, tuple) else (fn[0], fn[0], fn[1])
        for fn in _lots_of_indexes(flatten=True)
    ]

    equal_pairs += [
        (
            lambda t: Index("idx", "y", func.lower(t.c.x)),
            lambda t: Index("idx", "y", asc(func.lower(t.c.x))),
            config.requirements.reflects_indexes_column_sorting,
        ),
        (
            lambda t: Index("idx", "y", func.lower(t.c.x)),
            lambda t: Index("idx", "y", nullslast(func.lower(t.c.x))),
            config.requirements.reflects_indexes_column_sorting,
        ),
        (
            lambda t: Index("idx", "y", func.lower(t.c.x)),
            lambda t: Index("idx", "y", nullslast(asc(func.lower(t.c.x)))),
            config.requirements.reflects_indexes_column_sorting,
        ),
        (
            lambda t: Index("idx", "y", desc(func.lower(t.c.x))),
            lambda t: Index("idx", "y", nullsfirst(desc(func.lower(t.c.x)))),
            config.requirements.reflects_indexes_column_sorting,
        ),
    ]

    # textual_sorting
    equal_pairs += [
        (
            # use eval to avoid resolve lambda complaining about the closure
            eval(f'lambda t: Index("idx", text({conn!r}), _table=t)'),
            eval(f'lambda t: Index("idx", text({meta!r}), _table=t)'),
            config.requirements.reflects_indexes_column_sorting,
        )
        for meta, conn in (
            ("z nulls first", "z nulls first"),
            ("z nulls last", "z"),
            ("z asc", "z"),
            ("z asc nulls first", "z nulls first"),
            ("z asc nulls last", "z"),
            ("z desc", "z desc"),
            ("z desc nulls first", "z desc"),
            ("z desc nulls last", "z desc nulls last"),
        )
    ]

    return equal_pairs


class AutogenerateExpressionIndexTest(AutogenFixtureTest, TestBase):
    """tests involving indexes with expression"""

    __requires__ = ("indexes_with_expressions",)

    __backend__ = True

    @property
    def has_reflection(self):
        return config.requirements.reflect_indexes_with_expressions.enabled

    def test_expression_indexes_add(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "exp_index",
            m1,
            Column("id", Integer, primary_key=True),
            Column("x", Integer),
            Column("y", Integer),
        )

        idx = Index("SomeIndex", "y", func.lower(column("x")))  # noqa
        Table(
            "exp_index",
            m2,
            Column("id", Integer, primary_key=True),
            Column("x", Integer),
            Column("y", Integer),
            idx,
        )

        if self.has_reflection:
            diffs = self._fixture(m1, m2)
            eq_(diffs, [("add_index", schemacompare.CompareIndex(idx))])
        else:
            with expect_warnings(
                r"autogenerate skipping metadata-specified expression-based "
                r"index 'SomeIndex'; dialect '.*' under SQLAlchemy .* "
                r"can't reflect these "
                r"indexes so they can't be compared",
            ):
                diffs = self._fixture(m1, m2)
            eq_(diffs, [])

    @testing.fixture
    def index_changed_tables(self):
        m1 = MetaData()
        m2 = MetaData()

        t_old = Table(
            "exp_index",
            m1,
            Column("id", Integer, primary_key=True),
            Column("x", String(100)),
            Column("y", String(100)),
            Column("q", String(100)),
            Column("z", Integer),
            Column("ff", Float().with_variant(DOUBLE_PRECISION, "postgresql")),
        )

        t_new = Table(
            "exp_index",
            m2,
            Column("id", Integer, primary_key=True),
            Column("x", String(100)),
            Column("y", String(100)),
            Column("q", String(100)),
            Column("z", Integer),
            Column("ff", Float().with_variant(DOUBLE_PRECISION, "postgresql")),
        )

        CapT_old = Table(
            "CapT table",
            m1,
            Column("id", Integer, primary_key=True),
            Column("XCol", String(100)),
            Column("y", String(100)),
        )

        CapT_new = Table(
            "CapT table",
            m2,
            Column("id", Integer, primary_key=True),
            Column("XCol", String(100)),
            Column("y", String(100)),
        )

        return (
            m1,
            m2,
            {"t": t_old, "CapT": CapT_old},
            {"t": t_new, "CapT": CapT_new},
        )

    @combinations(*_lots_of_indexes(), argnames="old_fn, new_fn")
    def test_expression_indexes_changed(
        self, index_changed_tables, old_fn, new_fn
    ):
        m1, m2, old_fixture_tables, new_fixture_tables = index_changed_tables

        old = resolve_lambda(old_fn, **old_fixture_tables)
        new = resolve_lambda(new_fn, **new_fixture_tables)

        if self.has_reflection:
            diffs = self._fixture(m1, m2)
            eq_(
                diffs,
                [
                    ("remove_index", schemacompare.CompareIndex(old, True)),
                    ("add_index", schemacompare.CompareIndex(new)),
                ],
            )
        else:
            with expect_warnings(
                r"Skipped unsupported reflection of expression-based index "
                r"idx",
                r"autogenerate skipping metadata-specified expression-based "
                r"index 'idx'; dialect '.*' under SQLAlchemy .* "
                r"can't reflect these "
                r"indexes so they can't be compared",
            ):
                diffs = self._fixture(m1, m2)
            eq_(diffs, [])

    @combinations(
        *_lost_of_equal_indexes(_lots_of_indexes), argnames="fn1, fn2"
    )
    def test_expression_indexes_no_change(
        self, index_changed_tables, fn1, fn2
    ):
        m1, m2, old_fixture_tables, new_fixture_tables = index_changed_tables

        resolve_lambda(fn1, **old_fixture_tables)
        resolve_lambda(fn2, **new_fixture_tables)

        if self.has_reflection:
            ctx = nullcontext()
        else:
            ctx = expect_warnings()

        with ctx:
            diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_expression_indexes_remove(self):
        m1 = MetaData()
        m2 = MetaData()

        idx = Index("SomeIndex", "y", func.lower(column("x")))
        Table(
            "exp_index",
            m1,
            Column("id", Integer, primary_key=True),
            Column("x", String(100)),
            Column("y", Integer),
            idx,
        )

        Table(
            "exp_index",
            m2,
            Column("id", Integer, primary_key=True),
            Column("x", String(100)),
            Column("y", Integer),
        )

        if self.has_reflection:
            diffs = self._fixture(m1, m2)
            eq_(
                diffs,
                [("remove_index", schemacompare.CompareIndex(idx, True))],
            )
        else:
            with expect_warnings():
                diffs = self._fixture(m1, m2)
            eq_(diffs, [])


class NoUqReflectionIndexTest(NoUqReflection, AutogenerateUniqueIndexTest):
    __only_on__ = "sqlite"

    def test_uq_casing_convention_changed_so_put_drops_first(self):
        config.skip_test(
            "unique constraint reflection disabled for this suite"
        )

    def test_dont_add_uq_on_reverse_table_drop(self):
        config.skip_test(
            "unique constraint reflection disabled for this suite"
        )

    def test_unique_not_reported(self):
        m1 = MetaData()
        Table(
            "order",
            m1,
            Column("order_id", Integer, primary_key=True),
            Column("amount", Numeric(10, 2), nullable=True),
            Column("user_id", Integer),
            UniqueConstraint(
                "order_id", "user_id", name="order_order_id_user_id_unique"
            ),
        )

        diffs = self._fixture(m1, m1)
        eq_(diffs, [])

    def test_remove_unique_index_not_reported(self):
        m1 = MetaData()
        Table(
            "order",
            m1,
            Column("order_id", Integer, primary_key=True),
            Column("amount", Numeric(10, 2), nullable=True),
            Column("user_id", Integer),
            Index("oid_ix", "order_id", "user_id", unique=True),
        )
        m2 = MetaData()
        Table(
            "order",
            m2,
            Column("order_id", Integer, primary_key=True),
            Column("amount", Numeric(10, 2), nullable=True),
            Column("user_id", Integer),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs, [])

    def test_remove_plain_index_is_reported(self):
        m1 = MetaData()
        Table(
            "order",
            m1,
            Column("order_id", Integer, primary_key=True),
            Column("amount", Numeric(10, 2), nullable=True),
            Column("user_id", Integer),
            Index("oid_ix", "order_id", "user_id"),
        )
        m2 = MetaData()
        Table(
            "order",
            m2,
            Column("order_id", Integer, primary_key=True),
            Column("amount", Numeric(10, 2), nullable=True),
            Column("user_id", Integer),
        )

        diffs = self._fixture(m1, m2)
        eq_(diffs[0][0], "remove_index")


class NoUqReportsIndAsUqTest(NoUqReflectionIndexTest):
    """this test suite simulates the condition where:

    a. the dialect doesn't report unique constraints

    b. the dialect returns unique constraints within the indexes list.

    Currently the mssql dialect does this, but here we force this
    condition so that we can test the behavior regardless of if/when
    mssql supports unique constraint reflection.

    """

    __only_on__ = "sqlite"

    @classmethod
    def _get_bind(cls):
        eng = config.db

        _get_unique_constraints = eng.dialect.get_unique_constraints
        _get_indexes = eng.dialect.get_indexes

        def unimpl(*arg, **kw):
            raise NotImplementedError()

        def get_indexes(self, connection, tablename, **kw):
            indexes = _get_indexes(self, connection, tablename, **kw)
            for uq in _get_unique_constraints(
                self, connection, tablename, **kw
            ):
                uq["unique"] = True
                indexes.append(uq)
            return indexes

        eng.dialect.get_unique_constraints = unimpl
        eng.dialect.get_indexes = get_indexes
        return eng


class IncludeHooksTest(AutogenFixtureTest, TestBase):
    __backend__ = True

    @combinations(("name",), ("object",))
    def test_remove_connection_index(self, hook_type):
        m1 = MetaData()
        m2 = MetaData()

        t1 = Table("t", m1, Column("x", Integer), Column("y", Integer))
        Index("ix1", t1.c.x)
        Index("ix2", t1.c.y)

        Table("t", m2, Column("x", Integer), Column("y", Integer))

        if hook_type == "object":

            def include_object(object_, name, type_, reflected, compare_to):
                if type_ == "unique_constraint":
                    return False
                return not (
                    isinstance(object_, Index)
                    and type_ == "index"
                    and reflected
                    and name == "ix1"
                )

            diffs = self._fixture(m1, m2, object_filters=include_object)
        elif hook_type == "name":
            all_names = set()

            def include_name(name, type_, parent_names):
                all_names.add((name, type_))
                if name == "ix1":
                    eq_(type_, "index")
                    eq_(
                        parent_names,
                        {
                            "table_name": "t",
                            "schema_name": None,
                            "schema_qualified_table_name": "t",
                        },
                    )
                    return False
                else:
                    return True

            diffs = self._fixture(m1, m2, name_filters=include_name)
            eq_(
                all_names,
                {
                    ("ix1", "index"),
                    ("ix2", "index"),
                    ("y", "column"),
                    ("t", "table"),
                    (None, "schema"),
                    ("x", "column"),
                },
            )

        eq_(diffs[0][0], "remove_index")
        eq_(diffs[0][1].name, "ix2")
        eq_(len(diffs), 1)

    @combinations(("name",), ("object",))
    @config.requirements.unique_constraint_reflection
    @config.requirements.reflects_unique_constraints_unambiguously
    def test_remove_connection_uq(self, hook_type):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            Column("y", Integer),
            UniqueConstraint("x", name="uq1"),
            UniqueConstraint("y", name="uq2"),
        )

        Table("t", m2, Column("x", Integer), Column("y", Integer))

        if hook_type == "object":

            def include_object(object_, name, type_, reflected, compare_to):
                if type_ == "index":
                    return False
                return not (
                    isinstance(object_, UniqueConstraint)
                    and type_ == "unique_constraint"
                    and reflected
                    and name == "uq1"
                )

            diffs = self._fixture(m1, m2, object_filters=include_object)
        elif hook_type == "name":
            all_names = set()

            def include_name(name, type_, parent_names):
                if type_ == "index":
                    return False  # PostgreSQL thing

                all_names.add((name, type_))

                if name == "uq1":
                    eq_(type_, "unique_constraint")
                    eq_(
                        parent_names,
                        {
                            "table_name": "t",
                            "schema_name": None,
                            "schema_qualified_table_name": "t",
                        },
                    )
                    return False
                return True

            diffs = self._fixture(m1, m2, name_filters=include_name)
            eq_(
                all_names,
                {
                    ("t", "table"),
                    (None, "schema"),
                    ("uq2", "unique_constraint"),
                    ("x", "column"),
                    ("y", "column"),
                    ("uq1", "unique_constraint"),
                },
            )

        eq_(diffs[0][0], "remove_constraint")
        eq_(diffs[0][1].name, "uq2")
        eq_(len(diffs), 1)

    def test_add_metadata_index(self):
        m1 = MetaData()
        m2 = MetaData()

        Table("t", m1, Column("x", Integer))

        t2 = Table("t", m2, Column("x", Integer))
        Index("ix1", t2.c.x)
        Index("ix2", t2.c.x)

        def include_object(object_, name, type_, reflected, compare_to):
            return not (
                isinstance(object_, Index)
                and type_ == "index"
                and not reflected
                and name == "ix1"
            )

        diffs = self._fixture(m1, m2, object_filters=include_object)

        eq_(diffs[0][0], "add_index")
        eq_(diffs[0][1].name, "ix2")
        eq_(len(diffs), 1)

    @config.requirements.unique_constraint_reflection
    def test_add_metadata_unique(self):
        m1 = MetaData()
        m2 = MetaData()

        Table("t", m1, Column("x", Integer))

        Table(
            "t",
            m2,
            Column("x", Integer),
            UniqueConstraint("x", name="uq1"),
            UniqueConstraint("x", name="uq2"),
        )

        def include_object(object_, name, type_, reflected, compare_to):
            return not (
                isinstance(object_, UniqueConstraint)
                and type_ == "unique_constraint"
                and not reflected
                and name == "uq1"
            )

        diffs = self._fixture(m1, m2, object_filters=include_object)

        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "uq2")
        eq_(len(diffs), 1)

    def test_change_index(self):
        m1 = MetaData()
        m2 = MetaData()

        t1 = Table(
            "t",
            m1,
            Column("x", Integer),
            Column("y", Integer),
            Column("z", Integer),
        )
        Index("ix1", t1.c.x)
        Index("ix2", t1.c.y)

        t2 = Table(
            "t",
            m2,
            Column("x", Integer),
            Column("y", Integer),
            Column("z", Integer),
        )
        Index("ix1", t2.c.x, t2.c.y)
        Index("ix2", t2.c.x, t2.c.z)

        def include_object(object_, name, type_, reflected, compare_to):
            return not (
                isinstance(object_, Index)
                and type_ == "index"
                and not reflected
                and name == "ix1"
                and isinstance(compare_to, Index)
            )

        diffs = self._fixture(m1, m2, object_filters=include_object)

        eq_(diffs[0][0], "remove_index")
        eq_(diffs[0][1].name, "ix2")
        eq_(diffs[1][0], "add_index")
        eq_(diffs[1][1].name, "ix2")
        eq_(len(diffs), 2)

    @config.requirements.unique_constraint_reflection
    def test_change_unique(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            Column("y", Integer),
            Column("z", Integer),
            UniqueConstraint("x", name="uq1"),
            UniqueConstraint("y", name="uq2"),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            Column("y", Integer),
            Column("z", Integer),
            UniqueConstraint("x", "z", name="uq1"),
            UniqueConstraint("y", "z", name="uq2"),
        )

        def include_object(object_, name, type_, reflected, compare_to):
            if type_ == "index":
                return False
            return not (
                isinstance(object_, UniqueConstraint)
                and type_ == "unique_constraint"
                and not reflected
                and name == "uq1"
                and isinstance(compare_to, UniqueConstraint)
            )

        diffs = self._fixture(m1, m2, object_filters=include_object)

        eq_(diffs[0][0], "remove_constraint")
        eq_(diffs[0][1].name, "uq2")
        eq_(diffs[1][0], "add_constraint")
        eq_(diffs[1][1].name, "uq2")
        eq_(len(diffs), 2)


class TruncatedIdxTest(AutogenFixtureTest, TestBase):
    def setUp(self):
        self.bind = util.testing_engine()
        self.bind.dialect.max_identifier_length = 30

    def test_idx_matches_long(self):
        from alembic.operations.base import conv

        m1 = MetaData()
        Table(
            "q",
            m1,
            Column("id", Integer, primary_key=True),
            Column("data", Integer),
            Index(
                conv("idx_q_table_this_is_more_than_thirty_characters"), "data"
            ),
        )

        diffs = self._fixture(m1, m1)
        eq_(diffs, [])
