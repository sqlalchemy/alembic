"""Test registration and lookup of DefaultImpl subclasses by dialect name."""

import contextlib
import re
from types import SimpleNamespace
from unittest import mock
import warnings

from sqlalchemy.dialects import registry
from sqlalchemy.engine import default

from alembic import command
from alembic import testing
from alembic import util
from alembic.ddl import impl
from alembic.ddl.impl import BaseImpl
from alembic.ddl.impl import DefaultImpl
from alembic.ddl.postgresql import PostgresqlImpl
from alembic.migration import MigrationContext
from alembic.testing import eq_
from alembic.testing import expect_raises
from alembic.testing import expect_raises_message
from alembic.testing import expect_warnings
from alembic.testing import is_
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import clear_staging_env
from alembic.testing.env import env_file_fixture
from alembic.testing.env import staging_env
from alembic.testing.env import three_rev_fixture
from alembic.testing.fixtures import capture_context_buffer
from alembic.testing.fixtures import TestBase

CONFLICT_WARNING = r"Dialect .* has an implementation .* available via entry point"  # noqa: E501


def _dialect(name):
    return type("D", (default.DefaultDialect,), {"name": name})()


def _library(hook=None):
    """Return a loader standing in for the import of a third party module.

    The class is created the first time the loader is called and that same
    class is returned afterwards, as a real import would.

    """
    created = []

    def load():
        if not created:
            attrs = {"__dialect__": "newdb"}
            if hook is not None:
                attrs["resolve_registration_conflict"] = classmethod(hook)
            created.append(type("LibraryNewDbImpl", (DefaultImpl,), attrs))
        return created[0]

    return load


@contextlib.contextmanager
def _no_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        yield


@contextlib.contextmanager
def _record_warnings():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        yield caught


def _conflict_warnings(caught):
    return [w for w in caught if re.match(CONFLICT_WARNING, str(w.message))]


class _RegistryFixture(TestBase):
    @testing.fixture(scope="function", autouse=True)
    def _restore_registry(self):
        impls = BaseImpl._impls.copy()
        cache = impl._entrypoint_cache.copy()

        # other tests may already have looked up a dialect name; start each
        # test as though no entry points have been consulted yet
        impl._entrypoint_cache.clear()

        yield

        BaseImpl._impls.clear()
        BaseImpl._impls.update(impls)
        impl._entrypoint_cache.clear()
        impl._entrypoint_cache.update(cache)

    @contextlib.contextmanager
    def _entry_points(self, **loaders):
        """Patch entry point discovery for the ``alembic.dialects`` group.

        Each loader is called when its entry point is loaded, standing in for
        the import of the module that defines the implementation.

        """
        entry_points = [
            SimpleNamespace(name=name, load=load)
            for name, load in loaders.items()
        ]

        def entry_points_(group=None, name=None, **kw):
            if group != "alembic.dialects":
                return []
            return [ep for ep in entry_points if ep.name == name]

        with mock.patch(
            "alembic.ddl.impl.metadata.entry_points",
            side_effect=entry_points_,
        ) as patched:
            yield patched


class RegistrationTest(_RegistryFixture):
    def test_subclass_registers(self):
        class NewDbImpl(DefaultImpl):
            __dialect__ = "newdb"

        is_(BaseImpl._impls["newdb"], NewDbImpl)

    def test_helper_subclass_does_not_register(self):
        class NewDbImpl(DefaultImpl):
            __dialect__ = "newdb"

        class Helper(NewDbImpl):
            pass

        class SharedBase(DefaultImpl):
            pass

        is_(BaseImpl._impls["newdb"], NewDbImpl)
        is_(BaseImpl._impls["default"], DefaultImpl)

    def test_redeclaration_replaces_quietly(self):
        class NewDbImpl(DefaultImpl):
            __dialect__ = "newdb"

        with _no_warnings():

            class OtherNewDbImpl(DefaultImpl):
                __dialect__ = "newdb"

        is_(BaseImpl._impls["newdb"], OtherNewDbImpl)

    def test_builtins_registered(self):
        eq_(
            {
                "default",
                "mariadb",
                "mssql",
                "mysql",
                "oracle",
                "postgresql",
                "sqlite",
            }
            - set(BaseImpl._impls),
            set(),
        )

    def test_module_level_impls_alias(self):
        is_(impl._impls, BaseImpl._impls)

    def test_unknown_dialect_raises(self):
        with self._entry_points():
            with expect_raises_message(
                util.NoSuchDialectError,
                "Implementation for dialect 'nosuchdb' not found",
            ):
                DefaultImpl.get_by_dialect(_dialect("nosuchdb"))

    def test_unknown_dialect_raises_from_migration_context(self):
        with self._entry_points():
            with expect_raises(util.CommandError):
                MigrationContext.configure(dialect=_dialect("nosuchdb"))


class EntryPointTest(_RegistryFixture):
    def test_entry_point_loaded(self):
        load = _library()

        with self._entry_points(newdb=load):
            result = DefaultImpl.get_by_dialect(_dialect("newdb"))

        is_(result, load())

    def test_entry_point_used_by_migration_context(self):
        load = _library()

        with self._entry_points(newdb=load):
            ctx = MigrationContext.configure(dialect=_dialect("newdb"))

        is_(type(ctx.impl), load())

    def test_entry_point_loaded_once(self):
        load = mock.Mock(wraps=_library())

        with self._entry_points(newdb=load):
            first = DefaultImpl.get_by_dialect(_dialect("newdb"))
            second = DefaultImpl.get_by_dialect(_dialect("newdb"))

        is_(first, second)
        eq_(load.call_count, 1)

    def test_entry_point_ignored_for_builtin_dialect(self):
        load = mock.Mock(side_effect=AssertionError("should not be loaded"))

        with self._entry_points(postgresql=load) as patched:
            result = DefaultImpl.get_by_dialect(_dialect("postgresql"))

        is_(result, PostgresqlImpl)
        eq_(patched.call_count, 0)

    def test_declared_impl_wins_with_warning(self):
        class UserNewDbImpl(DefaultImpl):
            __dialect__ = "newdb"

        with self._entry_points(newdb=_library()):
            with expect_warnings(CONFLICT_WARNING):
                result = DefaultImpl.get_by_dialect(_dialect("newdb"))

        is_(result, UserNewDbImpl)

    def test_declared_subclass_is_quiet(self):
        load = _library()

        class CustomNewDbImpl(load()):
            __dialect__ = "newdb"

        with self._entry_points(newdb=load):
            with _no_warnings():
                result = DefaultImpl.get_by_dialect(_dialect("newdb"))

        is_(result, CustomNewDbImpl)

    @testing.variation("hook_on", ["library", "declared"])
    def test_hook_resolves_conflict(self, hook_on):
        def prefers_self(cls, other):
            return cls

        class UserNewDbImpl(DefaultImpl):
            __dialect__ = "newdb"

            if hook_on.declared:
                resolve_registration_conflict = classmethod(prefers_self)

        load = _library(hook=prefers_self if hook_on.library else None)

        with self._entry_points(newdb=load):
            with _no_warnings():
                result = DefaultImpl.get_by_dialect(_dialect("newdb"))

        is_(result, load() if hook_on.library else UserNewDbImpl)

    def test_broken_entry_point_raises_every_time(self):
        def load():
            raise ImportError("No module named 'newdb_sqlalchemy.alembic'")

        with self._entry_points(newdb=load):
            for _ in range(2):
                with expect_raises(ImportError):
                    DefaultImpl.get_by_dialect(_dialect("newdb"))


registry.register("newdb", __name__, "NewDbDialect")


class NewDbDialect(default.DefaultDialect):
    name = "newdb"
    supports_statement_cache = True


class MultipleCommandsTest(_RegistryFixture):
    """Run several commands in one process, as test suites and programmatic
    users of :mod:`alembic.command` do.

    ``env.py`` is executed again for every command, so an implementation
    declared there is a new class each time, whereas an entry point
    implementation is loaded once per process.  The implementation selected
    and the warnings emitted should be the same for the third command as for
    the first.

    """

    env_py_impl = """
from alembic.ddl.impl import DefaultImpl

class NewDbImpl(DefaultImpl):
    __dialect__ = "newdb"

config.attributes["defined"].append(NewDbImpl)
"""

    env_py_subclass = """
class CustomNewDbImpl(config.attributes["library"]()):
    __dialect__ = "newdb"

config.attributes["defined"].append(CustomNewDbImpl)
"""

    def setUp(self):
        staging_env()
        self.cfg = _no_sql_testing_config(dialect="newdb")
        self.cfg.attributes.update(defined=[], used=[])
        self.a, self.b, self.c = three_rev_fixture(self.cfg)

    def tearDown(self):
        clear_staging_env()

    def _write_env(self, declare_impl):
        env_file_fixture(declare_impl + """
context.configure(
    url=config.get_main_option("sqlalchemy.url"), literal_binds=True
)
config.attributes["used"].append(type(context.get_context().impl))
with context.begin_transaction():
    context.run_migrations()
""")

    def _run_three_commands(self):
        for cmd, rev in [
            (command.upgrade, "head"),
            (command.downgrade, f"{self.c}:{self.a}"),
            (command.upgrade, f"{self.a}:head"),
        ]:
            with capture_context_buffer():
                cmd(self.cfg, rev, sql=True)

    def test_env_py_impl_without_entry_point(self):
        self._write_env(self.env_py_impl)

        with self._entry_points():
            with _record_warnings() as caught:
                self._run_three_commands()

        eq_(_conflict_warnings(caught), [])
        eq_(len(self.cfg.attributes["used"]), 3)
        eq_(self.cfg.attributes["used"], self.cfg.attributes["defined"])

    @testing.variation("env_impl", ["none", "unrelated", "subclass"])
    def test_same_impl_for_every_command(self, env_impl):
        library = _library()
        self.cfg.attributes["library"] = library

        if env_impl.unrelated:
            self._write_env(self.env_py_impl)
        elif env_impl.subclass:
            self._write_env(self.env_py_subclass)
        else:
            self._write_env("")

        with self._entry_points(newdb=library):
            with _record_warnings() as caught:
                self._run_three_commands()

        used = self.cfg.attributes["used"]
        defined = self.cfg.attributes["defined"]
        eq_(len(used), 3)

        if env_impl.none:
            eq_(used, [library()] * 3)
            eq_(_conflict_warnings(caught), [])
        elif env_impl.unrelated:
            # the declared impl wins, with a warning, on every command
            eq_(used, defined)
            eq_(len(_conflict_warnings(caught)), 3)
        else:
            eq_(used, defined)
            eq_(_conflict_warnings(caught), [])
