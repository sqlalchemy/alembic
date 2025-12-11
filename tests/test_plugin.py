"""Test the Plugin class and plugin system."""

from types import ModuleType
from unittest import mock

from alembic import testing
from alembic import util
from alembic.runtime.plugins import _all_plugins
from alembic.runtime.plugins import _make_re
from alembic.runtime.plugins import Plugin
from alembic.testing import eq_
from alembic.testing.fixtures import TestBase
from alembic.util import DispatchPriority
from alembic.util import PriorityDispatcher
from alembic.util import PriorityDispatchResult


class PluginTest(TestBase):
    """Tests for the Plugin class."""

    @testing.fixture(scope="function", autouse=True)
    def _clear_plugin_registry(self):
        """Clear plugin registry before each test and restore after."""
        # Save original plugins
        original_plugins = _all_plugins.copy()
        _all_plugins.clear()

        yield

        # Restore plugin registry after test
        _all_plugins.clear()
        _all_plugins.update(original_plugins)

    def test_plugin_creation(self):
        """Test basic plugin creation."""
        plugin = Plugin("test.plugin")
        eq_(plugin.name, "test.plugin")
        assert "test.plugin" in _all_plugins
        eq_(_all_plugins["test.plugin"], plugin)

    def test_plugin_creation_duplicate_raises(self):
        """Test that duplicate plugin names raise ValueError."""
        Plugin("test.plugin")
        with testing.expect_raises_message(
            ValueError, "A plugin named test.plugin is already registered"
        ):
            Plugin("test.plugin")

    def test_plugin_remove(self):
        """Test plugin removal."""
        plugin = Plugin("test.plugin")
        assert "test.plugin" in _all_plugins
        plugin.remove()
        assert "test.plugin" not in _all_plugins

    def test_add_autogenerate_comparator(self):
        """Test adding autogenerate comparison functions."""
        plugin = Plugin("test.plugin")

        def my_comparator():
            return PriorityDispatchResult.CONTINUE

        plugin.add_autogenerate_comparator(
            my_comparator,
            "table",
            "column",
            qualifier="postgresql",
            priority=DispatchPriority.FIRST,
        )

        # Verify it was registered in the dispatcher
        fn = plugin.autogenerate_comparators.dispatch(
            "table", qualifier="postgresql"
        )
        # The dispatcher returns a callable, call it to verify
        fn()

    def test_populate_autogenerate_priority_dispatch_simple(self):
        """Test populating dispatcher with simple include pattern."""
        plugin1 = Plugin("test.plugin1")
        plugin2 = Plugin("test.plugin2")

        mock1 = mock.Mock()
        mock2 = mock.Mock()

        plugin1.add_autogenerate_comparator(mock1, "test")
        plugin2.add_autogenerate_comparator(mock2, "test")

        dispatcher = PriorityDispatcher()
        Plugin.populate_autogenerate_priority_dispatch(
            dispatcher, ["test.plugin1"]
        )

        # Should have plugin1's handler, but not plugin2's
        fn = dispatcher.dispatch("test")
        fn()
        eq_(mock1.mock_calls, [mock.call()])
        eq_(mock2.mock_calls, [])

    def test_populate_autogenerate_priority_dispatch_wildcard(self):
        """Test populating dispatcher with wildcard pattern."""
        plugin1_alpha = Plugin("test.plugin1.alpha")
        plugin1_beta = Plugin("test.plugin1.beta")
        plugin2_gamma = Plugin("test.plugin2.gamma")

        mock_alpha = mock.Mock()
        mock_beta = mock.Mock()
        mock_gamma = mock.Mock()

        plugin1_alpha.add_autogenerate_comparator(mock_alpha, "test")
        plugin1_beta.add_autogenerate_comparator(mock_beta, "test")
        plugin2_gamma.add_autogenerate_comparator(mock_gamma, "test")

        dispatcher = PriorityDispatcher()
        Plugin.populate_autogenerate_priority_dispatch(
            dispatcher, ["test.plugin1.*"]
        )

        # Both test.plugin1.* should be included
        # test.plugin2.* should not be included
        fn = dispatcher.dispatch("test")
        fn()
        eq_(mock_alpha.mock_calls, [mock.call()])
        eq_(mock_beta.mock_calls, [mock.call()])
        eq_(mock_gamma.mock_calls, [])

    def test_populate_autogenerate_priority_dispatch_exclude(self):
        """Test populating dispatcher with exclude pattern."""
        plugin1 = Plugin("test.plugin1")
        plugin2 = Plugin("test.plugin2")

        mock1 = mock.Mock()
        mock2 = mock.Mock()

        plugin1.add_autogenerate_comparator(mock1, "test")
        plugin2.add_autogenerate_comparator(mock2, "test")

        dispatcher = PriorityDispatcher()
        Plugin.populate_autogenerate_priority_dispatch(
            dispatcher, ["test.*", "~test.plugin2"]
        )

        # Should have plugin1's handler, but not plugin2's (excluded)
        fn = dispatcher.dispatch("test")
        fn()
        eq_(mock1.mock_calls, [mock.call()])
        eq_(mock2.mock_calls, [])

    def test_populate_autogenerate_priority_dispatch_not_found(self):
        """Test that non-matching pattern raises error."""
        Plugin("test.plugin1")

        dispatcher = PriorityDispatcher()
        with testing.expect_raises_message(
            util.CommandError,
            "Did not locate plugins.*test.nonexistent",
        ):
            Plugin.populate_autogenerate_priority_dispatch(
                dispatcher, ["test.nonexistent"]
            )

    def test_populate_autogenerate_priority_dispatch_wildcard_not_found(
        self,
    ):
        """Test that non-matching wildcard pattern raises error."""
        Plugin("test.plugin1")

        dispatcher = PriorityDispatcher()
        with testing.expect_raises_message(
            util.CommandError,
            "Did not locate plugins",
        ):
            Plugin.populate_autogenerate_priority_dispatch(
                dispatcher, ["other.*"]
            )

    def test_populate_autogenerate_priority_dispatch_multiple_includes(self):
        """Test populating with multiple include patterns."""
        Plugin("test.plugin1")
        Plugin("other.plugin2")

        dispatcher = PriorityDispatcher()
        Plugin.populate_autogenerate_priority_dispatch(
            dispatcher, ["test.plugin1", "other.plugin2"]
        )
        # Should not raise error

    def test_setup_plugin_from_module(self):
        """Test setting up plugin from a module."""
        # Create a mock module with a setup function
        mock_module = ModuleType("mock_plugin")

        def setup(plugin):
            eq_(plugin.name, "mock.plugin")
            # Register a comparator to verify setup was called
            plugin.add_autogenerate_comparator(
                lambda: PriorityDispatchResult.CONTINUE,
                "test_target",
            )

        mock_module.setup = setup

        Plugin.setup_plugin_from_module(mock_module, "mock.plugin")

        # Verify plugin was created
        assert "mock.plugin" in _all_plugins

    def test_autogenerate_comparators_dispatcher(self):
        """Test that autogenerate_comparators is a PriorityDispatcher."""
        plugin = Plugin("test.plugin")
        assert isinstance(plugin.autogenerate_comparators, PriorityDispatcher)

    def test_populate_with_real_handlers(self):
        """Test populating dispatcher with actual comparison handlers."""
        plugin = Plugin("test.plugin")
        results = []

        def compare_tables(
            autogen_context, upgrade_ops, schemas
        ):  # pragma: no cover
            results.append(("compare_tables", autogen_context))
            return PriorityDispatchResult.CONTINUE

        def compare_types(
            autogen_context,
            alter_column_op,
            schema,
            tname,
            cname,
            conn_col,
            metadata_col,
        ):  # pragma: no cover
            results.append(("compare_types", tname))
            return PriorityDispatchResult.CONTINUE

        plugin.add_autogenerate_comparator(compare_tables, "table")
        plugin.add_autogenerate_comparator(compare_types, "type")

        dispatcher = PriorityDispatcher()
        Plugin.populate_autogenerate_priority_dispatch(
            dispatcher, ["test.plugin"]
        )

        # Verify handlers are in dispatcher
        fn_table = dispatcher.dispatch("table")
        fn_type = dispatcher.dispatch("type")

        # Call them to verify they work
        fn_table("autogen_ctx", "upgrade_ops", "schemas")
        fn_type(
            "autogen_ctx",
            "alter_op",
            "schema",
            "tablename",
            "colname",
            "conn_col",
            "meta_col",
        )

        eq_(results[0][0], "compare_tables")
        eq_(results[1][0], "compare_types")
        eq_(results[1][1], "tablename")


class MakeReTest(TestBase):
    """Tests for the _make_re helper function."""

    def test_simple_name(self):
        """Test regex generation for simple dotted names."""
        pattern = _make_re("test.plugin")
        assert pattern.match("test.plugin")

        # Partial matches dont work; use a * for this
        assert not pattern.match("test.plugin.extra")

        # other tokens don't match either
        assert not pattern.match("test.pluginfoo")

        assert not pattern.match("other.plugin")
        assert not pattern.match("test")

    def test_wildcard(self):
        """Test regex generation with wildcard."""
        pattern = _make_re("test.*")
        assert pattern.match("test.plugin")
        assert pattern.match("test.plugin.extra")
        assert not pattern.match("test")
        assert not pattern.match("other.plugin")

    def test_multiple_wildcards(self):
        """Test regex generation with multiple wildcards."""
        pattern = _make_re("test.*.sub.*")
        assert pattern.match("test.plugin.sub.item")
        assert pattern.match("test.a.sub.b")
        assert not pattern.match("test.plugin")

    def test_invalid_pattern_raises(self):
        """Test that invalid patterns raise ValueError."""
        with testing.expect_raises_message(
            ValueError, "Invalid plugin expression"
        ):
            _make_re("test.plugin-name")

    def test_valid_underscore(self):
        """Test that underscores are valid in names."""
        pattern = _make_re("test.my_plugin")
        assert pattern.match("test.my_plugin")

    def test_valid_mixed_case(self):
        """Test that mixed case is valid in names."""
        pattern = _make_re("test.MyPlugin")
        assert pattern.match("test.MyPlugin")
        assert not pattern.match("test.myplugin")
