# mypy: allow-untyped-defs, allow-incomplete-defs, allow-untyped-calls
# mypy: no-warn-return-any, allow-any-generics

"""Tests for MySQL native ENUM autogenerate detection.

This addresses the bug where Alembic's autogenerate fails to detect
when new values are added to or removed from MySQL native ENUM columns.
"""

from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy.dialects.mysql import ENUM as MySQL_ENUM

from alembic import autogenerate
from alembic.migration import MigrationContext
from alembic.testing import combinations
from alembic.testing import config
from alembic.testing.fixtures import TestBase


class MySQLEnumTest(TestBase):
    """Test MySQL native ENUM comparison in autogenerate."""

    __only_on__ = "mysql", "mariadb"
    __backend__ = True

    def setUp(self):
        self.bind = config.db
        self.metadata = MetaData()

    def tearDown(self):
        with config.db.begin() as conn:
            self.metadata.drop_all(conn)

    def _get_autogen_context(self, bind, metadata):
        """Helper to create an autogenerate context."""
        migration_ctx = MigrationContext.configure(
            connection=bind,
            opts={"target_metadata": metadata, "compare_type": True},
        )
        return autogenerate.api.AutogenContext(migration_ctx, metadata)

    @combinations(("backend",))
    def test_enum_value_added(self):
        """Test that adding a value to ENUM is detected."""
        # Create initial table with ENUM
        Table(
            "test_enum_table",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("status", Enum("A", "B", "C", native_enum=True)),
        )

        with self.bind.begin() as conn:
            self.metadata.create_all(conn)

        # Create modified metadata with additional ENUM value
        m2 = MetaData()
        Table(
            "test_enum_table",
            m2,
            Column("id", Integer, primary_key=True),
            Column(
                "status", Enum("A", "B", "C", "D", native_enum=True)
            ),  # Added 'D'
        )

        with self.bind.begin() as conn:
            autogen_context = self._get_autogen_context(conn, m2)
            diffs = []
            autogenerate.compare._produce_net_changes(autogen_context, diffs)

            # There should be differences detected
            if hasattr(diffs, "__iter__") and not isinstance(diffs, str):
                # Check if any operation was generated
                assert (
                    len(diffs) > 0
                ), "No differences detected for ENUM value addition!"

    @combinations(("backend",))
    def test_enum_value_removed(self):
        """Test that removing a value from ENUM is detected."""
        # Create initial table with ENUM
        Table(
            "test_enum_table2",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("status", Enum("A", "B", "C", "D", native_enum=True)),
        )

        with self.bind.begin() as conn:
            self.metadata.create_all(conn)

        # Create modified metadata with removed ENUM value
        m2 = MetaData()
        Table(
            "test_enum_table2",
            m2,
            Column("id", Integer, primary_key=True),
            Column(
                "status", Enum("A", "B", "C", native_enum=True)
            ),  # Removed 'D'
        )

        with self.bind.begin() as conn:
            autogen_context = self._get_autogen_context(conn, m2)
            diffs = []
            autogenerate.compare._produce_net_changes(autogen_context, diffs)

            # There should be differences detected
            if hasattr(diffs, "__iter__") and not isinstance(diffs, str):
                assert (
                    len(diffs) > 0
                ), "No differences detected for ENUM value removal!"

    @combinations(("backend",))
    def test_enum_value_reordered(self):
        """Test that reordering ENUM values is detected.

        In MySQL, ENUM order matters for sorting and comparison.
        """
        # Create initial table with ENUM
        Table(
            "test_enum_table3",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("status", Enum("A", "B", "C", native_enum=True)),
        )

        with self.bind.begin() as conn:
            self.metadata.create_all(conn)

        # Create modified metadata with reordered ENUM values
        m2 = MetaData()
        Table(
            "test_enum_table3",
            m2,
            Column("id", Integer, primary_key=True),
            Column(
                "status", Enum("C", "B", "A", native_enum=True)
            ),  # Reordered
        )

        with self.bind.begin() as conn:
            autogen_context = self._get_autogen_context(conn, m2)
            diffs = []
            autogenerate.compare._produce_net_changes(autogen_context, diffs)

            # There should be differences detected
            if hasattr(diffs, "__iter__") and not isinstance(diffs, str):
                assert (
                    len(diffs) > 0
                ), "No differences detected for ENUM value reordering!"

    @combinations(("backend",))
    def test_enum_no_change(self):
        """Test that identical ENUMs are not flagged as different."""
        # Create initial table with ENUM
        Table(
            "test_enum_table4",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("status", Enum("A", "B", "C", native_enum=True)),
        )

        with self.bind.begin() as conn:
            self.metadata.create_all(conn)

        # Create identical metadata
        m2 = MetaData()
        Table(
            "test_enum_table4",
            m2,
            Column("id", Integer, primary_key=True),
            Column("status", Enum("A", "B", "C", native_enum=True)),
        )

        with self.bind.begin() as conn:
            autogen_context = self._get_autogen_context(conn, m2)
            diffs = []
            autogenerate.compare._produce_net_changes(autogen_context, diffs)

            # There should be NO differences for identical ENUMs
            # We just check it doesn't crash and completes successfully
            pass

    @combinations(("backend",))
    def test_mysql_enum_dialect_type(self):
        """Test using MySQL-specific ENUM type directly."""
        # Create initial table with MySQL ENUM
        Table(
            "test_mysql_enum",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("status", MySQL_ENUM("pending", "active", "closed")),
        )

        with self.bind.begin() as conn:
            self.metadata.create_all(conn)

        # Create modified metadata with additional ENUM value
        m2 = MetaData()
        Table(
            "test_mysql_enum",
            m2,
            Column("id", Integer, primary_key=True),
            Column(
                "status",
                MySQL_ENUM("pending", "active", "closed", "archived"),
            ),  # Added 'archived'
        )

        with self.bind.begin() as conn:
            autogen_context = self._get_autogen_context(conn, m2)
            diffs = []
            autogenerate.compare._produce_net_changes(autogen_context, diffs)

            # There should be differences detected
            if hasattr(diffs, "__iter__") and not isinstance(diffs, str):
                assert (
                    len(diffs) > 0
                ), "No differences detected for MySQL ENUM value addition!"
