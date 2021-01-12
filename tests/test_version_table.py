from sqlalchemy import Column
from sqlalchemy import inspect
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table

from alembic import migration
from alembic.testing import assert_raises
from alembic.testing import assert_raises_message
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import mock
from alembic.testing.fixtures import TestBase
from alembic.util import CommandError

version_table = Table(
    "version_table",
    MetaData(),
    Column("version_num", String(32), nullable=False),
)


def _up(from_, to_, branch_presence_changed=False):
    return migration.StampStep(from_, to_, True, branch_presence_changed)


def _down(from_, to_, branch_presence_changed=False):
    return migration.StampStep(from_, to_, False, branch_presence_changed)


class TestMigrationContext(TestBase):
    @classmethod
    def setup_class(cls):
        cls.bind = config.db

    def setUp(self):
        self.connection = self.bind.connect()
        self.transaction = self.connection.begin()

    def tearDown(self):
        self.transaction.rollback()
        with self.connection.begin():
            version_table.drop(self.connection, checkfirst=True)
        self.connection.close()

    def make_one(self, **kwargs):
        return migration.MigrationContext.configure(**kwargs)

    def get_revision(self):
        result = self.connection.execute(version_table.select())
        rows = result.fetchall()
        if len(rows) == 0:
            return None
        eq_(len(rows), 1)
        return rows[0]["version_num"]

    def test_config_default_version_table_name(self):
        context = self.make_one(dialect_name="sqlite")
        eq_(context._version.name, "alembic_version")

    def test_config_explicit_version_table_name(self):
        context = self.make_one(
            dialect_name="sqlite", opts={"version_table": "explicit"}
        )
        eq_(context._version.name, "explicit")
        eq_(context._version.primary_key.name, "explicit_pkc")

    def test_config_explicit_version_table_schema(self):
        context = self.make_one(
            dialect_name="sqlite", opts={"version_table_schema": "explicit"}
        )
        eq_(context._version.schema, "explicit")

    def test_config_explicit_no_pk(self):
        context = self.make_one(
            dialect_name="sqlite", opts={"version_table_pk": False}
        )
        eq_(len(context._version.primary_key), 0)

    def test_config_explicit_w_pk(self):
        context = self.make_one(
            dialect_name="sqlite", opts={"version_table_pk": True}
        )
        eq_(len(context._version.primary_key), 1)
        eq_(context._version.primary_key.name, "alembic_version_pkc")

    def test_get_current_revision_doesnt_create_version_table(self):
        context = self.make_one(
            connection=self.connection, opts={"version_table": "version_table"}
        )
        eq_(context.get_current_revision(), None)
        insp = inspect(self.connection)
        assert "version_table" not in insp.get_table_names()

    def test_get_current_revision(self):
        context = self.make_one(
            connection=self.connection, opts={"version_table": "version_table"}
        )
        version_table.create(self.connection)
        eq_(context.get_current_revision(), None)
        self.connection.execute(
            version_table.insert().values(version_num="revid")
        )
        eq_(context.get_current_revision(), "revid")

    def test_get_current_revision_error_if_starting_rev_given_online(self):
        context = self.make_one(
            connection=self.connection, opts={"starting_rev": "boo"}
        )
        assert_raises(CommandError, context.get_current_revision)

    def test_get_current_revision_offline(self):
        context = self.make_one(
            dialect_name="sqlite",
            opts={"starting_rev": "startrev", "as_sql": True},
        )
        eq_(context.get_current_revision(), "startrev")

    def test_get_current_revision_multiple_heads(self):
        version_table.create(self.connection)
        context = self.make_one(
            connection=self.connection, opts={"version_table": "version_table"}
        )
        updater = migration.HeadMaintainer(context, ())
        updater.update_to_step(_up(None, "a", True))
        updater.update_to_step(_up(None, "b", True))
        assert_raises_message(
            CommandError,
            "Version table 'version_table' has more than one head present; "
            "please use get_current_heads()",
            context.get_current_revision,
        )

    def test_get_heads(self):
        version_table.create(self.connection)
        context = self.make_one(
            connection=self.connection, opts={"version_table": "version_table"}
        )
        updater = migration.HeadMaintainer(context, ())
        updater.update_to_step(_up(None, "a", True))
        updater.update_to_step(_up(None, "b", True))
        eq_(context.get_current_heads(), ("a", "b"))

    def test_get_heads_offline(self):
        version_table.create(self.connection)
        context = self.make_one(
            connection=self.connection,
            opts={
                "starting_rev": "q",
                "version_table": "version_table",
                "as_sql": True,
            },
        )
        eq_(context.get_current_heads(), ("q",))

    def test_stamp_api_creates_table(self):
        context = self.make_one(connection=self.connection)
        assert (
            "alembic_version" not in inspect(self.connection).get_table_names()
        )

        script = mock.Mock(
            _stamp_revs=lambda revision, heads: [
                _up(None, "a", True),
                _up(None, "b", True),
            ]
        )

        context.stamp(script, "b")
        eq_(context.get_current_heads(), ("a", "b"))
        assert "alembic_version" in inspect(self.connection).get_table_names()


class UpdateRevTest(TestBase):
    __backend__ = True

    @classmethod
    def setup_class(cls):
        cls.bind = config.db

    def setUp(self):
        self.connection = self.bind.connect()
        self.context = migration.MigrationContext.configure(
            connection=self.connection, opts={"version_table": "version_table"}
        )
        with self.connection.begin():
            version_table.create(self.connection)
        self.updater = migration.HeadMaintainer(self.context, ())

    def tearDown(self):
        in_t = getattr(self.connection, "in_transaction", lambda: False)
        if in_t():
            self.connection.rollback()
        with self.connection.begin():
            version_table.drop(self.connection, checkfirst=True)
        self.connection.close()

    def _assert_heads(self, heads):
        eq_(set(self.context.get_current_heads()), set(heads))
        eq_(self.updater.heads, set(heads))

    def test_update_none_to_single(self):
        with self.connection.begin():
            self.updater.update_to_step(_up(None, "a", True))
            self._assert_heads(("a",))

    def test_update_single_to_single(self):
        with self.connection.begin():
            self.updater.update_to_step(_up(None, "a", True))
            self.updater.update_to_step(_up("a", "b"))
            self._assert_heads(("b",))

    def test_update_single_to_none(self):
        with self.connection.begin():
            self.updater.update_to_step(_up(None, "a", True))
            self.updater.update_to_step(_down("a", None, True))
            self._assert_heads(())

    def test_add_branches(self):
        with self.connection.begin():
            self.updater.update_to_step(_up(None, "a", True))
            self.updater.update_to_step(_up("a", "b"))
            self.updater.update_to_step(_up(None, "c", True))
            self._assert_heads(("b", "c"))
            self.updater.update_to_step(_up("c", "d"))
            self.updater.update_to_step(_up("d", "e1"))
            self.updater.update_to_step(_up("d", "e2", True))
            self._assert_heads(("b", "e1", "e2"))

    def test_teardown_branches(self):
        with self.connection.begin():
            self.updater.update_to_step(_up(None, "d1", True))
            self.updater.update_to_step(_up(None, "d2", True))
            self._assert_heads(("d1", "d2"))

            self.updater.update_to_step(_down("d1", "c"))
            self._assert_heads(("c", "d2"))

            self.updater.update_to_step(_down("d2", "c", True))

            self._assert_heads(("c",))
            self.updater.update_to_step(_down("c", "b"))
            self._assert_heads(("b",))

    def test_resolve_merges(self):
        with self.connection.begin():
            self.updater.update_to_step(_up(None, "a", True))
            self.updater.update_to_step(_up("a", "b"))
            self.updater.update_to_step(_up("b", "c1"))
            self.updater.update_to_step(_up("b", "c2", True))
            self.updater.update_to_step(_up("c1", "d1"))
            self.updater.update_to_step(_up("c2", "d2"))
            self._assert_heads(("d1", "d2"))
            self.updater.update_to_step(_up(("d1", "d2"), "e"))
            self._assert_heads(("e",))

    def test_unresolve_merges(self):
        with self.connection.begin():
            self.updater.update_to_step(_up(None, "e", True))

            self.updater.update_to_step(_down("e", ("d1", "d2")))
            self._assert_heads(("d2", "d1"))

            self.updater.update_to_step(_down("d2", "c2"))
            self._assert_heads(("c2", "d1"))

    def test_update_no_match(self):
        with self.connection.begin():
            self.updater.update_to_step(_up(None, "a", True))
            self.updater.heads.add("x")
            assert_raises_message(
                CommandError,
                "Online migration expected to match one row when updating "
                "'x' to 'b' in 'version_table'; 0 found",
                self.updater.update_to_step,
                _up("x", "b"),
            )

    def test_update_no_match_no_sane_rowcount(self):
        with self.connection.begin():
            self.updater.update_to_step(_up(None, "a", True))
            self.updater.heads.add("x")
            with mock.patch.object(
                self.connection.dialect, "supports_sane_rowcount", False
            ):
                self.updater.update_to_step(_up("x", "b"))

    def test_update_multi_match(self):
        with self.connection.begin():
            self.connection.execute(
                version_table.insert(), dict(version_num="a")
            )
            self.connection.execute(
                version_table.insert(), dict(version_num="a")
            )

            self.updater.heads.add("a")
            assert_raises_message(
                CommandError,
                "Online migration expected to match one row when updating "
                "'a' to 'b' in 'version_table'; 2 found",
                self.updater.update_to_step,
                _up("a", "b"),
            )

    def test_update_multi_match_no_sane_rowcount(self):
        with self.connection.begin():
            self.connection.execute(
                version_table.insert(), dict(version_num="a")
            )
            self.connection.execute(
                version_table.insert(), dict(version_num="a")
            )

            self.updater.heads.add("a")
            with mock.patch.object(
                self.connection.dialect, "supports_sane_rowcount", False
            ):
                self.updater.update_to_step(_up("a", "b"))

    def test_delete_no_match(self):
        with self.connection.begin():
            self.updater.update_to_step(_up(None, "a", True))

            self.updater.heads.add("x")
            assert_raises_message(
                CommandError,
                "Online migration expected to match one row when "
                "deleting 'x' in 'version_table'; 0 found",
                self.updater.update_to_step,
                _down("x", None, True),
            )

    def test_delete_no_matchno_sane_rowcount(self):
        with self.connection.begin():
            self.updater.update_to_step(_up(None, "a", True))

            self.updater.heads.add("x")
            with mock.patch.object(
                self.connection.dialect, "supports_sane_rowcount", False
            ):
                self.updater.update_to_step(_down("x", None, True))

    def test_delete_multi_match(self):
        with self.connection.begin():
            self.connection.execute(
                version_table.insert(), dict(version_num="a")
            )
            self.connection.execute(
                version_table.insert(), dict(version_num="a")
            )

            self.updater.heads.add("a")
            assert_raises_message(
                CommandError,
                "Online migration expected to match one row when "
                "deleting 'a' in 'version_table'; 2 found",
                self.updater.update_to_step,
                _down("a", None, True),
            )

    def test_delete_multi_match_no_sane_rowcount(self):
        with self.connection.begin():
            self.connection.execute(
                version_table.insert(), dict(version_num="a")
            )
            self.connection.execute(
                version_table.insert(), dict(version_num="a")
            )

            self.updater.heads.add("a")
            with mock.patch.object(
                self.connection.dialect, "supports_sane_rowcount", False
            ):
                self.updater.update_to_step(_down("a", None, True))
