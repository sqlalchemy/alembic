from tests import assert_compiled
from sqlalchemy.schema import Column
from sqlalchemy.types import String, Integer, DateTime
from alembic.ddl.base import AddColumn, ColumnNullable, ColumnType, ColumnName


def test_add_column():
    assert_compiled(
        AddColumn("footable", Column("foocol", String(50), nullable=False)),
        "ALTER TABLE footable ADD COLUMN foocol VARCHAR(50) NOT NULL"
    )
    assert_compiled(
        AddColumn("footable", Column("foocol", String(50), server_default="12")),
        "ALTER TABLE footable ADD COLUMN foocol VARCHAR(50) DEFAULT '12'"
    )


def test_column_nullable():
    assert_compiled(
        ColumnNullable("footable", "foocol", True),
        "ALTER TABLE footable ALTER COLUMN foocol NULL"
    )

    assert_compiled(
        ColumnNullable("footable", "foocol", False),
        "ALTER TABLE footable ALTER COLUMN foocol NOT NULL"
    )
    