"""Test the Dispatcher and PriorityDispatcher utilities."""

from alembic import testing
from alembic.testing import eq_
from alembic.testing.fixtures import TestBase
from alembic.util import Dispatcher
from alembic.util import DispatchPriority
from alembic.util import PriorityDispatcher
from alembic.util import PriorityDispatchResult


class DispatcherTest(TestBase):
    """Tests for the Dispatcher class."""

    def test_dispatch_for_decorator(self):
        """Test basic decorator registration."""
        dispatcher = Dispatcher()

        @dispatcher.dispatch_for("target1")
        def handler1():
            return "handler1"

        fn = dispatcher.dispatch("target1")
        eq_(fn(), "handler1")

    def test_dispatch_with_args_kwargs(self):
        """Test that arguments are passed through to handlers."""
        dispatcher = Dispatcher()

        @dispatcher.dispatch_for("target1")
        def handler(arg1, kwarg1=None):
            return (arg1, kwarg1)

        fn = dispatcher.dispatch("target1")
        result = fn("value1", kwarg1="value2")
        eq_(result, ("value1", "value2"))

    def test_dispatch_for_qualifier(self):
        """Test registration with qualifier."""
        dispatcher = Dispatcher()

        @dispatcher.dispatch_for("target1", qualifier="postgresql")
        def handler_pg():
            return "postgresql"

        @dispatcher.dispatch_for("target1", qualifier="default")
        def handler_default():
            return "default"

        fn_pg = dispatcher.dispatch("target1", qualifier="postgresql")
        eq_(fn_pg(), "postgresql")

        fn_default = dispatcher.dispatch("target1", qualifier="default")
        eq_(fn_default(), "default")

    def test_dispatch_qualifier_fallback(self):
        """Test that non-default qualifier falls back to default."""
        dispatcher = Dispatcher()

        @dispatcher.dispatch_for("target1")
        def handler_default():
            return "default"

        # Request with specific qualifier should fallback to default
        fn = dispatcher.dispatch("target1", qualifier="mysql")
        eq_(fn(), "default")

    def test_dispatch_type_target(self):
        """Test dispatching with type targets using MRO."""
        dispatcher = Dispatcher()

        class Base:
            pass

        class Child(Base):
            pass

        @dispatcher.dispatch_for(Base)
        def handler_base():
            return "base"

        # Dispatching with Child should find Base handler via MRO
        fn = dispatcher.dispatch(Child())
        eq_(fn(), "base")

    def test_dispatch_type_class_vs_instance(self):
        """Test dispatching with type vs instance."""
        dispatcher = Dispatcher()

        class MyClass:
            pass

        @dispatcher.dispatch_for(MyClass)
        def handler():
            return "handler"

        # Both class and instance should work
        fn_class = dispatcher.dispatch(MyClass)
        eq_(fn_class(), "handler")

        fn_instance = dispatcher.dispatch(MyClass())
        eq_(fn_instance(), "handler")

    def test_dispatch_no_match_raises(self):
        """Test that dispatching with no match raises ValueError."""
        dispatcher = Dispatcher()

        with testing.expect_raises_message(ValueError, "no dispatch function"):
            dispatcher.dispatch("nonexistent")

    def test_dispatch_replace_false_raises(self):
        """Test that duplicate registration raises ValueError."""
        dispatcher = Dispatcher()

        @dispatcher.dispatch_for("target1")
        def handler1():
            return "handler1"

        with testing.expect_raises_message(ValueError, "key already exists"):

            @dispatcher.dispatch_for("target1")
            def handler2():
                return "handler2"

    def test_dispatch_replace_true_works(self):
        """Test that replace=True allows overwriting."""
        dispatcher = Dispatcher()

        @dispatcher.dispatch_for("target1")
        def handler1():
            return "handler1"

        @dispatcher.dispatch_for("target1", replace=True)
        def handler2():
            return "handler2"

        fn = dispatcher.dispatch("target1")
        eq_(fn(), "handler2")

    def test_branch(self):
        """Test that branch creates independent copy."""
        dispatcher = Dispatcher()

        @dispatcher.dispatch_for("target1")
        def handler1():
            return "handler1"

        dispatcher2 = dispatcher.branch()

        # Add to branch should not affect original
        @dispatcher2.dispatch_for("target2")
        def handler2():
            return "handler2"

        # Original should not have target2
        with testing.expect_raises(ValueError):
            dispatcher.dispatch("target2")

        # Branch should have both
        fn1 = dispatcher2.dispatch("target1")
        eq_(fn1(), "handler1")
        fn2 = dispatcher2.dispatch("target2")
        eq_(fn2(), "handler2")


class PriorityDispatcherTest(TestBase):
    """Tests for the PriorityDispatcher class."""

    def test_dispatch_for_decorator(self):
        """Test basic decorator registration."""
        dispatcher = PriorityDispatcher()
        results = []

        @dispatcher.dispatch_for("target1")
        def handler1():
            results.append("handler1")

        fn = dispatcher.dispatch("target1")
        fn()
        eq_(results, ["handler1"])

    def test_dispatch_target_not_registered(self):
        """Test that dispatching unregistered target returns noop."""
        dispatcher = PriorityDispatcher()

        # Unlike regular Dispatcher, PriorityDispatcher returns a noop
        # function for unregistered targets
        fn = dispatcher.dispatch("nonexistent")
        # Should not raise, just return a callable that does nothing
        fn()

    def test_dispatch_with_priority(self):
        """Test that handlers execute in priority order."""
        dispatcher = PriorityDispatcher()
        results = []

        @dispatcher.dispatch_for("target1", priority=DispatchPriority.LAST)
        def handler_last():
            results.append("last")

        @dispatcher.dispatch_for("target1", priority=DispatchPriority.FIRST)
        def handler_first():
            results.append("first")

        @dispatcher.dispatch_for("target1", priority=DispatchPriority.MEDIUM)
        def handler_medium():
            results.append("medium")

        fn = dispatcher.dispatch("target1")
        fn()
        eq_(results, ["first", "medium", "last"])

    def test_dispatch_with_subgroup(self):
        """Test that subgroups track results independently."""
        dispatcher = PriorityDispatcher()
        results = []

        @dispatcher.dispatch_for("target1", subgroup="group1")
        def handler1():
            results.append("group1")
            return PriorityDispatchResult.CONTINUE

        @dispatcher.dispatch_for("target1", subgroup="group2")
        def handler2():
            results.append("group2")
            return PriorityDispatchResult.CONTINUE

        fn = dispatcher.dispatch("target1")
        fn()
        eq_(results, ["group1", "group2"])

    def test_dispatch_stop_result(self):
        """Test that STOP prevents further execution in subgroup."""
        dispatcher = PriorityDispatcher()
        results = []

        @dispatcher.dispatch_for(
            "target1", priority=DispatchPriority.FIRST, subgroup="group1"
        )
        def handler1():
            results.append("handler1")
            return PriorityDispatchResult.STOP

        @dispatcher.dispatch_for(
            "target1", priority=DispatchPriority.MEDIUM, subgroup="group1"
        )
        def handler2():
            results.append("handler2")  # Should not execute
            return PriorityDispatchResult.CONTINUE

        @dispatcher.dispatch_for(
            "target1", priority=DispatchPriority.FIRST, subgroup="group2"
        )
        def handler3():
            results.append("handler3")  # Should execute
            return PriorityDispatchResult.CONTINUE

        fn = dispatcher.dispatch("target1")
        fn()
        # handler2 should not run because handler1 returned STOP for group1
        # handler3 should run because it's in a different subgroup
        eq_(results, ["handler1", "handler3"])

    def test_dispatch_with_qualifier(self):
        """Test dispatching with qualifiers includes both specific and
        default."""
        dispatcher = PriorityDispatcher()
        results = []

        @dispatcher.dispatch_for("target1", qualifier="postgresql")
        def handler_pg():
            results.append("postgresql")

        @dispatcher.dispatch_for("target1", qualifier="default")
        def handler_default():
            results.append("default")

        fn_pg = dispatcher.dispatch("target1", qualifier="postgresql")
        fn_pg()
        # Should run both postgresql and default handlers
        eq_(results, ["postgresql", "default"])

    def test_dispatch_qualifier_fallback(self):
        """Test that non-default qualifier also executes default handlers."""
        dispatcher = PriorityDispatcher()
        results = []

        @dispatcher.dispatch_for("target1", qualifier="default")
        def handler_default():
            results.append("default")

        # Request with specific qualifier should also run default
        fn = dispatcher.dispatch("target1", qualifier="mysql")
        fn()
        eq_(results, ["default"])

    def test_dispatch_with_args_kwargs(self):
        """Test that arguments are passed through to handlers."""
        dispatcher = PriorityDispatcher()
        results = []

        @dispatcher.dispatch_for("target1")
        def handler(arg1, kwarg1=None):
            results.append((arg1, kwarg1))

        fn = dispatcher.dispatch("target1")
        fn("value1", kwarg1="value2")
        eq_(results, [("value1", "value2")])

    def test_multiple_handlers_same_priority(self):
        """Test multiple handlers at same priority execute in order."""
        dispatcher = PriorityDispatcher()
        results = []

        @dispatcher.dispatch_for("target1", priority=DispatchPriority.MEDIUM)
        def handler1():
            results.append("handler1")

        @dispatcher.dispatch_for("target1", priority=DispatchPriority.MEDIUM)
        def handler2():
            results.append("handler2")

        fn = dispatcher.dispatch("target1")
        fn()
        # Both should execute
        eq_(results, ["handler1", "handler2"])

    def test_branch(self):
        """Test that branch creates independent copy."""
        dispatcher = PriorityDispatcher()
        results1 = []

        @dispatcher.dispatch_for("target1")
        def handler1():
            results1.append("handler1")

        dispatcher2 = dispatcher.branch()
        results2 = []

        @dispatcher2.dispatch_for("target2")
        def handler2():
            results2.append("handler2")

        # Original should have target1
        fn1 = dispatcher.dispatch("target1")
        fn1()
        eq_(results1, ["handler1"])

        # Branch should have both
        fn1_branch = dispatcher2.dispatch("target1")
        fn2_branch = dispatcher2.dispatch("target2")
        fn1_branch()
        fn2_branch()
        eq_(results1, ["handler1", "handler1"])
        eq_(results2, ["handler2"])

    def test_populate_with(self):
        """Test populate_with method."""
        dispatcher1 = PriorityDispatcher()
        results = []

        @dispatcher1.dispatch_for("target1")
        def handler1():
            results.append("handler1")

        dispatcher2 = PriorityDispatcher()

        @dispatcher2.dispatch_for("target2")
        def handler2():
            results.append("handler2")

        # Populate dispatcher2 with dispatcher1's handlers
        dispatcher2.populate_with(dispatcher1)

        # dispatcher2 should now have both handlers
        fn1 = dispatcher2.dispatch("target1")
        fn2 = dispatcher2.dispatch("target2")
        fn1()
        fn2()
        eq_(results, ["handler1", "handler2"])

    def test_none_subgroup(self):
        """Test that None subgroup is tracked separately."""
        dispatcher = PriorityDispatcher()
        results = []

        @dispatcher.dispatch_for("target1", subgroup=None)
        def handler1():
            results.append("none")
            return PriorityDispatchResult.STOP

        @dispatcher.dispatch_for("target1", subgroup=None)
        def handler2():
            results.append("none2")  # Should not execute
            return PriorityDispatchResult.CONTINUE

        @dispatcher.dispatch_for("target1", subgroup="other")
        def handler3():
            results.append("other")  # Should execute
            return PriorityDispatchResult.CONTINUE

        fn = dispatcher.dispatch("target1")
        fn()
        eq_(results, ["none", "other"])
