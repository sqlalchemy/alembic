"""Test registration and lookup of DefaultImpl subclasses by dialect name."""

import contextlib
from types import SimpleNamespace
from unittest import mock
import warnings

from sqlalchemy.engine import default

from alembic import testing
from alembic import util
from alembic.ddl import impl
from alembic.ddl.impl import DefaultImpl
from alembic.ddl.impl import RegisterImpl
from alembic.migration import MigrationContext
from alembic.testing import eq_
from alembic.testing import expect_raises
from alembic.testing import expect_raises_message
from alembic.testing import expect_warnings
from alembic.testing import is_
from alembic.testing.fixtures import TestBase

OVERWRITE_WARNING = "Overwriting existing registered implementation"


def _dialect(name):
    return type("D", (default.DefaultDialect,), {"name": name})()


@contextlib.contextmanager
def _no_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        yield


class _RegistryFixture(TestBase):
    @testing.fixture(scope="function", autouse=True)
    def _restore_registry(self):
        impls = RegisterImpl._impls.copy()
        checked = impl._entrypoints_checked.copy()
        loaders = impl.registry.impls.copy()

        # other tests may already have looked up a dialect name; start each
        # test as though no entry points have been consulted yet
        impl._entrypoints_checked.clear()
        impl.registry.impls.clear()

        yield

        RegisterImpl._impls.clear()
        RegisterImpl._impls.update(impls)
        impl._entrypoints_checked.clear()
        impl._entrypoints_checked.update(checked)
        impl.registry.impls.clear()
        impl.registry.impls.update(loaders)

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

        def importlib_metadata_get(group):
            return entry_points if group == "alembic.dialects" else []

        with mock.patch(
            "sqlalchemy.util.compat.importlib_metadata_get",
            side_effect=importlib_metadata_get,
        ) as patched:
            yield patched


class RegistrationTest(_RegistryFixture):
    def test_subclass_registers(self):
        class NewDbImpl(DefaultImpl):
            __dialect__ = "newdb"

        is_(RegisterImpl._impls["newdb"], NewDbImpl)

    def test_inherited_dialect_registers(self):
        class NewDbImpl(DefaultImpl):
            __dialect__ = "newdb"

        with _no_warnings():

            class Helper(NewDbImpl):
                pass

        is_(RegisterImpl._impls["newdb"], Helper)

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
            - set(RegisterImpl._impls),
            set(),
        )

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

    def test_conflict_with_subclass_does_not_warn(self):
        class NewDbImpl(DefaultImpl):
            __dialect__ = "newdb"

        with _no_warnings():

            class CustomNewDbImpl(NewDbImpl):
                __dialect__ = "newdb"

        is_(RegisterImpl._impls["newdb"], CustomNewDbImpl)

    def test_conflict_with_non_subclass_warns(self):
        class NewDbImpl(DefaultImpl):
            __dialect__ = "newdb"

        with expect_warnings(OVERWRITE_WARNING):

            class OtherNewDbImpl(DefaultImpl):
                __dialect__ = "newdb"

        is_(RegisterImpl._impls["newdb"], OtherNewDbImpl)


class ConflictHookTest(_RegistryFixture):
    def _keeps_other(self):
        """Make a class whose hook always keeps the other implementation."""

        class KeepsOther(DefaultImpl):
            @classmethod
            def resolve_registration_conflict(cls, new, existing):
                return existing if new is cls else new

        return KeepsOther

    def test_hook_receives_new_and_existing(self):
        calls = []

        class NewDbImpl(DefaultImpl):
            __dialect__ = "newdb"

            @classmethod
            def resolve_registration_conflict(cls, new, existing):
                calls.append((cls, new, existing))
                return None

        with expect_warnings(OVERWRITE_WARNING):

            class OtherNewDbImpl(DefaultImpl):
                __dialect__ = "newdb"

        eq_(calls, [(NewDbImpl, OtherNewDbImpl, NewDbImpl)])

    @testing.variation("hook_on", ["existing", "new"])
    def test_hook_decides(self, hook_on):
        KeepsOther = self._keeps_other()
        first_base = KeepsOther if hook_on.existing else DefaultImpl
        second_base = KeepsOther if hook_on.new else DefaultImpl

        first = type("First", (first_base,), {"__dialect__": "newdb"})
        with _no_warnings():
            second = type("Second", (second_base,), {"__dialect__": "newdb"})

        # the class with the hook keeps the other one, whichever side it is on
        is_(
            RegisterImpl._impls["newdb"], second if hook_on.existing else first
        )

    @testing.variation("hook_on", ["existing", "new", "both"])
    def test_hook_returning_none_is_default(self, hook_on):
        class SuperOnly(DefaultImpl):
            @classmethod
            def resolve_registration_conflict(cls, new, existing):
                return super().resolve_registration_conflict(new, existing)

        first_base = SuperOnly if not hook_on.new else DefaultImpl
        second_base = SuperOnly if not hook_on.existing else DefaultImpl

        type("First", (first_base,), {"__dialect__": "newdb"})
        with expect_warnings(OVERWRITE_WARNING):
            second = type("Second", (second_base,), {"__dialect__": "newdb"})

        is_(RegisterImpl._impls["newdb"], second)

    def test_both_hooks_newcomer_asked_first(self):
        class PrefersSelf(DefaultImpl):
            @classmethod
            def resolve_registration_conflict(cls, new, existing):
                return cls

        type("First", (PrefersSelf,), {"__dialect__": "newdb"})
        second = type("Second", (PrefersSelf,), {"__dialect__": "newdb"})

        is_(RegisterImpl._impls["newdb"], second)


class EntryPointTest(_RegistryFixture):
    def test_entry_point_loaded(self):
        def load():
            class NewDbImpl(DefaultImpl):
                __dialect__ = "newdb"

            return NewDbImpl

        with self._entry_points(newdb=load):
            result = DefaultImpl.get_by_dialect(_dialect("newdb"))

        eq_(result.__name__, "NewDbImpl")
        is_(RegisterImpl._impls["newdb"], result)

    def test_entry_point_used_by_migration_context(self):
        def load():
            class NewDbImpl(DefaultImpl):
                __dialect__ = "newdb"

            return NewDbImpl

        with self._entry_points(newdb=load):
            ctx = MigrationContext.configure(dialect=_dialect("newdb"))

        eq_(type(ctx.impl).__name__, "NewDbImpl")

    def test_entry_points_scanned_once_on_hit(self):
        def load():
            class NewDbImpl(DefaultImpl):
                __dialect__ = "newdb"

            return NewDbImpl

        with self._entry_points(newdb=load) as patched:
            first = DefaultImpl.get_by_dialect(_dialect("newdb"))
            second = DefaultImpl.get_by_dialect(_dialect("newdb"))

        is_(first, second)
        eq_(patched.call_count, 1)

    def test_entry_points_scanned_once_on_miss(self):
        with self._entry_points() as patched:
            for _ in range(2):
                with expect_raises(util.NoSuchDialectError):
                    DefaultImpl.get_by_dialect(_dialect("nosuchdb"))

        eq_(patched.call_count, 1)

    def test_entry_point_conflicts_with_env_py_impl(self):
        class UserNewDbImpl(DefaultImpl):
            __dialect__ = "newdb"

        def load():
            class LibraryNewDbImpl(DefaultImpl):
                __dialect__ = "newdb"

            return LibraryNewDbImpl

        with self._entry_points(newdb=load):
            with expect_warnings(OVERWRITE_WARNING):
                result = DefaultImpl.get_by_dialect(_dialect("newdb"))

        eq_(result.__name__, "LibraryNewDbImpl")

    def test_entry_point_hook_keeps_env_py_impl(self):
        class UserNewDbImpl(DefaultImpl):
            __dialect__ = "newdb"

        def load():
            class LibraryNewDbImpl(DefaultImpl):
                __dialect__ = "newdb"

                @classmethod
                def resolve_registration_conflict(cls, new, existing):
                    return existing if new is cls else new

            return LibraryNewDbImpl

        with self._entry_points(newdb=load):
            with _no_warnings():
                result = DefaultImpl.get_by_dialect(_dialect("newdb"))

        is_(result, UserNewDbImpl)

    def test_entry_point_for_builtin_subclass_replaces_quietly(self):
        from alembic.ddl.postgresql import PostgresqlImpl

        def load():
            class BetterPostgresqlImpl(PostgresqlImpl):
                __dialect__ = "postgresql"

            return BetterPostgresqlImpl

        with self._entry_points(postgresql=load):
            with _no_warnings():
                result = DefaultImpl.get_by_dialect(_dialect("postgresql"))

        eq_(result.__name__, "BetterPostgresqlImpl")

    def test_broken_entry_point_propagates(self):
        def load():
            raise AttributeError("module has no attribute 'NewDbImpl'")

        with self._entry_points(newdb=load):
            with expect_raises(AttributeError):
                DefaultImpl.get_by_dialect(_dialect("newdb"))
