from sqlalchemy import CHAR
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import event
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy import text
from sqlalchemy import UniqueConstraint
from sqlalchemy.engine.reflection import Inspector

from alembic import autogenerate
from alembic import util
from alembic.autogenerate import api
from alembic.ddl.base import _fk_spec
from alembic.migration import MigrationContext
from alembic.operations import ops
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env

names_in_this_test = set()


@event.listens_for(Table, "after_parent_attach")
def new_table(table, parent):
    names_in_this_test.add(table.name)


def _default_include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in names_in_this_test
    else:
        return True


_default_object_filters = _default_include_object


class ModelOne(object):
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


class _ComparesFKs(object):
    def _assert_fk_diff(
        self,
        diff,
        type_,
        source_table,
        source_columns,
        target_table,
        target_columns,
        name=None,
        conditional_name=None,
        source_schema=None,
        onupdate=None,
        ondelete=None,
        initially=None,
        deferrable=None,
    ):
        # the public API for ForeignKeyConstraint was not very rich
        # in 0.7, 0.8, so here we use the well-known but slightly
        # private API to get at its elements
        (
            fk_source_schema,
            fk_source_table,
            fk_source_columns,
            fk_target_schema,
            fk_target_table,
            fk_target_columns,
            fk_onupdate,
            fk_ondelete,
            fk_deferrable,
            fk_initially,
        ) = _fk_spec(diff[1])

        eq_(diff[0], type_)
        eq_(fk_source_table, source_table)
        eq_(fk_source_columns, source_columns)
        eq_(fk_target_table, target_table)
        eq_(fk_source_schema, source_schema)
        eq_(fk_onupdate, onupdate)
        eq_(fk_ondelete, ondelete)
        eq_(fk_initially, initially)
        eq_(fk_deferrable, deferrable)

        eq_([elem.column.name for elem in diff[1].elements], target_columns)
        if conditional_name is not None:
            if config.requirements.no_fk_names.enabled:
                eq_(diff[1].name, None)
            elif conditional_name == "servergenerated":
                fks = Inspector.from_engine(self.bind).get_foreign_keys(
                    source_table
                )
                server_fk_name = fks[0]["name"]
                eq_(diff[1].name, server_fk_name)
            else:
                eq_(diff[1].name, conditional_name)
        else:
            eq_(diff[1].name, name)


class AutogenTest(_ComparesFKs):
    def _flatten_diffs(self, diffs):
        for d in diffs:
            if isinstance(d, list):
                for fd in self._flatten_diffs(d):
                    yield fd
            else:
                yield d

    @classmethod
    def _get_bind(cls):
        return config.db

    configure_opts = {}

    @classmethod
    def setup_class(cls):
        staging_env()
        cls.bind = cls._get_bind()
        cls.m1 = cls._get_db_schema()
        cls.m1.create_all(cls.bind)
        cls.m2 = cls._get_model_schema()

    @classmethod
    def teardown_class(cls):
        cls.m1.drop_all(cls.bind)
        clear_staging_env()

    def setUp(self):
        self.conn = conn = self.bind.connect()
        ctx_opts = {
            "compare_type": True,
            "compare_server_default": True,
            "target_metadata": self.m2,
            "upgrade_token": "upgrades",
            "downgrade_token": "downgrades",
            "alembic_module_prefix": "op.",
            "sqlalchemy_module_prefix": "sa.",
            "include_object": _default_object_filters,
        }
        if self.configure_opts:
            ctx_opts.update(self.configure_opts)
        self.context = context = MigrationContext.configure(
            connection=conn, opts=ctx_opts
        )

        self.autogen_context = api.AutogenContext(context, self.m2)

    def tearDown(self):
        self.conn.close()

    def _update_context(self, object_filters=None, include_schemas=None):
        if include_schemas is not None:
            self.autogen_context.opts["include_schemas"] = include_schemas
        if object_filters is not None:
            self.autogen_context._object_filters = [object_filters]
        return self.autogen_context


class AutogenFixtureTest(_ComparesFKs):
    def _fixture(
        self,
        m1,
        m2,
        include_schemas=False,
        opts=None,
        object_filters=_default_object_filters,
        return_ops=False,
    ):
        self.metadata, model_metadata = m1, m2
        for m in util.to_list(self.metadata):
            m.create_all(self.bind)

        with self.bind.connect() as conn:
            ctx_opts = {
                "compare_type": True,
                "compare_server_default": True,
                "target_metadata": model_metadata,
                "upgrade_token": "upgrades",
                "downgrade_token": "downgrades",
                "alembic_module_prefix": "op.",
                "sqlalchemy_module_prefix": "sa.",
                "include_object": object_filters,
                "include_schemas": include_schemas,
            }
            if opts:
                ctx_opts.update(opts)
            self.context = context = MigrationContext.configure(
                connection=conn, opts=ctx_opts
            )

            autogen_context = api.AutogenContext(context, model_metadata)
            uo = ops.UpgradeOps(ops=[])
            autogenerate._produce_net_changes(autogen_context, uo)

            if return_ops:
                return uo
            else:
                return uo.as_diffs()

    reports_unnamed_constraints = False

    def setUp(self):
        staging_env()
        self.bind = config.db

    def tearDown(self):
        if hasattr(self, "metadata"):
            for m in util.to_list(self.metadata):
                m.drop_all(self.bind)
        clear_staging_env()
