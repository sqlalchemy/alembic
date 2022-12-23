from sqlalchemy import BIGINT
from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import CHAR
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DATE
from sqlalchemy import DateTime
from sqlalchemy import DECIMAL
from sqlalchemy import Enum
from sqlalchemy import FLOAT
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Index
from sqlalchemy import inspect
from sqlalchemy import INTEGER
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import LargeBinary
from sqlalchemy import MetaData
from sqlalchemy import Numeric
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import SmallInteger
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy import text
from sqlalchemy import TIMESTAMP
from sqlalchemy import TypeDecorator
from sqlalchemy import Unicode
from sqlalchemy import UniqueConstraint
from sqlalchemy import VARCHAR
from sqlalchemy.dialects import mysql
from sqlalchemy.dialects import sqlite
from sqlalchemy.types import NULLTYPE
from sqlalchemy.types import VARBINARY

from alembic import autogenerate
from alembic import testing
from alembic.autogenerate import api
from alembic.migration import MigrationContext
from alembic.operations import ops
from alembic.testing import assert_raises_message
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import is_
from alembic.testing import is_not_
from alembic.testing import mock
from alembic.testing import schemacompare
from alembic.testing import TestBase
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.suite._autogen_fixtures import _default_name_filters
from alembic.testing.suite._autogen_fixtures import _default_object_filters
from alembic.testing.suite._autogen_fixtures import AutogenFixtureTest
from alembic.testing.suite._autogen_fixtures import AutogenTest
from alembic.util import CommandError

# TODO: we should make an adaptation of CompareMetadataToInspectorTest that is
#       more well suited towards generic backends (2021-06-10)


class AutogenCrossSchemaTest(AutogenTest, TestBase):
    __only_on__ = "postgresql"
    __backend__ = True

    @classmethod
    def _get_db_schema(cls):
        m = MetaData()
        Table("t1", m, Column("x", Integer))
        Table("t2", m, Column("y", Integer), schema=config.test_schema)
        Table("t6", m, Column("u", Integer))
        Table("t7", m, Column("v", Integer), schema=config.test_schema)

        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()
        Table("t3", m, Column("q", Integer))
        Table("t4", m, Column("z", Integer), schema=config.test_schema)
        Table("t6", m, Column("u", Integer))
        Table("t7", m, Column("v", Integer), schema=config.test_schema)
        return m

    def test_default_schema_omitted_upgrade(self):
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t3"
            else:
                return True

        self._update_context(
            object_filters=include_object, include_schemas=True
        )
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        diffs = uo.as_diffs()
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, None)

    def test_default_schema_omitted_by_table_name_upgrade(self):
        def include_name(name, type_, parent_names):
            if type_ == "table":
                retval = name in ["t1", "t6"]
                if retval:
                    eq_(parent_names["schema_name"], None)
                    eq_(parent_names["schema_qualified_table_name"], name)
                else:
                    eq_(parent_names["schema_name"], config.test_schema)
                    eq_(
                        parent_names["schema_qualified_table_name"],
                        "%s.%s" % (config.test_schema, name),
                    )
                return retval
            else:
                return True

        self._update_context(name_filters=include_name, include_schemas=True)
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        diffs = uo.as_diffs()
        eq_(
            {(d[0], d[1].name) for d in diffs},
            {
                ("add_table", "t3"),
                ("add_table", "t4"),
                ("remove_table", "t1"),
                ("add_table", "t7"),
            },
        )

    def test_default_schema_omitted_by_schema_name_upgrade(self):
        def include_name(name, type_, parent_names):
            if type_ == "schema":
                assert not parent_names
                return name is None
            else:
                return True

        self._update_context(name_filters=include_name, include_schemas=True)
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        diffs = uo.as_diffs()
        eq_(
            {(d[0], d[1].name) for d in diffs},
            {
                ("add_table", "t3"),
                ("add_table", "t4"),
                ("remove_table", "t1"),
                ("add_table", "t7"),
            },
        )

    def test_alt_schema_included_upgrade(self):
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t4"
            else:
                return True

        self._update_context(
            object_filters=include_object, include_schemas=True
        )
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        diffs = uo.as_diffs()
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, config.test_schema)

    def test_alt_schema_included_by_schema_name(self):
        def include_name(name, type_, parent_names):
            if type_ == "schema":
                assert not parent_names
                return name == config.test_schema
            else:
                return True

        self._update_context(name_filters=include_name, include_schemas=True)
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        # does not include "t1" in drops because t1 is in default schema
        # includes "t6" in adds because t6 is in default schema, was omitted,
        # so reflection added it
        diffs = uo.as_diffs()
        eq_(
            {(d[0], d[1].name) for d in diffs},
            {
                ("add_table", "t3"),
                ("add_table", "t6"),
                ("add_table", "t4"),
                ("remove_table", "t2"),
            },
        )

    def test_default_schema_omitted_downgrade(self):
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t1"
            else:
                return True

        self._update_context(
            object_filters=include_object, include_schemas=True
        )
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        diffs = uo.as_diffs()
        eq_(diffs[0][0], "remove_table")
        eq_(diffs[0][1].schema, None)

    def test_alt_schema_included_downgrade(self):
        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name == "t2"
            else:
                return True

        self._update_context(
            object_filters=include_object, include_schemas=True
        )
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)
        diffs = uo.as_diffs()
        eq_(diffs[0][0], "remove_table")
        eq_(diffs[0][1].schema, config.test_schema)


class AutogenDefaultSchemaTest(AutogenFixtureTest, TestBase):
    __only_on__ = "postgresql"
    __backend__ = True

    def test_uses_explcit_schema_in_default_one(self):

        default_schema = self.bind.dialect.default_schema_name

        m1 = MetaData()
        m2 = MetaData()

        Table("a", m1, Column("x", String(50)))
        Table("a", m2, Column("x", String(50)), schema=default_schema)

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(diffs, [])

    def test_uses_explcit_schema_in_default_two(self):

        default_schema = self.bind.dialect.default_schema_name

        m1 = MetaData()
        m2 = MetaData()

        Table("a", m1, Column("x", String(50)))
        Table("a", m2, Column("x", String(50)), schema=default_schema)
        Table("a", m2, Column("y", String(50)), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, "test_schema")
        eq_(diffs[0][1].c.keys(), ["y"])

    def test_uses_explcit_schema_in_default_three(self):

        default_schema = self.bind.dialect.default_schema_name

        m1 = MetaData()
        m2 = MetaData()

        Table("a", m1, Column("y", String(50)), schema="test_schema")

        Table("a", m2, Column("x", String(50)), schema=default_schema)
        Table("a", m2, Column("y", String(50)), schema="test_schema")

        diffs = self._fixture(m1, m2, include_schemas=True)
        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].schema, default_schema)
        eq_(diffs[0][1].c.keys(), ["x"])


class AutogenDefaultSchemaIsNoneTest(AutogenFixtureTest, TestBase):
    __only_on__ = "sqlite"

    def setUp(self):
        super().setUp()

        # in SQLAlchemy 1.4, SQLite dialect is setting this name
        # to "main" as is the actual default schema name for SQLite.
        self.bind.dialect.default_schema_name = None

        # prerequisite
        eq_(self.bind.dialect.default_schema_name, None)

    def test_no_default_schema(self):

        m1 = MetaData()
        m2 = MetaData()

        Table("a", m1, Column("x", String(50)))
        Table("a", m2, Column("x", String(50)))

        def _include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name in "a" and obj.schema != "main"
            else:
                return True

        diffs = self._fixture(
            m1, m2, include_schemas=True, object_filters=_include_object
        )
        eq_(len(diffs), 0)


class ModelOne:
    __requires__ = ("unique_constraint_reflection",)

    schema = None

    @classmethod
    def _get_db_schema(cls):
        schema = cls.schema

        m = MetaData(schema=schema)

        Table(
            "user",
            m,
            Column("id", Integer, primary_key=True),
            Column("name", String(50)),
            Column("a1", Text),
            Column("pw", String(50)),
            Index("pw_idx", "pw"),
        )

        Table(
            "address",
            m,
            Column("id", Integer, primary_key=True),
            Column("email_address", String(100), nullable=False),
        )

        Table(
            "order",
            m,
            Column("order_id", Integer, primary_key=True),
            Column(
                "amount",
                Numeric(8, 2),
                nullable=False,
                server_default=text("0"),
            ),
            CheckConstraint("amount >= 0", name="ck_order_amount"),
        )

        Table(
            "extra",
            m,
            Column("x", CHAR),
            Column("uid", Integer, ForeignKey("user.id")),
        )

        return m

    @classmethod
    def _get_model_schema(cls):
        schema = cls.schema

        m = MetaData(schema=schema)

        Table(
            "user",
            m,
            Column("id", Integer, primary_key=True),
            Column("name", String(50), nullable=False),
            Column("a1", Text, server_default="x"),
        )

        Table(
            "address",
            m,
            Column("id", Integer, primary_key=True),
            Column("email_address", String(100), nullable=False),
            Column("street", String(50)),
            UniqueConstraint("email_address", name="uq_email"),
        )

        Table(
            "order",
            m,
            Column("order_id", Integer, primary_key=True),
            Column(
                "amount",
                Numeric(10, 2),
                nullable=True,
                server_default=text("0"),
            ),
            Column("user_id", Integer, ForeignKey("user.id")),
            CheckConstraint("amount > -1", name="ck_order_amount"),
        )

        Table(
            "item",
            m,
            Column("id", Integer, primary_key=True),
            Column("description", String(100)),
            Column("order_id", Integer, ForeignKey("order.order_id")),
            CheckConstraint("len(description) > 5"),
        )
        return m


class AutogenerateDiffTest(ModelOne, AutogenTest, TestBase):
    __only_on__ = "sqlite"

    def test_diffs(self):
        """test generation of diff rules"""

        metadata = self.m2
        uo = ops.UpgradeOps(ops=[])
        ctx = self.autogen_context

        autogenerate._produce_net_changes(ctx, uo)

        diffs = uo.as_diffs()
        eq_(
            diffs[0],
            ("add_table", schemacompare.CompareTable(metadata.tables["item"])),
        )

        eq_(diffs[1][0], "remove_table")
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], "add_column")
        eq_(diffs[2][1], None)
        eq_(diffs[2][2], "address")
        eq_(diffs[2][3], metadata.tables["address"].c.street)

        eq_(diffs[3][0], "add_constraint")
        eq_(diffs[3][1].name, "uq_email")

        eq_(diffs[4][0], "add_column")
        eq_(diffs[4][1], None)
        eq_(diffs[4][2], "order")
        eq_(diffs[4][3], metadata.tables["order"].c.user_id)

        eq_(diffs[5][0][0], "modify_type")
        eq_(diffs[5][0][1], None)
        eq_(diffs[5][0][2], "order")
        eq_(diffs[5][0][3], "amount")
        eq_(repr(diffs[5][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[5][0][6]), "Numeric(precision=10, scale=2)")

        self._assert_fk_diff(
            diffs[6], "add_fk", "order", ["user_id"], "user", ["id"]
        )

        eq_(diffs[7][0][0], "modify_nullable")
        eq_(diffs[7][0][5], True)
        eq_(diffs[7][0][6], False)

        eq_(diffs[8][0][0], "modify_default")
        eq_(diffs[8][0][1], None)
        eq_(diffs[8][0][2], "user")
        eq_(diffs[8][0][3], "a1")
        eq_(diffs[8][0][6].arg, "x")

        eq_(diffs[9][0], "remove_index")
        eq_(diffs[9][1].name, "pw_idx")

        eq_(diffs[10][0], "remove_column")
        eq_(diffs[10][3].name, "pw")
        eq_(diffs[10][3].table.name, "user")
        assert isinstance(diffs[10][3].type, String)

    def test_include_object(self):
        def include_object(obj, name, type_, reflected, compare_to):
            assert obj.name == name
            if type_ == "table":
                if reflected:
                    assert obj.metadata is not self.m2
                else:
                    assert obj.metadata is self.m2
                return name in ("address", "order", "user")
            elif type_ == "column":
                if reflected:
                    assert obj.table.metadata is not self.m2
                else:
                    assert obj.table.metadata is self.m2
                return name != "street"
            else:
                return True

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                "compare_type": True,
                "compare_server_default": True,
                "target_metadata": self.m2,
                "include_object": include_object,
            },
        )

        diffs = autogenerate.compare_metadata(
            context, context.opts["target_metadata"]
        )

        alter_cols = (
            {
                d[2]
                for d in self._flatten_diffs(diffs)
                if d[0].startswith("modify")
            }
            .union(
                d[3].name
                for d in self._flatten_diffs(diffs)
                if d[0] == "add_column"
            )
            .union(
                d[1].name
                for d in self._flatten_diffs(diffs)
                if d[0] == "add_table"
            )
        )
        eq_(alter_cols, {"user_id", "order", "user"})

    def test_include_name(self):
        all_names = set()

        def include_name(name, type_, parent_names):
            all_names.add((name, type_, parent_names.get("table_name", None)))
            if type_ == "table":
                eq_(
                    parent_names,
                    {"schema_name": None, "schema_qualified_table_name": name},
                )
                return name in ("address", "order", "user")
            elif type_ == "column":
                return name != "street"
            else:
                return True

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                "compare_type": True,
                "compare_server_default": True,
                "target_metadata": self.m2,
                "include_name": include_name,
            },
        )

        diffs = autogenerate.compare_metadata(
            context, context.opts["target_metadata"]
        )
        eq_(
            all_names,
            {
                (None, "schema", None),
                ("user", "table", None),
                ("id", "column", "user"),
                ("name", "column", "user"),
                ("a1", "column", "user"),
                ("pw", "column", "user"),
                ("pw_idx", "index", "user"),
                ("order", "table", None),
                ("order_id", "column", "order"),
                ("amount", "column", "order"),
                ("address", "table", None),
                ("id", "column", "address"),
                ("email_address", "column", "address"),
                ("extra", "table", None),
            },
        )

        alter_cols = (
            {
                d[2]
                for d in self._flatten_diffs(diffs)
                if d[0].startswith("modify")
            }
            .union(
                d[3].name
                for d in self._flatten_diffs(diffs)
                if d[0] == "add_column"
            )
            .union(
                d[1].name
                for d in self._flatten_diffs(diffs)
                if d[0] == "add_table"
            )
        )
        eq_(alter_cols, {"user_id", "order", "user", "street", "item"})

    def test_skip_null_type_comparison_reflected(self):
        ac = ops.AlterColumnOp("sometable", "somecol")
        autogenerate.compare._compare_type(
            self.autogen_context,
            ac,
            None,
            "sometable",
            "somecol",
            Column("somecol", NULLTYPE),
            Column("somecol", Integer()),
        )
        diff = ac.to_diff_tuple()
        assert not diff

    def test_skip_null_type_comparison_local(self):
        ac = ops.AlterColumnOp("sometable", "somecol")
        autogenerate.compare._compare_type(
            self.autogen_context,
            ac,
            None,
            "sometable",
            "somecol",
            Column("somecol", Integer()),
            Column("somecol", NULLTYPE),
        )
        diff = ac.to_diff_tuple()
        assert not diff

    def test_custom_type_compare(self):
        class MyType(TypeDecorator):
            impl = Integer

            def compare_against_backend(self, dialect, conn_type):
                return isinstance(conn_type, Integer)

        ac = ops.AlterColumnOp("sometable", "somecol")
        autogenerate.compare._compare_type(
            self.autogen_context,
            ac,
            None,
            "sometable",
            "somecol",
            Column("somecol", INTEGER()),
            Column("somecol", MyType()),
        )

        assert not ac.has_changes()

        ac = ops.AlterColumnOp("sometable", "somecol")
        autogenerate.compare._compare_type(
            self.autogen_context,
            ac,
            None,
            "sometable",
            "somecol",
            Column("somecol", String()),
            Column("somecol", MyType()),
        )
        diff = ac.to_diff_tuple()
        eq_(diff[0][0:4], ("modify_type", None, "sometable", "somecol"))

    def test_affinity_typedec(self):
        class MyType(TypeDecorator):
            impl = CHAR

            def load_dialect_impl(self, dialect):
                if dialect.name == "sqlite":
                    return dialect.type_descriptor(Integer())
                else:
                    return dialect.type_descriptor(CHAR(32))

        uo = ops.AlterColumnOp("sometable", "somecol")
        autogenerate.compare._compare_type(
            self.autogen_context,
            uo,
            None,
            "sometable",
            "somecol",
            Column("somecol", Integer, nullable=True),
            Column("somecol", MyType()),
        )
        assert not uo.has_changes()

    def test_dont_barf_on_already_reflected(self):
        from sqlalchemy.util import OrderedSet

        inspector = inspect(self.bind)
        uo = ops.UpgradeOps(ops=[])
        autogenerate.compare._compare_tables(
            OrderedSet([(None, "extra"), (None, "user")]),
            OrderedSet(),
            inspector,
            uo,
            self.autogen_context,
        )
        eq_(
            [(rec[0], rec[1].name) for rec in uo.as_diffs()],
            [
                ("remove_table", "extra"),
                ("remove_index", "pw_idx"),
                ("remove_table", "user"),
            ],
        )


class AutogenerateDiffTestWSchema(ModelOne, AutogenTest, TestBase):
    __only_on__ = "postgresql"
    __backend__ = True
    schema = "test_schema"

    def test_diffs(self):
        """test generation of diff rules"""

        metadata = self.m2

        self._update_context(include_schemas=True)
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        diffs = uo.as_diffs()

        eq_(
            diffs[0],
            (
                "add_table",
                schemacompare.CompareTable(
                    metadata.tables["%s.item" % self.schema]
                ),
            ),
        )

        eq_(diffs[1][0], "remove_table")
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], "add_column")
        eq_(diffs[2][1], self.schema)
        eq_(diffs[2][2], "address")
        eq_(
            schemacompare.CompareColumn(
                metadata.tables["%s.address" % self.schema].c.street
            ),
            diffs[2][3],
        )

        eq_(diffs[3][0], "add_constraint")
        eq_(diffs[3][1].name, "uq_email")

        eq_(diffs[4][0], "add_column")
        eq_(diffs[4][1], self.schema)
        eq_(diffs[4][2], "order")
        eq_(
            schemacompare.CompareColumn(
                metadata.tables["%s.order" % self.schema].c.user_id
            ),
            diffs[4][3],
        )

        eq_(diffs[5][0][0], "modify_type")
        eq_(diffs[5][0][1], self.schema)
        eq_(diffs[5][0][2], "order")
        eq_(diffs[5][0][3], "amount")
        eq_(repr(diffs[5][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[5][0][6]), "Numeric(precision=10, scale=2)")

        self._assert_fk_diff(
            diffs[6],
            "add_fk",
            "order",
            ["user_id"],
            "user",
            ["id"],
            source_schema=config.test_schema,
        )

        eq_(diffs[7][0][0], "modify_nullable")
        eq_(diffs[7][0][5], True)
        eq_(diffs[7][0][6], False)

        eq_(diffs[8][0][0], "modify_default")
        eq_(diffs[8][0][1], self.schema)
        eq_(diffs[8][0][2], "user")
        eq_(diffs[8][0][3], "a1")
        eq_(diffs[8][0][6].arg, "x")

        eq_(diffs[9][0], "remove_index")
        eq_(diffs[9][1].name, "pw_idx")

        eq_(diffs[10][0], "remove_column")
        eq_(diffs[10][3].name, "pw")


class CompareTypeSpecificityTest(TestBase):
    @testing.fixture
    def impl_fixture(self):
        from alembic.ddl import impl
        from sqlalchemy.engine import default

        return impl.DefaultImpl(
            default.DefaultDialect(), None, False, True, None, {}
        )

    def test_typedec_to_nonstandard(self, impl_fixture):
        class PasswordType(TypeDecorator):
            impl = VARBINARY

            def copy(self, **kw):
                return PasswordType(self.impl.length)

            def load_dialect_impl(self, dialect):
                if dialect.name == "default":
                    impl = sqlite.NUMERIC(self.length)
                else:
                    impl = VARBINARY(self.length)
                return dialect.type_descriptor(impl)

        impl_fixture.compare_type(
            Column("x", sqlite.NUMERIC(50)), Column("x", PasswordType(50))
        )

    @testing.combinations(
        (VARCHAR(30), String(30), False),
        (VARCHAR(30), String(40), True),
        (VARCHAR(30), Integer(), True),
        (VARCHAR(30), String(), False),
        (Text(), String(255), True),
        # insp + metadata types same number of
        # args but are different; they're different
        (DECIMAL(10, 5), DECIMAL(10, 6), True),
        # insp + metadata types, inspected type
        # has an additional arg; assume this is additional
        # default precision on the part of the DB, assume they are
        # equivalent
        (DECIMAL(10, 5), DECIMAL(10), False),
        # insp + metadata types, metadata type
        # has an additional arg; this can go either way, either the
        # metadata has extra precision, or the DB doesn't support the
        # element, go with consider them equivalent for now
        (DECIMAL(10), DECIMAL(10, 5), False),
        (DECIMAL(10, 2), Numeric(10), False),
        (DECIMAL(10, 5), Numeric(10, 5), False),
        (DECIMAL(10, 5), Numeric(12, 5), True),
        (DECIMAL(10, 5), DateTime(), True),
        (Numeric(), Numeric(scale=5), False),
        (INTEGER(), Integer(), False),
        (BIGINT(), Integer(), True),
        (BIGINT(), BigInteger(), False),
        (BIGINT(), SmallInteger(), True),
        (INTEGER(), SmallInteger(), True),
        (Integer(), String(), True),
        id_="ssa",
        argnames="inspected_type,metadata_type,expected",
    )
    def test_compare_type(
        self, impl_fixture, inspected_type, metadata_type, expected
    ):

        is_(
            impl_fixture.compare_type(
                Column("x", inspected_type), Column("x", metadata_type)
            ),
            expected,
        )


class CompareServerDefaultTest(TestBase):
    __backend__ = True

    @testing.fixture()
    def connection(self):
        with config.db.begin() as conn:
            yield conn

    @testing.fixture()
    def metadata(self, connection):
        m = MetaData()
        yield m
        m.drop_all(connection)

    @testing.combinations(
        (VARCHAR(30), text("'some default'"), text("'some new default'")),
        (VARCHAR(30), "some default", "some new default"),
        (VARCHAR(30), text("'//slash'"), text("'s//l//ash'")),
        (Integer(), text("15"), text("20")),
        (Integer(), "15", "20"),
        id_="sss",
        argnames="type_,default_text,new_default_text",
    )
    def test_server_default_yes_positives(
        self, type_, default_text, new_default_text, connection, metadata
    ):
        t1 = Table(
            "t1", metadata, Column("x", type_, server_default=default_text)
        )
        t1.create(connection)

        new_metadata = MetaData()
        Table(
            "t1",
            new_metadata,
            Column("x", type_, server_default=new_default_text),
        )

        mc = MigrationContext.configure(
            connection, opts={"compare_server_default": True}
        )

        diff = api.compare_metadata(mc, new_metadata)
        eq_(len(diff), 1)
        eq_(diff[0][0][0], "modify_default")

    @testing.combinations(
        (VARCHAR(30), text("'some default'")),
        (VARCHAR(30), "some default"),
        (VARCHAR(30), text("'//slash'")),
        (VARCHAR(30), text("'has '' quote'")),
        (Integer(), text("15")),
        (Integer(), "15"),
        id_="ss",
        argnames="type_,default_text",
    )
    def test_server_default_no_false_positives(
        self, type_, default_text, connection, metadata
    ):
        t1 = Table(
            "t1", metadata, Column("x", type_, server_default=default_text)
        )
        t1.create(connection)

        mc = MigrationContext.configure(
            connection, opts={"compare_server_default": True}
        )

        diff = api.compare_metadata(mc, metadata)

        assert not diff


class CompareMetadataToInspectorTest(TestBase):
    __backend__ = True

    @classmethod
    def _get_bind(cls):
        return config.db

    configure_opts = {}

    def setUp(self):
        staging_env()
        self.bind = self._get_bind()
        self.m1 = MetaData()

    def tearDown(self):
        self.m1.drop_all(self.bind)
        clear_staging_env()

    def _compare_columns(self, cola, colb):
        Table("sometable", self.m1, Column("col", cola))
        self.m1.create_all(self.bind)
        m2 = MetaData()
        Table("sometable", m2, Column("col", colb))

        ctx_opts = {
            "compare_type": True,
            "compare_server_default": True,
            "target_metadata": m2,
            "upgrade_token": "upgrades",
            "downgrade_token": "downgrades",
            "alembic_module_prefix": "op.",
            "sqlalchemy_module_prefix": "sa.",
            "include_object": _default_object_filters,
            "include_name": _default_name_filters,
        }
        if self.configure_opts:
            ctx_opts.update(self.configure_opts)
        with self.bind.connect() as conn:
            context = MigrationContext.configure(
                connection=conn, opts=ctx_opts
            )
            autogen_context = api.AutogenContext(context, m2)
            uo = ops.UpgradeOps(ops=[])
            autogenerate._produce_net_changes(autogen_context, uo)
        return bool(uo.as_diffs())

    @testing.combinations(
        (INTEGER(),),
        (CHAR(),),
        (VARCHAR(32),),
        (Text(),),
        (FLOAT(),),
        (Numeric(),),
        (DECIMAL(),),
        (TIMESTAMP(),),
        (DateTime(),),
        (Boolean(),),
        (BigInteger(),),
        (SmallInteger(),),
        (DATE(),),
        (String(32),),
        (LargeBinary(),),
        (Unicode(32),),
        (JSON(), config.requirements.json_type),
        (mysql.LONGTEXT(), config.requirements.mysql),
        (Enum("one", "two", "three", name="the_enum"),),
    )
    def test_introspected_columns_match_metadata_columns(self, cola):
        # this is ensuring false positives aren't generated for types
        # that have not changed.
        is_(self._compare_columns(cola, cola), False)

    # TODO: ideally the backend-specific types would be tested
    # within the test suites for those backends.
    @testing.combinations(
        (String(32), VARCHAR(32), False),
        (VARCHAR(6), String(6), False),
        (CHAR(), String(1), True),
        (Text(), VARCHAR(255), True),
        (Unicode(32), String(32), False, config.requirements.unicode_string),
        (Unicode(32), VARCHAR(32), False, config.requirements.unicode_string),
        (VARCHAR(6), VARCHAR(12), True),
        (VARCHAR(6), String(12), True),
        (Integer(), String(10), True),
        (String(10), Integer(), True),
        (
            Unicode(30, collation="en_US"),
            Unicode(30, collation="en_US"),
            False,  # unfortunately dialects don't seem to consistently
            # reflect collations right now so we can't test for
            # positives here
            config.requirements.postgresql,
        ),
        (
            mysql.VARCHAR(200, charset="utf8"),
            Unicode(200),
            False,
            config.requirements.mysql,
        ),
        (
            mysql.VARCHAR(200, charset="latin1"),
            mysql.VARCHAR(200, charset="utf-8"),
            True,
            config.requirements.mysql,
        ),
        (
            String(255, collation="utf8_bin"),
            String(255),
            False,
            config.requirements.mysql,
        ),
        (
            String(255, collation="utf8_bin"),
            String(255, collation="latin1_bin"),
            True,
            config.requirements.mysql,
        ),
    )
    def test_string_comparisons(self, cola, colb, expect_changes):
        is_(self._compare_columns(cola, colb), expect_changes)

    @testing.combinations(
        (
            DateTime(),
            DateTime(timezone=False),
            False,
            config.requirements.datetime_timezone,
        ),
        (
            DateTime(),
            DateTime(timezone=True),
            True,
            config.requirements.datetime_timezone,
        ),
        (
            DateTime(timezone=True),
            DateTime(timezone=False),
            True,
            config.requirements.datetime_timezone,
        ),
    )
    def test_datetime_comparisons(self, cola, colb, expect_changes):
        is_(self._compare_columns(cola, colb), expect_changes)

    @testing.combinations(
        (Integer(), Integer(), False),
        (
            Integer(),
            Numeric(8, 0),
            True,
            config.requirements.integer_subtype_comparisons,
        ),
        (Numeric(8, 0), Numeric(8, 2), True),
        (
            BigInteger(),
            Integer(),
            True,
            config.requirements.integer_subtype_comparisons,
        ),
        (
            SmallInteger(),
            Integer(),
            True,
            config.requirements.integer_subtype_comparisons,
        ),
        (  # note that the mysql.INTEGER tests only use these params
            # if the dialect is "mysql".  however we also test that their
            # dialect-agnostic representation compares by running this
            # against other dialects.
            mysql.INTEGER(unsigned=True, display_width=10),
            mysql.INTEGER(unsigned=True, display_width=10),
            False,
        ),
        (mysql.INTEGER(unsigned=True), mysql.INTEGER(unsigned=True), False),
        (
            mysql.INTEGER(unsigned=True, display_width=10),
            mysql.INTEGER(unsigned=True),
            False,
        ),
        (
            mysql.INTEGER(unsigned=True),
            mysql.INTEGER(unsigned=True, display_width=10),
            False,
        ),
    )
    def test_numeric_comparisons(self, cola, colb, expect_changes):
        is_(self._compare_columns(cola, colb), expect_changes)


class AutogenSystemColTest(AutogenTest, TestBase):
    __only_on__ = "postgresql"

    @classmethod
    def _get_db_schema(cls):
        m = MetaData()

        Table("sometable", m, Column("id", Integer, primary_key=True))
        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()

        # 'xmin' is implicitly present, when added to a model should produce
        # no change
        Table(
            "sometable",
            m,
            Column("id", Integer, primary_key=True),
            Column("xmin", Integer, system=True),
        )
        return m

    def test_dont_add_system(self):
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        diffs = uo.as_diffs()
        eq_(diffs, [])


class AutogenerateVariantCompareTest(AutogenTest, TestBase):
    __backend__ = True

    @classmethod
    def _get_db_schema(cls):
        m = MetaData()

        Table(
            "sometable",
            m,
            Column(
                "id",
                BigInteger().with_variant(Integer, "sqlite"),
                primary_key=True,
            ),
            Column("value", String(50)),
        )
        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()

        Table(
            "sometable",
            m,
            Column(
                "id",
                BigInteger().with_variant(Integer, "sqlite"),
                primary_key=True,
            ),
            Column("value", String(50)),
        )
        return m

    def test_variant_no_issue(self):
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(self.autogen_context, uo)

        diffs = uo.as_diffs()
        eq_(diffs, [])


class AutogenerateCustomCompareTypeTest(AutogenTest, TestBase):
    __only_on__ = "sqlite"

    @classmethod
    def _get_db_schema(cls):
        m = MetaData()

        Table(
            "sometable",
            m,
            Column("id", Integer, primary_key=True),
            Column("value", Integer),
        )
        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()

        Table(
            "sometable",
            m,
            Column("id", Integer, primary_key=True),
            Column("value", String),
        )
        return m

    def test_uses_custom_compare_type_function(self):
        my_compare_type = mock.Mock()
        self.context._user_compare_type = my_compare_type

        uo = ops.UpgradeOps(ops=[])

        ctx = self.autogen_context
        autogenerate._produce_net_changes(ctx, uo)

        first_table = self.m2.tables["sometable"]
        first_column = first_table.columns["id"]

        eq_(len(my_compare_type.mock_calls), 2)

        # We'll just test the first call
        _, args, _ = my_compare_type.mock_calls[0]
        (
            context,
            inspected_column,
            metadata_column,
            inspected_type,
            metadata_type,
        ) = args
        eq_(context, self.context)
        eq_(metadata_column, first_column)
        eq_(metadata_type, first_column.type)
        eq_(inspected_column.name, first_column.name)
        eq_(type(inspected_type), INTEGER)

    def test_column_type_not_modified_custom_compare_type_returns_False(self):
        my_compare_type = mock.Mock()
        my_compare_type.return_value = False
        self.context._user_compare_type = my_compare_type

        diffs = []
        ctx = self.autogen_context
        diffs = []
        autogenerate._produce_net_changes(ctx, diffs)

        eq_(diffs, [])

    def test_column_type_modified_custom_compare_type_returns_True(self):
        my_compare_type = mock.Mock()
        my_compare_type.return_value = True
        self.context._user_compare_type = my_compare_type

        ctx = self.autogen_context
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(ctx, uo)
        diffs = uo.as_diffs()

        eq_(diffs[0][0][0], "modify_type")
        eq_(diffs[1][0][0], "modify_type")


class IncludeFiltersAPITest(AutogenTest, TestBase):
    @classmethod
    def _get_db_schema(cls):
        return MetaData()

    @classmethod
    def _get_model_schema(cls):
        return MetaData()

    def test_run_name_filters_supports_extension_types(self):
        include_name = mock.Mock()

        self._update_context(name_filters=include_name, include_schemas=True)

        self.autogen_context.run_name_filters(
            name="some_function",
            type_="function",
            parent_names={"schema_name": "public"},
        )

        eq_(
            include_name.mock_calls,
            [
                mock.call(
                    "some_function", "function", {"schema_name": "public"}
                )
            ],
        )

    def test_run_object_filters_supports_extension_types(self):
        include_object = mock.Mock()

        self._update_context(
            object_filters=include_object, include_schemas=True
        )

        class ExtFunction:
            pass

        extfunc = ExtFunction()
        self.autogen_context.run_object_filters(
            object_=extfunc,
            name="some_function",
            type_="function",
            reflected=False,
            compare_to=None,
        )

        eq_(
            include_object.mock_calls,
            [mock.call(extfunc, "some_function", "function", False, None)],
        )


class PKConstraintUpgradesIgnoresNullableTest(AutogenTest, TestBase):
    __backend__ = True

    # test behavior for issue originally observed in SQLAlchemy issue #3023,
    # alembic issue #199
    @classmethod
    def _get_db_schema(cls):
        m = MetaData()

        Table(
            "person_to_role",
            m,
            Column("person_id", Integer, autoincrement=False),
            Column("role_id", Integer, autoincrement=False),
            PrimaryKeyConstraint("person_id", "role_id"),
        )
        return m

    @classmethod
    def _get_model_schema(cls):
        return cls._get_db_schema()

    def test_no_change(self):
        uo = ops.UpgradeOps(ops=[])
        ctx = self.autogen_context
        autogenerate._produce_net_changes(ctx, uo)
        diffs = uo.as_diffs()
        eq_(diffs, [])


class AutogenKeyTest(AutogenTest, TestBase):
    __only_on__ = "sqlite"

    @classmethod
    def _get_db_schema(cls):
        m = MetaData()

        Table(
            "someothertable",
            m,
            Column("id", Integer, primary_key=True),
            Column("value", Integer, key="somekey"),
        )
        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()

        Table(
            "sometable",
            m,
            Column("id", Integer, primary_key=True),
            Column("value", Integer, key="someotherkey"),
        )
        Table(
            "someothertable",
            m,
            Column("id", Integer, primary_key=True),
            Column("value", Integer, key="somekey"),
            Column("othervalue", Integer, key="otherkey"),
        )
        return m

    symbols = ["someothertable", "sometable"]

    def test_autogen(self):

        uo = ops.UpgradeOps(ops=[])

        ctx = self.autogen_context
        autogenerate._produce_net_changes(ctx, uo)
        diffs = uo.as_diffs()
        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].name, "sometable")
        eq_(diffs[1][0], "add_column")
        eq_(diffs[1][3].key, "otherkey")


class AutogenVersionTableTest(AutogenTest, TestBase):
    __only_on__ = "sqlite"
    version_table_name = "alembic_version"
    version_table_schema = None

    @classmethod
    def _get_db_schema(cls):
        m = MetaData()
        Table(
            cls.version_table_name,
            m,
            Column("x", Integer),
            schema=cls.version_table_schema,
        )
        return m

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()
        return m

    def test_no_version_table(self):
        ctx = self.autogen_context

        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(ctx, uo)
        eq_(uo.as_diffs(), [])

    def test_version_table_in_target(self):
        Table(
            self.version_table_name,
            self.m2,
            Column("x", Integer),
            schema=self.version_table_schema,
        )

        ctx = self.autogen_context
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(ctx, uo)
        eq_(uo.as_diffs(), [])


class AutogenCustomVersionTableSchemaTest(AutogenVersionTableTest):
    __only_on__ = "postgresql"
    __backend__ = True
    version_table_schema = "test_schema"
    configure_opts = {"version_table_schema": "test_schema"}


class AutogenCustomVersionTableTest(AutogenVersionTableTest):
    version_table_name = "my_version_table"
    configure_opts = {"version_table": "my_version_table"}


class AutogenCustomVersionTableAndSchemaTest(AutogenVersionTableTest):
    __only_on__ = "postgresql"
    __backend__ = True
    version_table_name = "my_version_table"
    version_table_schema = "test_schema"
    configure_opts = {
        "version_table": "my_version_table",
        "version_table_schema": "test_schema",
    }


class AutogenerateDiffOrderTest(AutogenTest, TestBase):
    __only_on__ = "sqlite"

    @classmethod
    def _get_db_schema(cls):
        return MetaData()

    @classmethod
    def _get_model_schema(cls):
        m = MetaData()
        Table("parent", m, Column("id", Integer, primary_key=True))

        Table(
            "child", m, Column("parent_id", Integer, ForeignKey("parent.id"))
        )

        return m

    def test_diffs_order(self):
        """
        Added in order to test that child tables(tables with FKs) are
        generated before their parent tables
        """

        ctx = self.autogen_context
        uo = ops.UpgradeOps(ops=[])
        autogenerate._produce_net_changes(ctx, uo)
        diffs = uo.as_diffs()

        eq_(diffs[0][0], "add_table")
        eq_(diffs[0][1].name, "parent")
        eq_(diffs[1][0], "add_table")
        eq_(diffs[1][1].name, "child")


class CompareMetadataTest(ModelOne, AutogenTest, TestBase):
    __only_on__ = "sqlite"

    def test_compare_metadata(self):
        metadata = self.m2

        diffs = autogenerate.compare_metadata(self.context, metadata)

        eq_(
            diffs[0],
            ("add_table", schemacompare.CompareTable(metadata.tables["item"])),
        )

        eq_(diffs[1][0], "remove_table")
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], "add_column")
        eq_(diffs[2][1], None)
        eq_(diffs[2][2], "address")
        eq_(diffs[2][3], metadata.tables["address"].c.street)

        eq_(diffs[3][0], "add_constraint")
        eq_(diffs[3][1].name, "uq_email")

        eq_(diffs[4][0], "add_column")
        eq_(diffs[4][1], None)
        eq_(diffs[4][2], "order")
        eq_(diffs[4][3], metadata.tables["order"].c.user_id)

        eq_(diffs[5][0][0], "modify_type")
        eq_(diffs[5][0][1], None)
        eq_(diffs[5][0][2], "order")
        eq_(diffs[5][0][3], "amount")
        eq_(repr(diffs[5][0][5]), "NUMERIC(precision=8, scale=2)")
        eq_(repr(diffs[5][0][6]), "Numeric(precision=10, scale=2)")

        self._assert_fk_diff(
            diffs[6], "add_fk", "order", ["user_id"], "user", ["id"]
        )

        eq_(diffs[7][0][0], "modify_nullable")
        eq_(diffs[7][0][5], True)
        eq_(diffs[7][0][6], False)

        eq_(diffs[8][0][0], "modify_default")
        eq_(diffs[8][0][1], None)
        eq_(diffs[8][0][2], "user")
        eq_(diffs[8][0][3], "a1")
        eq_(diffs[8][0][6].arg, "x")

        eq_(diffs[9][0], "remove_index")
        eq_(diffs[9][1].name, "pw_idx")

        eq_(diffs[10][0], "remove_column")
        eq_(diffs[10][3].name, "pw")

    def test_compare_metadata_include_object(self):
        metadata = self.m2

        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "table":
                return name in ("extra", "order")
            elif type_ == "column":
                return name != "amount"
            else:
                return True

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                "compare_type": True,
                "compare_server_default": True,
                "include_object": include_object,
            },
        )

        diffs = autogenerate.compare_metadata(context, metadata)

        eq_(diffs[0][0], "remove_table")
        eq_(diffs[0][1].name, "extra")

        eq_(diffs[1][0], "add_column")
        eq_(diffs[1][1], None)
        eq_(diffs[1][2], "order")
        eq_(diffs[1][3], metadata.tables["order"].c.user_id)

    def test_compare_metadata_include_name(self):
        metadata = self.m2

        all_names = set()

        def include_name(name, type_, parent_names):
            all_names.add((name, type_, parent_names.get("table_name", None)))
            if type_ == "table":
                return name in ("extra", "order")
            elif type_ == "column":
                return name != "amount"
            else:
                return True

        context = MigrationContext.configure(
            connection=self.bind.connect(),
            opts={
                "compare_type": True,
                "compare_server_default": True,
                "include_name": include_name,
            },
        )

        diffs = autogenerate.compare_metadata(context, metadata)
        eq_(
            all_names,
            {
                ("user", "table", None),
                ("order", "table", None),
                ("address", "table", None),
                (None, "schema", None),
                ("amount", "column", "order"),
                ("extra", "table", None),
                ("order_id", "column", "order"),
            },
        )

        eq_(
            {
                (
                    d[0],
                    d[3].name if d[0] == "add_column" else d[1].name,
                    d[2] if d[0] == "add_column" else None,
                )
                for d in diffs
            },
            {
                ("remove_table", "extra", None),
                ("add_fk", None, None),
                ("add_column", "amount", "order"),
                ("add_table", "user", None),
                ("add_table", "item", None),
                ("add_column", "user_id", "order"),
                ("add_table", "address", None),
            },
        )

    def test_compare_metadata_as_sql(self):
        context = MigrationContext.configure(
            connection=self.bind.connect(), opts={"as_sql": True}
        )
        metadata = self.m2

        assert_raises_message(
            CommandError,
            "autogenerate can't use as_sql=True as it prevents "
            "querying the database for schema information",
            autogenerate.compare_metadata,
            context,
            metadata,
        )


class PGCompareMetaData(ModelOne, AutogenTest, TestBase):
    __only_on__ = "postgresql"
    __backend__ = True
    schema = "test_schema"

    def test_compare_metadata_schema(self):
        metadata = self.m2

        context = MigrationContext.configure(
            connection=self.bind.connect(), opts={"include_schemas": True}
        )

        diffs = autogenerate.compare_metadata(context, metadata)

        eq_(
            diffs[0],
            (
                "add_table",
                schemacompare.CompareTable(
                    metadata.tables["test_schema.item"]
                ),
            ),
        )

        eq_(diffs[1][0], "remove_table")
        eq_(diffs[1][1].name, "extra")

        eq_(diffs[2][0], "add_column")
        eq_(diffs[2][1], "test_schema")
        eq_(diffs[2][2], "address")
        eq_(
            schemacompare.CompareColumn(
                metadata.tables["test_schema.address"].c.street
            ),
            diffs[2][3],
        )

        eq_(diffs[3][0], "add_constraint")
        eq_(diffs[3][1].name, "uq_email")

        eq_(diffs[4][0], "add_column")
        eq_(diffs[4][1], "test_schema")
        eq_(diffs[4][2], "order")
        eq_(
            schemacompare.CompareColumn(
                metadata.tables["test_schema.order"].c.user_id
            ),
            diffs[4][3],
        )

        eq_(diffs[5][0][0], "modify_nullable")
        eq_(diffs[5][0][5], False)
        eq_(diffs[5][0][6], True)


class OrigObjectTest(TestBase):
    def setUp(self):
        self.metadata = m = MetaData()
        t = Table(
            "t",
            m,
            Column("id", Integer(), primary_key=True),
            Column("x", Integer()),
        )
        self.ix = Index("ix1", t.c.id)
        fk = ForeignKeyConstraint(["t_id"], ["t.id"])
        q = Table("q", m, Column("t_id", Integer()), fk)
        self.table = t
        self.fk = fk
        self.ck = CheckConstraint(t.c.x > 5)
        t.append_constraint(self.ck)
        self.uq = UniqueConstraint(q.c.t_id)
        self.pk = t.primary_key

    def test_drop_fk(self):
        fk = self.fk
        op = ops.DropConstraintOp.from_constraint(fk)
        eq_(op.to_constraint(), schemacompare.CompareForeignKey(fk))
        eq_(op.reverse().to_constraint(), schemacompare.CompareForeignKey(fk))

    def test_add_fk(self):
        fk = self.fk
        op = ops.AddConstraintOp.from_constraint(fk)
        eq_(op.to_constraint(), schemacompare.CompareForeignKey(fk))
        eq_(op.reverse().to_constraint(), schemacompare.CompareForeignKey(fk))
        is_not_(None, op.to_constraint().table)

    def test_add_check(self):
        ck = self.ck
        op = ops.AddConstraintOp.from_constraint(ck)
        eq_(op.to_constraint(), schemacompare.CompareCheckConstraint(ck))
        eq_(
            op.reverse().to_constraint(),
            schemacompare.CompareCheckConstraint(ck),
        )
        is_not_(None, op.to_constraint().table)

    def test_drop_check(self):
        ck = self.ck
        op = ops.DropConstraintOp.from_constraint(ck)
        eq_(op.to_constraint(), schemacompare.CompareCheckConstraint(ck))
        eq_(
            op.reverse().to_constraint(),
            schemacompare.CompareCheckConstraint(ck),
        )
        is_not_(None, op.to_constraint().table)

    def test_add_unique(self):
        uq = self.uq
        op = ops.AddConstraintOp.from_constraint(uq)
        eq_(op.to_constraint(), schemacompare.CompareUniqueConstraint(uq))
        eq_(
            op.reverse().to_constraint(),
            schemacompare.CompareUniqueConstraint(uq),
        )
        is_not_(None, op.to_constraint().table)

    def test_drop_unique(self):
        uq = self.uq
        op = ops.DropConstraintOp.from_constraint(uq)
        eq_(op.to_constraint(), schemacompare.CompareUniqueConstraint(uq))
        eq_(
            op.reverse().to_constraint(),
            schemacompare.CompareUniqueConstraint(uq),
        )
        is_not_(None, op.to_constraint().table)

    def test_add_pk_no_orig(self):
        op = ops.CreatePrimaryKeyOp("pk1", "t", ["x", "y"])
        pk = op.to_constraint()
        eq_(pk.name, "pk1")
        eq_(pk.table.name, "t")

    def test_add_pk(self):
        pk = self.pk
        op = ops.AddConstraintOp.from_constraint(pk)
        eq_(op.to_constraint(), schemacompare.ComparePrimaryKey(pk))
        eq_(op.reverse().to_constraint(), schemacompare.ComparePrimaryKey(pk))
        is_not_(None, op.to_constraint().table)

    def test_drop_pk(self):
        pk = self.pk
        op = ops.DropConstraintOp.from_constraint(pk)
        eq_(op.to_constraint(), schemacompare.ComparePrimaryKey(pk))
        eq_(op.reverse().to_constraint(), schemacompare.ComparePrimaryKey(pk))
        is_not_(None, op.to_constraint().table)

    def test_drop_column(self):
        t = self.table

        op = ops.DropColumnOp.from_column_and_tablename(None, "t", t.c.x)
        is_(op.to_column(), t.c.x)
        is_(op.reverse().to_column(), t.c.x)
        is_not_(None, op.to_column().table)

    def test_add_column(self):
        t = self.table

        op = ops.AddColumnOp.from_column_and_tablename(None, "t", t.c.x)
        is_(op.to_column(), t.c.x)
        is_(op.reverse().to_column(), t.c.x)
        is_not_(None, op.to_column().table)

    def test_drop_table(self):
        t = self.table

        op = ops.DropTableOp.from_table(t)
        eq_(op.to_table(), schemacompare.CompareTable(t))
        eq_(op.reverse().to_table(), schemacompare.CompareTable(t))

    def test_add_table(self):
        t = self.table

        op = ops.CreateTableOp.from_table(t)
        eq_(op.to_table(), schemacompare.CompareTable(t))
        eq_(op.reverse().to_table(), schemacompare.CompareTable(t))

    def test_drop_index(self):
        op = ops.DropIndexOp.from_index(self.ix)
        eq_(op.to_index(), schemacompare.CompareIndex(self.ix))
        eq_(op.reverse().to_index(), schemacompare.CompareIndex(self.ix))

    def test_create_index(self):
        op = ops.CreateIndexOp.from_index(self.ix)
        eq_(op.to_index(), schemacompare.CompareIndex(self.ix))
        eq_(op.reverse().to_index(), schemacompare.CompareIndex(self.ix))


class MultipleMetaDataTest(AutogenFixtureTest, TestBase):
    def test_multiple(self):
        m1a = MetaData()
        m1b = MetaData()
        m1c = MetaData()

        m2a = MetaData()
        m2b = MetaData()
        m2c = MetaData()

        Table("a", m1a, Column("id", Integer, primary_key=True))
        Table("b1", m1b, Column("id", Integer, primary_key=True))
        Table("b2", m1b, Column("id", Integer, primary_key=True))
        Table(
            "c1",
            m1c,
            Column("id", Integer, primary_key=True),
            Column("x", Integer),
        )

        a = Table(
            "a",
            m2a,
            Column("id", Integer, primary_key=True),
            Column("q", Integer),
        )
        Table("b1", m2b, Column("id", Integer, primary_key=True))
        Table("c1", m2c, Column("id", Integer, primary_key=True))
        c2 = Table("c2", m2c, Column("id", Integer, primary_key=True))

        diffs = self._fixture([m1a, m1b, m1c], [m2a, m2b, m2c])
        eq_(diffs[0], ("add_table", schemacompare.CompareTable(c2)))
        eq_(diffs[1][0], "remove_table")
        eq_(diffs[1][1].name, "b2")
        eq_(diffs[2], ("add_column", None, "a", a.c.q))
        eq_(diffs[3][0:3], ("remove_column", None, "c1"))
        eq_(diffs[3][3].name, "x")

    def test_empty_list(self):
        # because they're going to do it....

        diffs = self._fixture([], [])
        eq_(diffs, [])

    def test_non_list_sequence(self):
        # we call it "sequence", let's check that

        m1a = MetaData()
        m1b = MetaData()

        m2a = MetaData()
        m2b = MetaData()

        Table("a", m1a, Column("id", Integer, primary_key=True))
        Table("b", m1b, Column("id", Integer, primary_key=True))

        Table("a", m2a, Column("id", Integer, primary_key=True))
        b = Table(
            "b",
            m2b,
            Column("id", Integer, primary_key=True),
            Column("q", Integer),
        )

        diffs = self._fixture((m1a, m1b), (m2a, m2b))
        eq_(diffs, [("add_column", None, "b", b.c.q)])

    def test_raise_on_dupe(self):
        m1a = MetaData()
        m1b = MetaData()

        m2a = MetaData()
        m2b = MetaData()

        Table("a", m1a, Column("id", Integer, primary_key=True))
        Table("b1", m1b, Column("id", Integer, primary_key=True))
        Table("b2", m1b, Column("id", Integer, primary_key=True))
        Table("b3", m1b, Column("id", Integer, primary_key=True))

        Table("a", m2a, Column("id", Integer, primary_key=True))
        Table("a", m2b, Column("id", Integer, primary_key=True))
        Table("b1", m2b, Column("id", Integer, primary_key=True))
        Table("b2", m2a, Column("id", Integer, primary_key=True))
        Table("b2", m2b, Column("id", Integer, primary_key=True))

        assert_raises_message(
            ValueError,
            'Duplicate table keys across multiple MetaData objects: "a", "b2"',
            self._fixture,
            [m1a, m1b],
            [m2a, m2b],
        )
