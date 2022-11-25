from contextlib import contextmanager
import re

from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import func
from sqlalchemy import Index
from sqlalchemy import inspect
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import MetaData
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import sqlite as sqlite_dialect
from sqlalchemy.schema import CreateIndex
from sqlalchemy.schema import CreateTable
from sqlalchemy.sql import column
from sqlalchemy.sql import text

from alembic import command
from alembic import testing
from alembic import util
from alembic.ddl import sqlite
from alembic.operations import Operations
from alembic.operations.batch import ApplyBatchImpl
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.testing import assert_raises_message
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import exclusions
from alembic.testing import expect_raises_message
from alembic.testing import is_
from alembic.testing import mock
from alembic.testing import TestBase
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.env import write_script
from alembic.testing.fixtures import capture_context_buffer
from alembic.testing.fixtures import op_fixture
from alembic.util import CommandError
from alembic.util import exc as alembic_exc
from alembic.util.sqla_compat import _safe_commit_connection_transaction
from alembic.util.sqla_compat import _select
from alembic.util.sqla_compat import has_computed
from alembic.util.sqla_compat import has_identity
from alembic.util.sqla_compat import sqla_14

if has_computed:
    from alembic.util.sqla_compat import Computed

if has_identity:
    from alembic.util.sqla_compat import Identity


class BatchApplyTest(TestBase):
    def setUp(self):
        self.op = Operations(mock.Mock(opts={}))
        self.impl = sqlite.SQLiteImpl(
            sqlite_dialect.dialect(), None, False, False, None, {}
        )

    def _simple_fixture(self, table_args=(), table_kwargs={}, **kw):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("x", String(10)),
            Column("y", Integer),
        )
        return ApplyBatchImpl(
            self.impl, t, table_args, table_kwargs, False, **kw
        )

    def _uq_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("x", String()),
            Column("y", Integer),
            UniqueConstraint("y", name="uq1"),
        )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _named_ck_table_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("x", String()),
            Column("y", Integer),
            CheckConstraint("y > 5", name="ck1"),
        )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _named_ck_col_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("x", String()),
            Column("y", Integer, CheckConstraint("y > 5", name="ck1")),
        )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _ix_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("x", String()),
            Column("y", Integer),
            Index("ix1", "y"),
        )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _pk_fixture(self):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer),
            Column("x", String()),
            Column("y", Integer),
            PrimaryKeyConstraint("id", name="mypk"),
        )
        return ApplyBatchImpl(self.impl, t, (), {}, False)

    def _literal_ck_fixture(
        self, copy_from=None, table_args=(), table_kwargs={}
    ):
        m = MetaData()
        if copy_from is not None:
            t = copy_from
        else:
            t = Table(
                "tname",
                m,
                Column("id", Integer, primary_key=True),
                Column("email", String()),
                CheckConstraint("email LIKE '%@%'"),
            )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _sql_ck_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("email", String()),
        )
        t.append_constraint(CheckConstraint(t.c.email.like("%@%")))
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _fk_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("email", String()),
            Column("user_id", Integer, ForeignKey("user.id")),
        )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _multi_fk_fixture(self, table_args=(), table_kwargs={}, schema=None):
        m = MetaData()
        if schema:
            schemaarg = "%s." % schema
        else:
            schemaarg = ""

        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("email", String()),
            Column("user_id_1", Integer, ForeignKey("%suser.id" % schemaarg)),
            Column("user_id_2", Integer, ForeignKey("%suser.id" % schemaarg)),
            Column("user_id_3", Integer),
            Column("user_id_version", Integer),
            ForeignKeyConstraint(
                ["user_id_3", "user_id_version"],
                ["%suser.id" % schemaarg, "%suser.id_version" % schemaarg],
            ),
            schema=schema,
        )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _named_fk_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("email", String()),
            Column("user_id", Integer, ForeignKey("user.id", name="ufk")),
        )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _selfref_fk_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("parent_id", Integer, ForeignKey("tname.id")),
            Column("data", String),
        )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _boolean_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("flag", Boolean(create_constraint=True)),
        )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _boolean_no_ck_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("flag", Boolean(create_constraint=False)),
        )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _enum_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("thing", Enum("a", "b", "c", create_constraint=True)),
        )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _server_default_fixture(self, table_args=(), table_kwargs={}):
        m = MetaData()
        t = Table(
            "tname",
            m,
            Column("id", Integer, primary_key=True),
            Column("thing", String(), server_default=""),
        )
        return ApplyBatchImpl(self.impl, t, table_args, table_kwargs, False)

    def _assert_impl(
        self,
        impl,
        colnames=None,
        ddl_contains=None,
        ddl_not_contains=None,
        dialect="default",
        schema=None,
    ):
        context = op_fixture(dialect=dialect)

        impl._create(context.impl)

        if colnames is None:
            colnames = ["id", "x", "y"]
        eq_(impl.new_table.c.keys(), colnames)

        pk_cols = [col for col in impl.new_table.c if col.primary_key]
        eq_(list(impl.new_table.primary_key), pk_cols)

        create_stmt = str(
            CreateTable(impl.new_table).compile(dialect=context.dialect)
        )
        create_stmt = re.sub(r"[\n\t]", "", create_stmt)

        idx_stmt = ""

        # create indexes; these should be created in terms of the
        # final table name
        impl.new_table.name = impl.table.name

        for idx in impl._gather_indexes_from_both_tables():
            idx_stmt += str(CreateIndex(idx).compile(dialect=context.dialect))

        idx_stmt = re.sub(r"[\n\t]", "", idx_stmt)

        # revert new table name to the temp name, assertions below
        # are looking for the temp name
        impl.new_table.name = ApplyBatchImpl._calc_temp_name(impl.table.name)

        if ddl_contains:
            assert ddl_contains in create_stmt + idx_stmt
        if ddl_not_contains:
            assert ddl_not_contains not in create_stmt + idx_stmt

        expected = [create_stmt]

        if schema:
            args = {"schema": "%s." % schema}
        else:
            args = {"schema": ""}

        args["temp_name"] = impl.new_table.name

        args["colnames"] = ", ".join(
            [
                impl.new_table.c[name].name
                for name in colnames
                if name in impl.table.c
            ]
        )

        args["tname_colnames"] = ", ".join(
            "CAST(%(schema)stname.%(name)s AS %(type)s) AS %(cast_label)s"
            % {
                "schema": args["schema"],
                "name": name,
                "type": impl.new_table.c[name].type,
                "cast_label": name if sqla_14 else "anon_1",
            }
            if (
                impl.new_table.c[name].type._type_affinity
                is not impl.table.c[name].type._type_affinity
            )
            else "%(schema)stname.%(name)s"
            % {"schema": args["schema"], "name": name}
            for name in colnames
            if name in impl.table.c
        )

        expected.extend(
            [
                "INSERT INTO %(schema)s%(temp_name)s (%(colnames)s) "
                "SELECT %(tname_colnames)s FROM %(schema)stname" % args,
                "DROP TABLE %(schema)stname" % args,
                "ALTER TABLE %(schema)s%(temp_name)s "
                "RENAME TO %(schema)stname" % args,
            ]
        )
        if idx_stmt:
            expected.append(idx_stmt)
        context.assert_(*expected)
        return impl.new_table

    def test_change_type(self):
        impl = self._simple_fixture()
        impl.alter_column("tname", "x", type_=String)
        new_table = self._assert_impl(impl)
        assert new_table.c.x.type._type_affinity is String

    def test_rename_col(self):
        impl = self._simple_fixture()
        impl.alter_column("tname", "x", name="q")
        new_table = self._assert_impl(impl)
        eq_(new_table.c.x.name, "q")

    def test_rename_col_w_index(self):
        impl = self._ix_fixture()
        impl.alter_column("tname", "y", name="y2")
        new_table = self._assert_impl(
            impl, ddl_contains="CREATE INDEX ix1 ON tname (y2)"
        )
        eq_(new_table.c.y.name, "y2")

    def test_rename_col_w_uq(self):
        impl = self._uq_fixture()
        impl.alter_column("tname", "y", name="y2")
        new_table = self._assert_impl(impl, ddl_contains="UNIQUE (y2)")
        eq_(new_table.c.y.name, "y2")

    def test_alter_column_comment(self):
        impl = self._simple_fixture()
        impl.alter_column("tname", "x", comment="some comment")
        new_table = self._assert_impl(impl)
        eq_(new_table.c.x.comment, "some comment")

    def test_add_column_comment(self):
        impl = self._simple_fixture()
        impl.add_column("tname", Column("q", Integer, comment="some comment"))
        new_table = self._assert_impl(impl, colnames=["id", "x", "y", "q"])
        eq_(new_table.c.q.comment, "some comment")

    def test_rename_col_boolean(self):
        impl = self._boolean_fixture()
        impl.alter_column("tname", "flag", name="bflag")
        new_table = self._assert_impl(
            impl,
            ddl_contains="CHECK (bflag IN (0, 1)",
            colnames=["id", "flag"],
        )
        eq_(new_table.c.flag.name, "bflag")
        eq_(
            len(
                [
                    const
                    for const in new_table.constraints
                    if isinstance(const, CheckConstraint)
                ]
            ),
            1,
        )

    def test_change_type_schematype_to_non(self):
        impl = self._boolean_fixture()
        impl.alter_column("tname", "flag", type_=Integer)
        new_table = self._assert_impl(
            impl, colnames=["id", "flag"], ddl_not_contains="CHECK"
        )
        assert new_table.c.flag.type._type_affinity is Integer

        # NOTE: we can't do test_change_type_non_to_schematype
        # at this level because the "add_constraint" part of this
        # comes from toimpl.py, which we aren't testing here

    def test_rename_col_boolean_no_ck(self):
        impl = self._boolean_no_ck_fixture()
        impl.alter_column("tname", "flag", name="bflag")
        new_table = self._assert_impl(
            impl, ddl_not_contains="CHECK", colnames=["id", "flag"]
        )
        eq_(new_table.c.flag.name, "bflag")
        eq_(
            len(
                [
                    const
                    for const in new_table.constraints
                    if isinstance(const, CheckConstraint)
                ]
            ),
            0,
        )

    def test_rename_col_enum(self):
        impl = self._enum_fixture()
        impl.alter_column("tname", "thing", name="thang")
        new_table = self._assert_impl(
            impl,
            ddl_contains="CHECK (thang IN ('a', 'b', 'c')",
            colnames=["id", "thing"],
        )
        eq_(new_table.c.thing.name, "thang")
        eq_(
            len(
                [
                    const
                    for const in new_table.constraints
                    if isinstance(const, CheckConstraint)
                ]
            ),
            1,
        )

    def test_rename_col_literal_ck(self):
        impl = self._literal_ck_fixture()
        impl.alter_column("tname", "email", name="emol")
        new_table = self._assert_impl(
            # note this is wrong, we don't dig into the SQL
            impl,
            ddl_contains="CHECK (email LIKE '%@%')",
            colnames=["id", "email"],
        )
        eq_(
            len(
                [
                    c
                    for c in new_table.constraints
                    if isinstance(c, CheckConstraint)
                ]
            ),
            1,
        )

        eq_(new_table.c.email.name, "emol")

    def test_rename_col_literal_ck_workaround(self):
        impl = self._literal_ck_fixture(
            copy_from=Table(
                "tname",
                MetaData(),
                Column("id", Integer, primary_key=True),
                Column("email", String),
            ),
            table_args=[CheckConstraint("emol LIKE '%@%'")],
        )

        impl.alter_column("tname", "email", name="emol")
        new_table = self._assert_impl(
            impl,
            ddl_contains="CHECK (emol LIKE '%@%')",
            colnames=["id", "email"],
        )
        eq_(
            len(
                [
                    c
                    for c in new_table.constraints
                    if isinstance(c, CheckConstraint)
                ]
            ),
            1,
        )
        eq_(new_table.c.email.name, "emol")

    def test_rename_col_sql_ck(self):
        impl = self._sql_ck_fixture()

        impl.alter_column("tname", "email", name="emol")
        new_table = self._assert_impl(
            impl,
            ddl_contains="CHECK (emol LIKE '%@%')",
            colnames=["id", "email"],
        )
        eq_(
            len(
                [
                    c
                    for c in new_table.constraints
                    if isinstance(c, CheckConstraint)
                ]
            ),
            1,
        )

        eq_(new_table.c.email.name, "emol")

    def test_add_col(self):
        impl = self._simple_fixture()
        col = Column("g", Integer)
        # operations.add_column produces a table
        t = self.op.schema_obj.table("tname", col)  # noqa
        impl.add_column("tname", col)
        new_table = self._assert_impl(impl, colnames=["id", "x", "y", "g"])
        eq_(new_table.c.g.name, "g")

    def test_partial_reordering(self):
        impl = self._simple_fixture(partial_reordering=[("x", "id", "y")])
        new_table = self._assert_impl(impl, colnames=["x", "id", "y"])
        eq_(new_table.c.x.name, "x")

    def test_add_col_partial_reordering(self):
        impl = self._simple_fixture(partial_reordering=[("id", "x", "g", "y")])
        col = Column("g", Integer)
        # operations.add_column produces a table
        t = self.op.schema_obj.table("tname", col)  # noqa
        impl.add_column("tname", col)
        new_table = self._assert_impl(impl, colnames=["id", "x", "g", "y"])
        eq_(new_table.c.g.name, "g")

    def test_add_col_insert_before(self):
        impl = self._simple_fixture()
        col = Column("g", Integer)
        # operations.add_column produces a table
        t = self.op.schema_obj.table("tname", col)  # noqa
        impl.add_column("tname", col, insert_before="x")
        new_table = self._assert_impl(impl, colnames=["id", "g", "x", "y"])
        eq_(new_table.c.g.name, "g")

    def test_add_col_insert_before_beginning(self):
        impl = self._simple_fixture()
        impl.add_column("tname", Column("g", Integer), insert_before="id")
        new_table = self._assert_impl(impl, colnames=["g", "id", "x", "y"])
        eq_(new_table.c.g.name, "g")

    def test_add_col_insert_before_middle(self):
        impl = self._simple_fixture()
        impl.add_column("tname", Column("g", Integer), insert_before="y")
        new_table = self._assert_impl(impl, colnames=["id", "x", "g", "y"])
        eq_(new_table.c.g.name, "g")

    def test_add_col_insert_after_middle(self):
        impl = self._simple_fixture()
        impl.add_column("tname", Column("g", Integer), insert_after="id")
        new_table = self._assert_impl(impl, colnames=["id", "g", "x", "y"])
        eq_(new_table.c.g.name, "g")

    def test_add_col_insert_after_penultimate(self):
        impl = self._simple_fixture()
        impl.add_column("tname", Column("g", Integer), insert_after="x")
        self._assert_impl(impl, colnames=["id", "x", "g", "y"])

    def test_add_col_insert_after_end(self):
        impl = self._simple_fixture()
        impl.add_column("tname", Column("g", Integer), insert_after="y")
        new_table = self._assert_impl(impl, colnames=["id", "x", "y", "g"])
        eq_(new_table.c.g.name, "g")

    def test_add_col_insert_after_plus_no_order(self):
        impl = self._simple_fixture()
        # operations.add_column produces a table
        impl.add_column("tname", Column("g", Integer), insert_after="id")
        impl.add_column("tname", Column("q", Integer))
        new_table = self._assert_impl(
            impl, colnames=["id", "g", "x", "y", "q"]
        )
        eq_(new_table.c.g.name, "g")

    def test_add_col_no_order_plus_insert_after(self):
        impl = self._simple_fixture()
        col = Column("g", Integer)
        # operations.add_column produces a table
        t = self.op.schema_obj.table("tname", col)  # noqa
        impl.add_column("tname", Column("q", Integer))
        impl.add_column("tname", Column("g", Integer), insert_after="id")
        new_table = self._assert_impl(
            impl, colnames=["id", "g", "x", "y", "q"]
        )
        eq_(new_table.c.g.name, "g")

    def test_add_col_insert_after_another_insert(self):
        impl = self._simple_fixture()
        impl.add_column("tname", Column("g", Integer), insert_after="id")
        impl.add_column("tname", Column("q", Integer), insert_after="g")
        new_table = self._assert_impl(
            impl, colnames=["id", "g", "q", "x", "y"]
        )
        eq_(new_table.c.g.name, "g")

    def test_add_col_insert_before_another_insert(self):
        impl = self._simple_fixture()
        impl.add_column("tname", Column("g", Integer), insert_after="id")
        impl.add_column("tname", Column("q", Integer), insert_before="g")
        new_table = self._assert_impl(
            impl, colnames=["id", "q", "g", "x", "y"]
        )
        eq_(new_table.c.g.name, "g")

    def test_add_server_default(self):
        impl = self._simple_fixture()
        impl.alter_column("tname", "y", server_default="10")
        new_table = self._assert_impl(impl, ddl_contains="DEFAULT '10'")
        eq_(new_table.c.y.server_default.arg, "10")

    def test_drop_server_default(self):
        impl = self._server_default_fixture()
        impl.alter_column("tname", "thing", server_default=None)
        new_table = self._assert_impl(
            impl, colnames=["id", "thing"], ddl_not_contains="DEFAULT"
        )
        eq_(new_table.c.thing.server_default, None)

    def test_rename_col_pk(self):
        impl = self._simple_fixture()
        impl.alter_column("tname", "id", name="foobar")
        new_table = self._assert_impl(
            impl, ddl_contains="PRIMARY KEY (foobar)"
        )
        eq_(new_table.c.id.name, "foobar")
        eq_(list(new_table.primary_key), [new_table.c.id])

    def test_rename_col_fk(self):
        impl = self._fk_fixture()
        impl.alter_column("tname", "user_id", name="foobar")
        new_table = self._assert_impl(
            impl,
            colnames=["id", "email", "user_id"],
            ddl_contains='FOREIGN KEY(foobar) REFERENCES "user" (id)',
        )
        eq_(new_table.c.user_id.name, "foobar")
        eq_(
            list(new_table.c.user_id.foreign_keys)[0]._get_colspec(), "user.id"
        )

    def test_regen_multi_fk(self):
        impl = self._multi_fk_fixture()
        self._assert_impl(
            impl,
            colnames=[
                "id",
                "email",
                "user_id_1",
                "user_id_2",
                "user_id_3",
                "user_id_version",
            ],
            ddl_contains="FOREIGN KEY(user_id_3, user_id_version) "
            'REFERENCES "user" (id, id_version)',
        )

    def test_regen_multi_fk_schema(self):
        impl = self._multi_fk_fixture(schema="foo_schema")
        self._assert_impl(
            impl,
            colnames=[
                "id",
                "email",
                "user_id_1",
                "user_id_2",
                "user_id_3",
                "user_id_version",
            ],
            ddl_contains="FOREIGN KEY(user_id_3, user_id_version) "
            'REFERENCES foo_schema."user" (id, id_version)',
            schema="foo_schema",
        )

    def test_do_not_add_existing_columns_columns(self):
        impl = self._multi_fk_fixture()
        meta = impl.table.metadata

        cid = Column("id", Integer())
        user = Table("user", meta, cid)

        fk = [
            c
            for c in impl.unnamed_constraints
            if isinstance(c, ForeignKeyConstraint)
        ]
        impl._setup_referent(meta, fk[0])
        is_(user.c.id, cid)

    def test_drop_col(self):
        impl = self._simple_fixture()
        impl.drop_column("tname", column("x"))
        new_table = self._assert_impl(impl, colnames=["id", "y"])
        assert "y" in new_table.c
        assert "x" not in new_table.c

    def test_drop_col_remove_pk(self):
        impl = self._simple_fixture()
        impl.drop_column("tname", column("id"))
        new_table = self._assert_impl(
            impl, colnames=["x", "y"], ddl_not_contains="PRIMARY KEY"
        )
        assert "y" in new_table.c
        assert "id" not in new_table.c
        assert not new_table.primary_key

    def test_drop_col_remove_fk(self):
        impl = self._fk_fixture()
        impl.drop_column("tname", column("user_id"))
        new_table = self._assert_impl(
            impl, colnames=["id", "email"], ddl_not_contains="FOREIGN KEY"
        )
        assert "user_id" not in new_table.c
        assert not new_table.foreign_keys

    def test_drop_col_retain_fk(self):
        impl = self._fk_fixture()
        impl.drop_column("tname", column("email"))
        new_table = self._assert_impl(
            impl,
            colnames=["id", "user_id"],
            ddl_contains='FOREIGN KEY(user_id) REFERENCES "user" (id)',
        )
        assert "email" not in new_table.c
        assert new_table.c.user_id.foreign_keys

    def test_drop_col_retain_fk_selfref(self):
        impl = self._selfref_fk_fixture()
        impl.drop_column("tname", column("data"))
        new_table = self._assert_impl(impl, colnames=["id", "parent_id"])
        assert "data" not in new_table.c
        assert new_table.c.parent_id.foreign_keys

    def test_add_fk(self):
        impl = self._simple_fixture()
        impl.add_column("tname", Column("user_id", Integer))
        fk = self.op.schema_obj.foreign_key_constraint(
            "fk1", "tname", "user", ["user_id"], ["id"]
        )
        impl.add_constraint(fk)
        new_table = self._assert_impl(
            impl,
            colnames=["id", "x", "y", "user_id"],
            ddl_contains="CONSTRAINT fk1 FOREIGN KEY(user_id) "
            'REFERENCES "user" (id)',
        )
        eq_(
            list(new_table.c.user_id.foreign_keys)[0]._get_colspec(), "user.id"
        )

    def test_drop_fk(self):
        impl = self._named_fk_fixture()
        fk = ForeignKeyConstraint([], [], name="ufk")
        impl.drop_constraint(fk)
        new_table = self._assert_impl(
            impl,
            colnames=["id", "email", "user_id"],
            ddl_not_contains="CONSTRANT fk1",
        )
        eq_(list(new_table.foreign_keys), [])

    def test_add_uq(self):
        impl = self._simple_fixture()
        uq = self.op.schema_obj.unique_constraint("uq1", "tname", ["y"])

        impl.add_constraint(uq)
        self._assert_impl(
            impl,
            colnames=["id", "x", "y"],
            ddl_contains="CONSTRAINT uq1 UNIQUE",
        )

    def test_drop_uq(self):
        impl = self._uq_fixture()

        uq = self.op.schema_obj.unique_constraint("uq1", "tname", ["y"])
        impl.drop_constraint(uq)
        self._assert_impl(
            impl,
            colnames=["id", "x", "y"],
            ddl_not_contains="CONSTRAINT uq1 UNIQUE",
        )

    def test_add_ck(self):
        impl = self._simple_fixture()
        ck = self.op.schema_obj.check_constraint("ck1", "tname", "y > 5")

        impl.add_constraint(ck)
        self._assert_impl(
            impl,
            colnames=["id", "x", "y"],
            ddl_contains="CONSTRAINT ck1 CHECK (y > 5)",
        )

    def test_drop_ck_table(self):
        impl = self._named_ck_table_fixture()

        ck = self.op.schema_obj.check_constraint("ck1", "tname", "y > 5")
        impl.drop_constraint(ck)
        self._assert_impl(
            impl,
            colnames=["id", "x", "y"],
            ddl_not_contains="CONSTRAINT ck1 CHECK (y > 5)",
        )

    def test_drop_ck_col(self):
        impl = self._named_ck_col_fixture()

        ck = self.op.schema_obj.check_constraint("ck1", "tname", "y > 5")
        impl.drop_constraint(ck)
        self._assert_impl(
            impl,
            colnames=["id", "x", "y"],
            ddl_not_contains="CONSTRAINT ck1 CHECK (y > 5)",
        )

    def test_create_index(self):
        impl = self._simple_fixture()
        ix = self.op.schema_obj.index("ix1", "tname", ["y"])

        impl.create_index(ix)
        self._assert_impl(
            impl, colnames=["id", "x", "y"], ddl_contains="CREATE INDEX ix1"
        )

    def test_drop_index(self):
        impl = self._ix_fixture()

        ix = self.op.schema_obj.index("ix1", "tname", ["y"])
        impl.drop_index(ix)
        self._assert_impl(
            impl,
            colnames=["id", "x", "y"],
            ddl_not_contains="CONSTRAINT uq1 UNIQUE",
        )

    def test_add_table_opts(self):
        impl = self._simple_fixture(table_kwargs={"mysql_engine": "InnoDB"})
        self._assert_impl(impl, ddl_contains="ENGINE=InnoDB", dialect="mysql")

    def test_drop_pk(self):
        impl = self._pk_fixture()
        pk = self.op.schema_obj.primary_key_constraint("mypk", "tname", ["id"])
        impl.drop_constraint(pk)
        new_table = self._assert_impl(impl)
        assert not new_table.c.id.primary_key
        assert not len(new_table.primary_key)


class BatchAPITest(TestBase):
    @contextmanager
    def _fixture(self, schema=None):

        migration_context = mock.Mock(
            opts={},
            impl=mock.MagicMock(__dialect__="sqlite", connection=object()),
        )
        op = Operations(migration_context)
        batch = op.batch_alter_table(
            "tname", recreate="never", schema=schema
        ).__enter__()

        mock_schema = mock.MagicMock()
        with mock.patch("alembic.operations.schemaobj.sa_schema", mock_schema):
            yield batch
        batch.impl.flush()
        self.mock_schema = mock_schema

    def test_drop_col(self):
        with self._fixture() as batch:
            batch.drop_column("q")

        eq_(
            batch.impl.operations.impl.mock_calls,
            [
                mock.call.drop_column(
                    "tname", self.mock_schema.Column(), schema=None
                )
            ],
        )

    def test_add_col(self):
        column = Column("w", String(50))

        with self._fixture() as batch:
            batch.add_column(column)

        assert (
            mock.call.add_column("tname", column, schema=None)
            in batch.impl.operations.impl.mock_calls
        )

    def test_create_fk(self):
        with self._fixture() as batch:
            batch.create_foreign_key("myfk", "user", ["x"], ["y"])

        eq_(
            self.mock_schema.ForeignKeyConstraint.mock_calls,
            [
                mock.call(
                    ["x"],
                    ["user.y"],
                    onupdate=None,
                    ondelete=None,
                    name="myfk",
                    initially=None,
                    deferrable=None,
                    match=None,
                )
            ],
        )
        eq_(
            self.mock_schema.Table.mock_calls,
            [
                mock.call(
                    "user",
                    self.mock_schema.MetaData(),
                    self.mock_schema.Column(),
                    schema=None,
                ),
                mock.call(
                    "tname",
                    self.mock_schema.MetaData(),
                    self.mock_schema.Column(),
                    schema=None,
                ),
                mock.call().append_constraint(
                    self.mock_schema.ForeignKeyConstraint()
                ),
            ],
        )
        eq_(
            batch.impl.operations.impl.mock_calls,
            [
                mock.call.add_constraint(
                    self.mock_schema.ForeignKeyConstraint()
                )
            ],
        )

    def test_create_fk_schema(self):
        with self._fixture(schema="foo") as batch:
            batch.create_foreign_key("myfk", "user", ["x"], ["y"])

        eq_(
            self.mock_schema.ForeignKeyConstraint.mock_calls,
            [
                mock.call(
                    ["x"],
                    ["user.y"],
                    onupdate=None,
                    ondelete=None,
                    name="myfk",
                    initially=None,
                    deferrable=None,
                    match=None,
                )
            ],
        )
        eq_(
            self.mock_schema.Table.mock_calls,
            [
                mock.call(
                    "user",
                    self.mock_schema.MetaData(),
                    self.mock_schema.Column(),
                    schema=None,
                ),
                mock.call(
                    "tname",
                    self.mock_schema.MetaData(),
                    self.mock_schema.Column(),
                    schema="foo",
                ),
                mock.call().append_constraint(
                    self.mock_schema.ForeignKeyConstraint()
                ),
            ],
        )
        eq_(
            batch.impl.operations.impl.mock_calls,
            [
                mock.call.add_constraint(
                    self.mock_schema.ForeignKeyConstraint()
                )
            ],
        )

    def test_create_uq(self):
        with self._fixture() as batch:
            batch.create_unique_constraint("uq1", ["a", "b"])

        eq_(
            self.mock_schema.Table().c.__getitem__.mock_calls,
            [mock.call("a"), mock.call("b")],
        )

        eq_(
            self.mock_schema.UniqueConstraint.mock_calls,
            [
                mock.call(
                    self.mock_schema.Table().c.__getitem__(),
                    self.mock_schema.Table().c.__getitem__(),
                    name="uq1",
                )
            ],
        )
        eq_(
            batch.impl.operations.impl.mock_calls,
            [mock.call.add_constraint(self.mock_schema.UniqueConstraint())],
        )

    def test_create_pk(self):
        with self._fixture() as batch:
            batch.create_primary_key("pk1", ["a", "b"])

        eq_(
            self.mock_schema.Table().c.__getitem__.mock_calls,
            [mock.call("a"), mock.call("b")],
        )

        eq_(
            self.mock_schema.PrimaryKeyConstraint.mock_calls,
            [
                mock.call(
                    self.mock_schema.Table().c.__getitem__(),
                    self.mock_schema.Table().c.__getitem__(),
                    name="pk1",
                )
            ],
        )
        eq_(
            batch.impl.operations.impl.mock_calls,
            [
                mock.call.add_constraint(
                    self.mock_schema.PrimaryKeyConstraint()
                )
            ],
        )

    def test_create_check(self):
        expr = text("a > b")
        with self._fixture() as batch:
            batch.create_check_constraint("ck1", expr)

        eq_(
            self.mock_schema.CheckConstraint.mock_calls,
            [mock.call(expr, name="ck1")],
        )
        eq_(
            batch.impl.operations.impl.mock_calls,
            [mock.call.add_constraint(self.mock_schema.CheckConstraint())],
        )

    def test_drop_constraint(self):
        with self._fixture() as batch:
            batch.drop_constraint("uq1")

        eq_(self.mock_schema.Constraint.mock_calls, [mock.call(name="uq1")])
        eq_(
            batch.impl.operations.impl.mock_calls,
            [mock.call.drop_constraint(self.mock_schema.Constraint())],
        )


class CopyFromTest(TestBase):
    def _fixture(self):
        self.metadata = MetaData()
        self.table = Table(
            "foo",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("data", String(50)),
            Column("x", Integer),
        )

        context = op_fixture(dialect="sqlite", as_sql=True)
        self.op = Operations(context)
        return context

    @config.requirements.sqlalchemy_13
    def test_change_type(self):
        context = self._fixture()
        self.table.append_column(Column("toj", Text))
        self.table.append_column(Column("fromj", JSON))
        with self.op.batch_alter_table(
            "foo", copy_from=self.table
        ) as batch_op:
            batch_op.alter_column("data", type_=Integer)
            batch_op.alter_column("toj", type_=JSON)
            batch_op.alter_column("fromj", type_=Text)
        context.assert_(
            "CREATE TABLE _alembic_tmp_foo (id INTEGER NOT NULL, "
            "data INTEGER, x INTEGER, toj JSON, fromj TEXT, PRIMARY KEY (id))",
            "INSERT INTO _alembic_tmp_foo (id, data, x, toj, fromj) "
            "SELECT foo.id, "
            "CAST(foo.data AS INTEGER) AS %s, foo.x, foo.toj, "
            "CAST(foo.fromj AS TEXT) AS %s FROM foo"
            % (
                ("data" if sqla_14 else "anon_1"),
                ("fromj" if sqla_14 else "anon_2"),
            ),
            "DROP TABLE foo",
            "ALTER TABLE _alembic_tmp_foo RENAME TO foo",
        )

    def test_change_type_from_schematype(self):
        context = self._fixture()
        self.table.append_column(
            Column("y", Boolean(create_constraint=True, name="ck1"))
        )

        with self.op.batch_alter_table(
            "foo", copy_from=self.table
        ) as batch_op:
            batch_op.alter_column(
                "y",
                type_=Integer,
                existing_type=Boolean(create_constraint=True, name="ck1"),
            )
        context.assert_(
            "CREATE TABLE _alembic_tmp_foo (id INTEGER NOT NULL, "
            "data VARCHAR(50), x INTEGER, y INTEGER, PRIMARY KEY (id))",
            "INSERT INTO _alembic_tmp_foo (id, data, x, y) SELECT foo.id, "
            "foo.data, foo.x, CAST(foo.y AS INTEGER) AS %s FROM foo"
            % (("y" if sqla_14 else "anon_1"),),
            "DROP TABLE foo",
            "ALTER TABLE _alembic_tmp_foo RENAME TO foo",
        )

    def test_change_name_from_existing_variant_type(self):
        """test #982"""
        context = self._fixture()
        self.table.append_column(
            Column("y", Text().with_variant(Text(10000), "mysql"))
        )

        with self.op.batch_alter_table(
            "foo", copy_from=self.table
        ) as batch_op:
            batch_op.alter_column(
                column_name="y",
                new_column_name="q",
                existing_type=Text().with_variant(Text(10000), "mysql"),
            )
        context.assert_(
            "CREATE TABLE _alembic_tmp_foo (id INTEGER NOT NULL, "
            "data VARCHAR(50), x INTEGER, q TEXT, PRIMARY KEY (id))",
            "INSERT INTO _alembic_tmp_foo (id, data, x, q) "
            "SELECT foo.id, foo.data, foo.x, foo.y FROM foo",
            "DROP TABLE foo",
            "ALTER TABLE _alembic_tmp_foo RENAME TO foo",
        )

    def test_change_type_to_schematype(self):
        context = self._fixture()
        self.table.append_column(Column("y", Integer))

        with self.op.batch_alter_table(
            "foo", copy_from=self.table
        ) as batch_op:
            batch_op.alter_column(
                "y",
                existing_type=Integer,
                type_=Boolean(create_constraint=True, name="ck1"),
            )
        context.assert_(
            "CREATE TABLE _alembic_tmp_foo (id INTEGER NOT NULL, "
            "data VARCHAR(50), x INTEGER, y BOOLEAN, PRIMARY KEY (id), "
            "CONSTRAINT ck1 CHECK (y IN (0, 1)))",
            "INSERT INTO _alembic_tmp_foo (id, data, x, y) SELECT foo.id, "
            "foo.data, foo.x, CAST(foo.y AS BOOLEAN) AS %s FROM foo"
            % (("y" if sqla_14 else "anon_1"),),
            "DROP TABLE foo",
            "ALTER TABLE _alembic_tmp_foo RENAME TO foo",
        )

    def test_create_drop_index_w_always(self):
        context = self._fixture()
        with self.op.batch_alter_table(
            "foo", copy_from=self.table, recreate="always"
        ) as batch_op:
            batch_op.create_index("ix_data", ["data"], unique=True)

        context.assert_(
            "CREATE TABLE _alembic_tmp_foo (id INTEGER NOT NULL, "
            "data VARCHAR(50), "
            "x INTEGER, PRIMARY KEY (id))",
            "INSERT INTO _alembic_tmp_foo (id, data, x) "
            "SELECT foo.id, foo.data, foo.x FROM foo",
            "DROP TABLE foo",
            "ALTER TABLE _alembic_tmp_foo RENAME TO foo",
            "CREATE UNIQUE INDEX ix_data ON foo (data)",
        )

        context.clear_assertions()

        Index("ix_data", self.table.c.data, unique=True)
        with self.op.batch_alter_table(
            "foo", copy_from=self.table, recreate="always"
        ) as batch_op:
            batch_op.drop_index("ix_data")

        context.assert_(
            "CREATE TABLE _alembic_tmp_foo (id INTEGER NOT NULL, "
            "data VARCHAR(50), x INTEGER, PRIMARY KEY (id))",
            "INSERT INTO _alembic_tmp_foo (id, data, x) "
            "SELECT foo.id, foo.data, foo.x FROM foo",
            "DROP TABLE foo",
            "ALTER TABLE _alembic_tmp_foo RENAME TO foo",
        )

    def test_create_drop_index_wo_always(self):
        context = self._fixture()
        with self.op.batch_alter_table(
            "foo", copy_from=self.table
        ) as batch_op:
            batch_op.create_index("ix_data", ["data"], unique=True)

        context.assert_("CREATE UNIQUE INDEX ix_data ON foo (data)")

        context.clear_assertions()

        Index("ix_data", self.table.c.data, unique=True)
        with self.op.batch_alter_table(
            "foo", copy_from=self.table
        ) as batch_op:
            batch_op.drop_index("ix_data")

        context.assert_("DROP INDEX ix_data")

    def test_create_drop_index_w_other_ops(self):
        context = self._fixture()
        with self.op.batch_alter_table(
            "foo", copy_from=self.table
        ) as batch_op:
            batch_op.alter_column("data", type_=Integer)
            batch_op.create_index("ix_data", ["data"], unique=True)

        context.assert_(
            "CREATE TABLE _alembic_tmp_foo (id INTEGER NOT NULL, "
            "data INTEGER, x INTEGER, PRIMARY KEY (id))",
            "INSERT INTO _alembic_tmp_foo (id, data, x) SELECT foo.id, "
            "CAST(foo.data AS INTEGER) AS %s, foo.x FROM foo"
            % (("data" if sqla_14 else "anon_1"),),
            "DROP TABLE foo",
            "ALTER TABLE _alembic_tmp_foo RENAME TO foo",
            "CREATE UNIQUE INDEX ix_data ON foo (data)",
        )

        context.clear_assertions()

        Index("ix_data", self.table.c.data, unique=True)
        with self.op.batch_alter_table(
            "foo", copy_from=self.table
        ) as batch_op:
            batch_op.drop_index("ix_data")
            batch_op.alter_column("data", type_=String)

        context.assert_(
            "CREATE TABLE _alembic_tmp_foo (id INTEGER NOT NULL, "
            "data VARCHAR, x INTEGER, PRIMARY KEY (id))",
            "INSERT INTO _alembic_tmp_foo (id, data, x) SELECT foo.id, "
            "foo.data, foo.x FROM foo",
            "DROP TABLE foo",
            "ALTER TABLE _alembic_tmp_foo RENAME TO foo",
        )


class BatchRoundTripTest(TestBase):
    __only_on__ = "sqlite"

    def setUp(self):
        self.conn = config.db.connect()
        self.metadata = MetaData()
        t1 = Table(
            "foo",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("data", String(50)),
            Column("x", Integer),
            mysql_engine="InnoDB",
        )
        with self.conn.begin():
            t1.create(self.conn)

            self.conn.execute(
                t1.insert(),
                [
                    {"id": 1, "data": "d1", "x": 5},
                    {"id": 2, "data": "22", "x": 6},
                    {"id": 3, "data": "8.5", "x": 7},
                    {"id": 4, "data": "9.46", "x": 8},
                    {"id": 5, "data": "d5", "x": 9},
                ],
            )
        context = MigrationContext.configure(self.conn)
        self.op = Operations(context)

    def tearDown(self):
        # why commit?  because SQLite has inconsistent treatment
        # of transactional DDL. A test that runs CREATE TABLE and then
        # ALTER TABLE to change the name of that table, will end up
        # committing the CREATE TABLE but not the ALTER. As batch mode
        # does this with a temp table name that's not even in the
        # metadata collection, we don't have an explicit drop for it
        # (though we could do that too).  calling commit means the
        # ALTER will go through and the drop_all() will then catch it.
        _safe_commit_connection_transaction(self.conn)
        with self.conn.begin():
            self.metadata.drop_all(self.conn)
        self.conn.close()

    @contextmanager
    def _sqlite_referential_integrity(self):
        self.conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        try:
            yield
        finally:
            self.conn.exec_driver_sql("PRAGMA foreign_keys=OFF")

            # as these tests are typically intentional fails, clean out
            # tables left over
            m = MetaData()
            m.reflect(self.conn)
            with self.conn.begin():
                m.drop_all(self.conn)

    def _no_pk_fixture(self):
        with self.conn.begin():
            nopk = Table(
                "nopk",
                self.metadata,
                Column("a", Integer),
                Column("b", Integer),
                Column("c", Integer),
                mysql_engine="InnoDB",
            )
            nopk.create(self.conn)
            self.conn.execute(
                nopk.insert(),
                [{"a": 1, "b": 2, "c": 3}, {"a": 2, "b": 4, "c": 5}],
            )
            return nopk

    def _table_w_index_fixture(self):
        with self.conn.begin():
            t = Table(
                "t_w_ix",
                self.metadata,
                Column("id", Integer, primary_key=True),
                Column("thing", Integer),
                Column("data", String(20)),
            )
            Index("ix_thing", t.c.thing)
            t.create(self.conn)
            return t

    def _boolean_fixture(self):
        with self.conn.begin():
            t = Table(
                "hasbool",
                self.metadata,
                Column("x", Boolean(create_constraint=True, name="ck1")),
                Column("y", Integer),
            )
            t.create(self.conn)

    def _timestamp_fixture(self):
        with self.conn.begin():
            t = Table("hasts", self.metadata, Column("x", DateTime()))
            t.create(self.conn)
            return t

    def _ck_constraint_fixture(self):
        with self.conn.begin():
            t = Table(
                "ck_table",
                self.metadata,
                Column("id", Integer, nullable=False),
                CheckConstraint("id is not NULL", name="ck"),
            )
            t.create(self.conn)
            return t

    def _datetime_server_default_fixture(self):
        return func.datetime("now", "localtime")

    def _timestamp_w_expr_default_fixture(self):
        with self.conn.begin():
            t = Table(
                "hasts",
                self.metadata,
                Column(
                    "x",
                    DateTime(),
                    server_default=self._datetime_server_default_fixture(),
                    nullable=False,
                ),
            )
            t.create(self.conn)
            return t

    def _int_to_boolean_fixture(self):
        with self.conn.begin():
            t = Table("hasbool", self.metadata, Column("x", Integer))
            t.create(self.conn)

    def test_change_type_boolean_to_int(self):
        self._boolean_fixture()
        with self.op.batch_alter_table("hasbool") as batch_op:
            batch_op.alter_column(
                "x",
                type_=Integer,
                existing_type=Boolean(create_constraint=True, name="ck1"),
            )
        insp = inspect(self.conn)

        eq_(
            [
                c["type"]._type_affinity
                for c in insp.get_columns("hasbool")
                if c["name"] == "x"
            ],
            [Integer],
        )

    def test_no_net_change_timestamp(self):
        t = self._timestamp_fixture()

        import datetime

        with self.conn.begin():
            self.conn.execute(
                t.insert(), {"x": datetime.datetime(2012, 5, 18, 15, 32, 5)}
            )

        with self.op.batch_alter_table("hasts") as batch_op:
            batch_op.alter_column("x", type_=DateTime())

        eq_(
            self.conn.execute(_select(t.c.x)).fetchall(),
            [(datetime.datetime(2012, 5, 18, 15, 32, 5),)],
        )

    def test_no_net_change_timestamp_w_default(self):
        t = self._timestamp_w_expr_default_fixture()

        with self.op.batch_alter_table("hasts") as batch_op:
            batch_op.alter_column(
                "x",
                type_=DateTime(),
                nullable=False,
                server_default=self._datetime_server_default_fixture(),
            )

        with self.conn.begin():
            self.conn.execute(t.insert())
        res = self.conn.execute(_select(t.c.x))
        if sqla_14:
            assert res.scalar_one_or_none() is not None
        else:
            row = res.fetchone()
            assert row["x"] is not None

    def test_drop_col_schematype(self):
        self._boolean_fixture()
        with self.op.batch_alter_table("hasbool") as batch_op:
            batch_op.drop_column(
                "x", existing_type=Boolean(create_constraint=True, name="ck1")
            )
        insp = inspect(self.conn)

        assert "x" not in (c["name"] for c in insp.get_columns("hasbool"))

    def test_change_type_int_to_boolean(self):
        self._int_to_boolean_fixture()
        with self.op.batch_alter_table("hasbool") as batch_op:
            batch_op.alter_column(
                "x", type_=Boolean(create_constraint=True, name="ck1")
            )
        insp = inspect(self.conn)

        if exclusions.against(config, "sqlite"):
            eq_(
                [
                    c["type"]._type_affinity
                    for c in insp.get_columns("hasbool")
                    if c["name"] == "x"
                ],
                [Boolean],
            )
        elif exclusions.against(config, "mysql"):
            eq_(
                [
                    c["type"]._type_affinity
                    for c in insp.get_columns("hasbool")
                    if c["name"] == "x"
                ],
                [Integer],
            )

    def _assert_data(self, data, tablename="foo"):
        res = self.conn.execute(text("select * from %s" % tablename))
        if sqla_14:
            res = res.mappings()
        eq_([dict(row) for row in res], data)

    def test_ix_existing(self):
        self._table_w_index_fixture()

        with self.op.batch_alter_table("t_w_ix") as batch_op:
            batch_op.alter_column("data", type_=String(30))
            batch_op.create_index("ix_data", ["data"])

        insp = inspect(self.conn)
        eq_(
            {
                (ix["name"], tuple(ix["column_names"]))
                for ix in insp.get_indexes("t_w_ix")
            },
            {("ix_data", ("data",)), ("ix_thing", ("thing",))},
        )

    def test_fk_points_to_me_auto(self):
        self._test_fk_points_to_me("auto")

    # in particular, this tests that the failures
    # on PG and MySQL result in recovery of the batch system,
    # e.g. that the _alembic_tmp_temp table is dropped
    @config.requirements.no_referential_integrity
    def test_fk_points_to_me_recreate(self):
        self._test_fk_points_to_me("always")

    @exclusions.only_on("sqlite")
    @exclusions.fails(
        "intentionally asserting that this "
        "doesn't work w/ pragma foreign keys"
    )
    def test_fk_points_to_me_sqlite_refinteg(self):
        with self._sqlite_referential_integrity():
            self._test_fk_points_to_me("auto")

    def _test_fk_points_to_me(self, recreate):
        bar = Table(
            "bar",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("foo_id", Integer, ForeignKey("foo.id")),
            mysql_engine="InnoDB",
        )
        with self.conn.begin():
            bar.create(self.conn)
            self.conn.execute(bar.insert(), {"id": 1, "foo_id": 3})

        with self.op.batch_alter_table("foo", recreate=recreate) as batch_op:
            batch_op.alter_column(
                "data", new_column_name="newdata", existing_type=String(50)
            )

        insp = inspect(self.conn)
        eq_(
            [
                (
                    key["referred_table"],
                    key["referred_columns"],
                    key["constrained_columns"],
                )
                for key in insp.get_foreign_keys("bar")
            ],
            [("foo", ["id"], ["foo_id"])],
        )

    def test_selfref_fk_auto(self):
        self._test_selfref_fk("auto")

    @config.requirements.no_referential_integrity
    def test_selfref_fk_recreate(self):
        self._test_selfref_fk("always")

    @exclusions.only_on("sqlite")
    @exclusions.fails(
        "intentionally asserting that this "
        "doesn't work w/ pragma foreign keys"
    )
    def test_selfref_fk_sqlite_refinteg(self):
        with self._sqlite_referential_integrity():
            self._test_selfref_fk("auto")

    def _test_selfref_fk(self, recreate):
        bar = Table(
            "bar",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("bar_id", Integer, ForeignKey("bar.id")),
            Column("data", String(50)),
            mysql_engine="InnoDB",
        )
        with self.conn.begin():
            bar.create(self.conn)
            self.conn.execute(
                bar.insert(), {"id": 1, "data": "x", "bar_id": None}
            )
            self.conn.execute(
                bar.insert(), {"id": 2, "data": "y", "bar_id": 1}
            )

        with self.op.batch_alter_table("bar", recreate=recreate) as batch_op:
            batch_op.alter_column(
                "data", new_column_name="newdata", existing_type=String(50)
            )

        insp = inspect(self.conn)

        eq_(
            [
                (
                    key["referred_table"],
                    key["referred_columns"],
                    key["constrained_columns"],
                )
                for key in insp.get_foreign_keys("bar")
            ],
            [("bar", ["id"], ["bar_id"])],
        )

    def test_change_type(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.alter_column("data", type_=Integer)

        self._assert_data(
            [
                {"id": 1, "data": 0, "x": 5},
                {"id": 2, "data": 22, "x": 6},
                {"id": 3, "data": 8, "x": 7},
                {"id": 4, "data": 9, "x": 8},
                {"id": 5, "data": 0, "x": 9},
            ]
        )

    def test_drop_column(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.drop_column("data")

        self._assert_data(
            [
                {"id": 1, "x": 5},
                {"id": 2, "x": 6},
                {"id": 3, "x": 7},
                {"id": 4, "x": 8},
                {"id": 5, "x": 9},
            ]
        )

    def test_drop_pk_col_readd_col(self):
        # drop a column, add it back without primary_key=True, should no
        # longer be in the constraint
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.drop_column("id")
            batch_op.add_column(Column("id", Integer))

        pk_const = inspect(self.conn).get_pk_constraint("foo")
        eq_(pk_const["constrained_columns"], [])

    def test_drop_pk_col_readd_pk_col(self):
        # drop a column, add it back with primary_key=True, should remain
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.drop_column("id")
            batch_op.add_column(Column("id", Integer, primary_key=True))

        pk_const = inspect(self.conn).get_pk_constraint("foo")
        eq_(pk_const["constrained_columns"], ["id"])

    def test_drop_pk_col_readd_col_also_pk_const(self):
        # drop a column, add it back without primary_key=True, but then
        # also make anew PK constraint that includes it, should remain
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.drop_column("id")
            batch_op.add_column(Column("id", Integer))
            batch_op.create_primary_key("newpk", ["id"])

        pk_const = inspect(self.conn).get_pk_constraint("foo")
        eq_(pk_const["constrained_columns"], ["id"])

    @testing.combinations(("always",), ("auto",), argnames="recreate")
    def test_add_pk_constraint(self, recreate):
        self._no_pk_fixture()
        with self.op.batch_alter_table("nopk", recreate=recreate) as batch_op:
            batch_op.create_primary_key("newpk", ["a", "b"])

        pk_const = inspect(self.conn).get_pk_constraint("nopk")
        with config.requirements.reflects_pk_names.fail_if():
            eq_(pk_const["name"], "newpk")
        eq_(pk_const["constrained_columns"], ["a", "b"])

    @testing.combinations(("always",), ("auto",), argnames="recreate")
    @config.requirements.check_constraint_reflection
    def test_add_ck_constraint(self, recreate):
        with self.op.batch_alter_table("foo", recreate=recreate) as batch_op:
            batch_op.create_check_constraint("newck", text("x > 0"))

        ck_consts = inspect(self.conn).get_check_constraints("foo")
        ck_consts[0]["sqltext"] = re.sub(
            r"[\'\"`\(\)]", "", ck_consts[0]["sqltext"]
        )
        for ck in ck_consts:
            ck.pop("comment", None)
        eq_(ck_consts, [{"sqltext": "x > 0", "name": "newck"}])

    @testing.combinations(("always",), ("auto",), argnames="recreate")
    @config.requirements.check_constraint_reflection
    def test_drop_ck_constraint(self, recreate):
        self._ck_constraint_fixture()

        with self.op.batch_alter_table(
            "ck_table", recreate=recreate
        ) as batch_op:
            batch_op.drop_constraint("ck", "check")

        ck_consts = inspect(self.conn).get_check_constraints("ck_table")
        eq_(ck_consts, [])

    @config.requirements.unnamed_constraints
    def test_drop_foreign_key(self):
        bar = Table(
            "bar",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("foo_id", Integer, ForeignKey("foo.id")),
            mysql_engine="InnoDB",
        )
        with self.conn.begin():
            bar.create(self.conn)
            self.conn.execute(bar.insert(), {"id": 1, "foo_id": 3})

        naming_convention = {
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
        }
        with self.op.batch_alter_table(
            "bar", naming_convention=naming_convention
        ) as batch_op:
            batch_op.drop_constraint("fk_bar_foo_id_foo", type_="foreignkey")
        eq_(inspect(self.conn).get_foreign_keys("bar"), [])

    def test_drop_column_fk_recreate(self):
        with self.op.batch_alter_table("foo", recreate="always") as batch_op:
            batch_op.drop_column("data")

        self._assert_data(
            [
                {"id": 1, "x": 5},
                {"id": 2, "x": 6},
                {"id": 3, "x": 7},
                {"id": 4, "x": 8},
                {"id": 5, "x": 9},
            ]
        )

    def _assert_table_comment(self, tname, comment):
        insp = inspect(self.conn)

        tcomment = insp.get_table_comment(tname)
        eq_(tcomment, {"text": comment})

    @testing.combinations(("always",), ("auto",), argnames="recreate")
    def test_add_uq(self, recreate):
        with self.op.batch_alter_table("foo", recreate=recreate) as batch_op:
            batch_op.create_unique_constraint("newuk", ["x"])

        uq_consts = inspect(self.conn).get_unique_constraints("foo")
        eq_(
            [
                {"name": uc["name"], "column_names": uc["column_names"]}
                for uc in uq_consts
            ],
            [{"name": "newuk", "column_names": ["x"]}],
        )

    @testing.combinations(("always",), ("auto",), argnames="recreate")
    def test_add_uq_plus_col(self, recreate):
        with self.op.batch_alter_table("foo", recreate=recreate) as batch_op:
            batch_op.add_column(Column("y", Integer))
            batch_op.create_unique_constraint("newuk", ["x", "y"])

        uq_consts = inspect(self.conn).get_unique_constraints("foo")

        eq_(
            [
                {"name": uc["name"], "column_names": uc["column_names"]}
                for uc in uq_consts
            ],
            [{"name": "newuk", "column_names": ["x", "y"]}],
        )

    @config.requirements.comments
    def test_add_table_comment(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.create_table_comment("some comment")

        self._assert_table_comment("foo", "some comment")

        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.create_table_comment(
                "some new comment", existing_comment="some comment"
            )

        self._assert_table_comment("foo", "some new comment")

    @config.requirements.comments
    def test_drop_table_comment(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.create_table_comment("some comment")

        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.drop_table_comment(existing_comment="some comment")

        self._assert_table_comment("foo", None)

    def _assert_column_comment(self, tname, cname, comment):
        insp = inspect(self.conn)

        cols = {col["name"]: col for col in insp.get_columns(tname)}
        eq_(cols[cname]["comment"], comment)

    @config.requirements.comments
    def test_add_column_comment(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.add_column(Column("y", Integer, comment="some comment"))

        self._assert_column_comment("foo", "y", "some comment")

        self._assert_data(
            [
                {"id": 1, "data": "d1", "x": 5, "y": None},
                {"id": 2, "data": "22", "x": 6, "y": None},
                {"id": 3, "data": "8.5", "x": 7, "y": None},
                {"id": 4, "data": "9.46", "x": 8, "y": None},
                {"id": 5, "data": "d5", "x": 9, "y": None},
            ]
        )

    @config.requirements.comments
    def test_add_column_comment_recreate(self):
        with self.op.batch_alter_table("foo", recreate="always") as batch_op:
            batch_op.add_column(Column("y", Integer, comment="some comment"))

        self._assert_column_comment("foo", "y", "some comment")

        self._assert_data(
            [
                {"id": 1, "data": "d1", "x": 5, "y": None},
                {"id": 2, "data": "22", "x": 6, "y": None},
                {"id": 3, "data": "8.5", "x": 7, "y": None},
                {"id": 4, "data": "9.46", "x": 8, "y": None},
                {"id": 5, "data": "d5", "x": 9, "y": None},
            ]
        )

    @config.requirements.comments
    def test_alter_column_comment(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.alter_column(
                "x", existing_type=Integer(), comment="some comment"
            )

        self._assert_column_comment("foo", "x", "some comment")

        self._assert_data(
            [
                {"id": 1, "data": "d1", "x": 5},
                {"id": 2, "data": "22", "x": 6},
                {"id": 3, "data": "8.5", "x": 7},
                {"id": 4, "data": "9.46", "x": 8},
                {"id": 5, "data": "d5", "x": 9},
            ]
        )

    @config.requirements.comments
    def test_alter_column_comment_recreate(self):
        with self.op.batch_alter_table("foo", recreate="always") as batch_op:
            batch_op.alter_column("x", comment="some comment")

        self._assert_column_comment("foo", "x", "some comment")

        self._assert_data(
            [
                {"id": 1, "data": "d1", "x": 5},
                {"id": 2, "data": "22", "x": 6},
                {"id": 3, "data": "8.5", "x": 7},
                {"id": 4, "data": "9.46", "x": 8},
                {"id": 5, "data": "d5", "x": 9},
            ]
        )

    def test_rename_column(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.alter_column("x", new_column_name="y")

        self._assert_data(
            [
                {"id": 1, "data": "d1", "y": 5},
                {"id": 2, "data": "22", "y": 6},
                {"id": 3, "data": "8.5", "y": 7},
                {"id": 4, "data": "9.46", "y": 8},
                {"id": 5, "data": "d5", "y": 9},
            ]
        )

    def test_rename_column_boolean(self):
        bar = Table(
            "bar",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("flag", Boolean(create_constraint=True)),
            mysql_engine="InnoDB",
        )
        with self.conn.begin():
            bar.create(self.conn)
            self.conn.execute(bar.insert(), {"id": 1, "flag": True})
            self.conn.execute(bar.insert(), {"id": 2, "flag": False})

        with self.op.batch_alter_table("bar") as batch_op:
            batch_op.alter_column(
                "flag", new_column_name="bflag", existing_type=Boolean
            )

        self._assert_data(
            [{"id": 1, "bflag": True}, {"id": 2, "bflag": False}], "bar"
        )

    #    @config.requirements.check_constraint_reflection
    def test_rename_column_boolean_named_ck(self):
        bar = Table(
            "bar",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("flag", Boolean(create_constraint=True, name="ck1")),
            mysql_engine="InnoDB",
        )
        with self.conn.begin():
            bar.create(self.conn)
            self.conn.execute(bar.insert(), {"id": 1, "flag": True})
            self.conn.execute(bar.insert(), {"id": 2, "flag": False})

        with self.op.batch_alter_table("bar", recreate="always") as batch_op:
            batch_op.alter_column(
                "flag",
                new_column_name="bflag",
                existing_type=Boolean(create_constraint=True, name="ck1"),
            )

        self._assert_data(
            [{"id": 1, "bflag": True}, {"id": 2, "bflag": False}], "bar"
        )

    @config.requirements.non_native_boolean
    def test_rename_column_non_native_boolean_no_ck(self):
        bar = Table(
            "bar",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("flag", Boolean(create_constraint=False)),
            mysql_engine="InnoDB",
        )
        with self.conn.begin():
            bar.create(self.conn)
            self.conn.execute(bar.insert(), {"id": 1, "flag": True})
            self.conn.execute(bar.insert(), {"id": 2, "flag": False})
            self.conn.execute(
                # override Boolean type which as of 1.1 coerces numerics
                # to 1/0
                text("insert into bar (id, flag) values (:id, :flag)"),
                {"id": 3, "flag": 5},
            )

        with self.op.batch_alter_table(
            "bar",
            reflect_args=[Column("flag", Boolean(create_constraint=False))],
        ) as batch_op:
            batch_op.alter_column(
                "flag", new_column_name="bflag", existing_type=Boolean
            )

        self._assert_data(
            [
                {"id": 1, "bflag": True},
                {"id": 2, "bflag": False},
                {"id": 3, "bflag": 5},
            ],
            "bar",
        )

    def test_drop_column_pk(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.drop_column("id")

        self._assert_data(
            [
                {"data": "d1", "x": 5},
                {"data": "22", "x": 6},
                {"data": "8.5", "x": 7},
                {"data": "9.46", "x": 8},
                {"data": "d5", "x": 9},
            ]
        )

    def test_rename_column_pk(self):
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.alter_column("id", new_column_name="ident")

        self._assert_data(
            [
                {"ident": 1, "data": "d1", "x": 5},
                {"ident": 2, "data": "22", "x": 6},
                {"ident": 3, "data": "8.5", "x": 7},
                {"ident": 4, "data": "9.46", "x": 8},
                {"ident": 5, "data": "d5", "x": 9},
            ]
        )

    def test_add_column_auto(self):
        # note this uses ALTER
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.add_column(
                Column("data2", String(50), server_default="hi")
            )

        self._assert_data(
            [
                {"id": 1, "data": "d1", "x": 5, "data2": "hi"},
                {"id": 2, "data": "22", "x": 6, "data2": "hi"},
                {"id": 3, "data": "8.5", "x": 7, "data2": "hi"},
                {"id": 4, "data": "9.46", "x": 8, "data2": "hi"},
                {"id": 5, "data": "d5", "x": 9, "data2": "hi"},
            ]
        )
        eq_(
            [col["name"] for col in inspect(config.db).get_columns("foo")],
            ["id", "data", "x", "data2"],
        )

    def test_add_column_auto_server_default_calculated(self):
        """test #883"""
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.add_column(
                Column(
                    "data2",
                    DateTime(),
                    server_default=self._datetime_server_default_fixture(),
                )
            )

        self._assert_data(
            [
                {"id": 1, "data": "d1", "x": 5, "data2": mock.ANY},
                {"id": 2, "data": "22", "x": 6, "data2": mock.ANY},
                {"id": 3, "data": "8.5", "x": 7, "data2": mock.ANY},
                {"id": 4, "data": "9.46", "x": 8, "data2": mock.ANY},
                {"id": 5, "data": "d5", "x": 9, "data2": mock.ANY},
            ]
        )
        eq_(
            [col["name"] for col in inspect(self.conn).get_columns("foo")],
            ["id", "data", "x", "data2"],
        )

    @testing.combinations((True,), (False,))
    @testing.exclusions.only_on("sqlite")
    @config.requirements.computed_columns
    def test_add_column_auto_generated(self, persisted):
        """test #883"""
        with self.op.batch_alter_table("foo") as batch_op:
            batch_op.add_column(
                Column(
                    "data2", Integer, Computed("1 + 1", persisted=persisted)
                )
            )

        self._assert_data(
            [
                {"id": 1, "data": "d1", "x": 5, "data2": 2},
                {"id": 2, "data": "22", "x": 6, "data2": 2},
                {"id": 3, "data": "8.5", "x": 7, "data2": 2},
                {"id": 4, "data": "9.46", "x": 8, "data2": 2},
                {"id": 5, "data": "d5", "x": 9, "data2": 2},
            ]
        )
        eq_(
            [col["name"] for col in inspect(self.conn).get_columns("foo")],
            ["id", "data", "x", "data2"],
        )

    @config.requirements.identity_columns
    def test_add_column_auto_identity(self):
        """test #883"""

        self._no_pk_fixture()

        with self.op.batch_alter_table("nopk") as batch_op:
            batch_op.add_column(Column("id", Integer, Identity()))

        self._assert_data(
            [
                {"a": 1, "b": 2, "c": 3, "id": 1},
                {"a": 2, "b": 4, "c": 5, "id": 2},
            ],
            tablename="nopk",
        )
        eq_(
            [col["name"] for col in inspect(self.conn).get_columns("foo")],
            ["id", "data", "x"],
        )

    def test_add_column_insert_before_recreate(self):
        with self.op.batch_alter_table("foo", recreate="always") as batch_op:
            batch_op.add_column(
                Column("data2", String(50), server_default="hi"),
                insert_before="data",
            )
        self._assert_data(
            [
                {"id": 1, "data": "d1", "x": 5, "data2": "hi"},
                {"id": 2, "data": "22", "x": 6, "data2": "hi"},
                {"id": 3, "data": "8.5", "x": 7, "data2": "hi"},
                {"id": 4, "data": "9.46", "x": 8, "data2": "hi"},
                {"id": 5, "data": "d5", "x": 9, "data2": "hi"},
            ]
        )
        eq_(
            [col["name"] for col in inspect(self.conn).get_columns("foo")],
            ["id", "data2", "data", "x"],
        )

    def test_add_column_insert_after_recreate(self):
        with self.op.batch_alter_table("foo", recreate="always") as batch_op:
            batch_op.add_column(
                Column("data2", String(50), server_default="hi"),
                insert_after="data",
            )
        self._assert_data(
            [
                {"id": 1, "data": "d1", "x": 5, "data2": "hi"},
                {"id": 2, "data": "22", "x": 6, "data2": "hi"},
                {"id": 3, "data": "8.5", "x": 7, "data2": "hi"},
                {"id": 4, "data": "9.46", "x": 8, "data2": "hi"},
                {"id": 5, "data": "d5", "x": 9, "data2": "hi"},
            ]
        )
        eq_(
            [col["name"] for col in inspect(self.conn).get_columns("foo")],
            ["id", "data", "data2", "x"],
        )

    def test_add_column_insert_before_raise_on_alter(self):
        def go():
            with self.op.batch_alter_table("foo") as batch_op:
                batch_op.add_column(
                    Column("data2", String(50), server_default="hi"),
                    insert_before="data",
                )

        assert_raises_message(
            alembic_exc.CommandError,
            "Can't specify insert_before or insert_after when using ALTER",
            go,
        )

    def test_add_column_recreate(self):
        with self.op.batch_alter_table("foo", recreate="always") as batch_op:
            batch_op.add_column(
                Column("data2", String(50), server_default="hi")
            )

        self._assert_data(
            [
                {"id": 1, "data": "d1", "x": 5, "data2": "hi"},
                {"id": 2, "data": "22", "x": 6, "data2": "hi"},
                {"id": 3, "data": "8.5", "x": 7, "data2": "hi"},
                {"id": 4, "data": "9.46", "x": 8, "data2": "hi"},
                {"id": 5, "data": "d5", "x": 9, "data2": "hi"},
            ]
        )
        eq_(
            [col["name"] for col in inspect(self.conn).get_columns("foo")],
            ["id", "data", "x", "data2"],
        )

    def test_create_drop_index(self):
        insp = inspect(self.conn)
        eq_(insp.get_indexes("foo"), [])

        with self.op.batch_alter_table("foo", recreate="always") as batch_op:
            batch_op.create_index("ix_data", ["data"], unique=True)

        self._assert_data(
            [
                {"id": 1, "data": "d1", "x": 5},
                {"id": 2, "data": "22", "x": 6},
                {"id": 3, "data": "8.5", "x": 7},
                {"id": 4, "data": "9.46", "x": 8},
                {"id": 5, "data": "d5", "x": 9},
            ]
        )
        insp = inspect(self.conn)
        eq_(
            [
                dict(
                    unique=ix["unique"],
                    name=ix["name"],
                    column_names=ix["column_names"],
                )
                for ix in insp.get_indexes("foo")
            ],
            [{"unique": True, "name": "ix_data", "column_names": ["data"]}],
        )

        with self.op.batch_alter_table("foo", recreate="always") as batch_op:
            batch_op.drop_index("ix_data")

        insp = inspect(self.conn)
        eq_(insp.get_indexes("foo"), [])


class BatchRoundTripMySQLTest(BatchRoundTripTest):
    __only_on__ = "mysql", "mariadb"
    __backend__ = True

    def _datetime_server_default_fixture(self):
        return func.current_timestamp()

    @exclusions.fails()
    def test_drop_pk_col_readd_pk_col(self):
        super().test_drop_pk_col_readd_pk_col()

    @exclusions.fails()
    def test_drop_pk_col_readd_col_also_pk_const(self):
        super().test_drop_pk_col_readd_col_also_pk_const()

    @exclusions.fails()
    def test_rename_column_pk(self):
        super().test_rename_column_pk()

    @exclusions.fails()
    def test_rename_column(self):
        super().test_rename_column()

    @exclusions.fails()
    def test_change_type(self):
        super().test_change_type()

    def test_create_drop_index(self):
        super().test_create_drop_index()

    # fails on mariadb 10.2, succeeds on 10.3
    @exclusions.fails_if(config.requirements.mysql_check_col_name_change)
    def test_rename_column_boolean(self):
        super().test_rename_column_boolean()

    def test_change_type_boolean_to_int(self):
        super().test_change_type_boolean_to_int()

    def test_change_type_int_to_boolean(self):
        super().test_change_type_int_to_boolean()


class BatchRoundTripPostgresqlTest(BatchRoundTripTest):
    __only_on__ = "postgresql"
    __backend__ = True

    def _native_boolean_fixture(self):
        t = Table(
            "has_native_bool",
            self.metadata,
            Column(
                "x",
                Boolean(create_constraint=True),
                server_default="false",
                nullable=False,
            ),
            Column("y", Integer),
        )
        with self.conn.begin():
            t.create(self.conn)

    def _datetime_server_default_fixture(self):
        return func.current_timestamp()

    @exclusions.fails()
    def test_drop_pk_col_readd_pk_col(self):
        super().test_drop_pk_col_readd_pk_col()

    @exclusions.fails()
    def test_drop_pk_col_readd_col_also_pk_const(self):
        super().test_drop_pk_col_readd_col_also_pk_const()

    @exclusions.fails()
    def test_change_type(self):
        super().test_change_type()

    def test_create_drop_index(self):
        super().test_create_drop_index()

    @exclusions.fails()
    def test_change_type_int_to_boolean(self):
        super().test_change_type_int_to_boolean()

    @exclusions.fails()
    def test_change_type_boolean_to_int(self):
        super().test_change_type_boolean_to_int()

    def test_add_col_table_has_native_boolean(self):
        self._native_boolean_fixture()

        # to ensure test coverage on SQLAlchemy 1.4 and above,
        # force the create_constraint flag to True even though it
        # defaults to false in 1.4.  this test wants to ensure that the
        # "should create" rule is consulted
        def listen_for_reflect(inspector, table, column_info):
            if isinstance(column_info["type"], Boolean):
                column_info["type"].create_constraint = True

        with self.op.batch_alter_table(
            "has_native_bool",
            recreate="always",
            reflect_kwargs={
                "listeners": [("column_reflect", listen_for_reflect)]
            },
        ) as batch_op:
            batch_op.add_column(Column("data", Integer))

        insp = inspect(self.conn)

        eq_(
            [
                c["type"]._type_affinity
                for c in insp.get_columns("has_native_bool")
                if c["name"] == "data"
            ],
            [Integer],
        )
        eq_(
            [
                c["type"]._type_affinity
                for c in insp.get_columns("has_native_bool")
                if c["name"] == "x"
            ],
            [Boolean],
        )


class OfflineTest(TestBase):
    @testing.fixture
    def no_reflect_batch_fixture(self):
        staging_env()

        def go():
            self.cfg = cfg = _no_sql_testing_config(dialect="sqlite")

            self.a = a = util.rev_id()

            script = ScriptDirectory.from_config(cfg)
            script.generate_revision(
                a, "revision a", refresh=True, head="base"
            )
            write_script(
                script,
                a,
                """\
    "Rev A"
    revision = '%s'
    down_revision = None

    from alembic import op
    from sqlalchemy import Column
    from sqlalchemy import Integer
    from sqlalchemy import String, Table, MetaData

    some_table_up = Table(
        "some_table", MetaData(),
        Column('id', Integer),
        Column('bar', String)
    )

    some_table_down = Table(
        "some_table", MetaData(),
        Column('id', Integer),
        Column('foo', Integer)
    )

    def upgrade():
        with op.batch_alter_table("some_table", copy_from=some_table_up) as batch_op:
            batch_op.add_column(Column('foo', Integer))
            batch_op.drop_column('bar')

    def downgrade():
        with op.batch_alter_table("some_table", copy_from=some_table_down) as batch_op:
            batch_op.drop_column('foo')
            batch_op.add_column(Column('bar', String))

    """  # noqa: E501
                % a,
            )

        yield go
        clear_staging_env()

    @testing.fixture
    def batch_fixture(self):
        staging_env()

        def go(dialect):
            self.cfg = cfg = _no_sql_testing_config(dialect=dialect)

            self.a = a = util.rev_id()

            script = ScriptDirectory.from_config(cfg)
            script.generate_revision(
                a, "revision a", refresh=True, head="base"
            )
            write_script(
                script,
                a,
                """\
    "Rev A"
    revision = '%s'
    down_revision = None

    from alembic import op
    from sqlalchemy import Column
    from sqlalchemy import Integer
    from sqlalchemy import String

    def upgrade():
        with op.batch_alter_table("some_table") as batch_op:
            batch_op.add_column(Column('foo', Integer))
            batch_op.drop_column('bar')

    def downgrade():
        with op.batch_alter_table("some_table") as batch_op:
            batch_op.drop_column('foo')
            batch_op.add_column(Column('bar', String))

    """
                % a,
            )

        yield go
        clear_staging_env()

    def test_upgrade_non_batch(self, batch_fixture):
        batch_fixture("postgresql")

        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.a, sql=True)

        assert re.search(
            r"ALTER TABLE some_table ADD COLUMN foo INTEGER", buf.getvalue()
        )

    def test_downgrade_non_batch(self, batch_fixture):
        batch_fixture("postgresql")

        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, f"{self.a}:base", sql=True)
        assert re.search(
            r"ALTER TABLE some_table DROP COLUMN foo", buf.getvalue()
        )

    def test_upgrade_batch_fails_gracefully(self, batch_fixture):
        batch_fixture("sqlite")

        with expect_raises_message(
            CommandError,
            "This operation cannot proceed in --sql mode; batch mode with "
            "dialect sqlite requires a live database connection with which "
            'to reflect the table "some_table"',
        ):
            command.upgrade(self.cfg, self.a, sql=True)

    def test_downgrade_batch_fails_gracefully(self, batch_fixture):
        batch_fixture("sqlite")

        with expect_raises_message(
            CommandError,
            "This operation cannot proceed in --sql mode; batch mode with "
            "dialect sqlite requires a live database connection with which "
            'to reflect the table "some_table"',
        ):
            command.downgrade(self.cfg, f"{self.a}:base", sql=True)

    def test_upgrade_batch_no_reflection(self, no_reflect_batch_fixture):
        no_reflect_batch_fixture()

        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.a, sql=True)

        assert re.search(
            r"CREATE TABLE _alembic_tmp_some_table", buf.getvalue()
        )

    def test_downgrade_batch_no_reflection(self, no_reflect_batch_fixture):
        no_reflect_batch_fixture()

        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, f"{self.a}:base", sql=True)

        assert re.search(
            r"CREATE TABLE _alembic_tmp_some_table", buf.getvalue()
        )
