from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table

from alembic import autogenerate
from alembic.autogenerate import api
from alembic.migration import MigrationContext
from alembic.operations import ops
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import TestBase
from alembic.testing import util
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.suite._autogen_fixtures import AutogenFixtureTest


_ck_plugin_opts = {
    "autogenerate_plugins": [
        "alembic.autogenerate.*",
        "alembic.ext.checkconstraint",
    ]
}


class AutogenCheckConstraintTest(AutogenFixtureTest, TestBase):
    __backend__ = True
    __requires__ = ("check_constraint_reflection",)

    def test_add_check_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "ck_t_x_positive")

    def test_remove_check_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "remove_constraint")
        eq_(diffs[0][1].name, "ck_t_x_positive")

    def test_same_name_different_expression_no_change(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            CheckConstraint("x > 5", name="ck_t_x_positive"),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        eq_(diffs, [])

    def test_no_change_check_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        eq_(diffs, [])

    def test_unnamed_check_constraint_in_metadata_ignored(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            CheckConstraint("x > 0"),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        eq_(diffs, [])

    def test_type_bound_boolean_not_detected(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            Column("flag", Boolean(create_constraint=True)),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])

    def test_multiple_check_constraints(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            Column("y", Integer),
            CheckConstraint("x > 0", name="ck_x"),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            Column("y", Integer),
            CheckConstraint("x > 0", name="ck_x"),
            CheckConstraint("y > 0", name="ck_y"),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "ck_y")

    def test_remove_one_of_multiple(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            Column("y", Integer),
            CheckConstraint("x > 0", name="ck_x"),
            CheckConstraint("y > 0", name="ck_y"),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            Column("y", Integer),
            CheckConstraint("x > 0", name="ck_x"),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "remove_constraint")
        eq_(diffs[0][1].name, "ck_y")

    def test_add_table_with_check_constraint_no_duplicate(self):
        m1 = MetaData()
        m2 = MetaData()

        Table("t", m1, Column("x", Integer))

        Table("t", m2, Column("x", Integer))
        Table(
            "new_table",
            m2,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_new_x"),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        add_table = [d for d in diffs if d[0] == "add_table"]
        eq_(len(add_table), 1)
        eq_(add_table[0][1].name, "new_table")

        new_table = add_table[0][1]
        ck_in_table = [
            c
            for c in new_table.constraints
            if isinstance(c, CheckConstraint) and c.name == "ck_new_x"
        ]
        eq_(len(ck_in_table), 1)

        add_ck = [
            d
            for d in diffs
            if d[0] == "add_constraint" and isinstance(d[1], CheckConstraint)
        ]
        eq_(add_ck, [])

    def test_drop_table_with_check_constraint_no_duplicate(self):
        m1 = MetaData()
        m2 = MetaData()

        Table("t", m1, Column("x", Integer))
        Table(
            "old_table",
            m1,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_old_x"),
        )

        Table("t", m2, Column("x", Integer))

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        drop_table = [d for d in diffs if d[0] == "remove_table"]
        eq_(len(drop_table), 1)
        eq_(drop_table[0][1].name, "old_table")

        old_table = drop_table[0][1]
        ck_in_table = [
            c
            for c in old_table.constraints
            if isinstance(c, CheckConstraint) and c.name == "ck_old_x"
        ]
        eq_(len(ck_in_table), 1)

        drop_ck = [
            d
            for d in diffs
            if d[0] == "remove_constraint"
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(drop_ck, [])


class AutogenCheckConstraintFilterTest(AutogenFixtureTest, TestBase):
    __backend__ = True
    __requires__ = ("check_constraint_reflection",)

    def test_include_name_excludes_reflected_check_constraint(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
        )

        def include_name(name, type_, parent_names):
            if type_ == "check_constraint":
                return False
            return True

        diffs = self._fixture(
            m1,
            m2,
            name_filters=include_name,
            opts=_ck_plugin_opts,
        )

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])

    def test_include_object_excludes_add(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "check_constraint":
                return False
            return True

        diffs = self._fixture(
            m1,
            m2,
            object_filters=include_object,
            opts=_ck_plugin_opts,
        )

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])

    def test_include_object_excludes_remove(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
        )

        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "check_constraint":
                return False
            return True

        diffs = self._fixture(
            m1,
            m2,
            object_filters=include_object,
            opts=_ck_plugin_opts,
        )

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])

    def test_include_object_receives_correct_args_for_add(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        calls = []

        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "check_constraint":
                calls.append((name, type_, reflected, compare_to))
            return True

        self._fixture(
            m1,
            m2,
            object_filters=include_object,
            opts=_ck_plugin_opts,
        )

        eq_(len(calls), 1)
        eq_(calls[0][0], "ck_t_x_positive")
        eq_(calls[0][1], "check_constraint")
        eq_(calls[0][2], False)
        eq_(calls[0][3], None)

    def test_include_object_receives_correct_args_for_remove(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
        )

        calls = []

        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "check_constraint":
                calls.append((name, type_, reflected, compare_to))
            return True

        self._fixture(
            m1,
            m2,
            object_filters=include_object,
            opts=_ck_plugin_opts,
        )

        eq_(len(calls), 1)
        eq_(calls[0][0], "ck_t_x_positive")
        eq_(calls[0][1], "check_constraint")
        eq_(calls[0][2], True)
        eq_(calls[0][3], None)


class AutogenCheckConstraintNoReflectionTest(AutogenFixtureTest, TestBase):
    __backend__ = True

    def setUp(self):
        staging_env()
        self.bind = eng = util.testing_engine()

        def unimpl(*arg, **kw):
            raise NotImplementedError()

        eng.dialect.get_check_constraints = unimpl

    def test_no_reflection_graceful_skip_add(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])

    def test_no_reflection_graceful_skip_remove(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])


class AutogenCheckConstraintRenderTest(TestBase):

    def setUp(self):
        staging_env()
        self.bind = config.db

        ctx_opts = {
            "sqlalchemy_module_prefix": "sa.",
            "alembic_module_prefix": "op.",
            "target_metadata": MetaData(),
        }
        context = MigrationContext.configure(
            dialect_name=self.bind.dialect.name, opts=ctx_opts
        )
        self.autogen_context = api.AutogenContext(context)

    def tearDown(self):
        clear_staging_env()

    def test_render_add_check_constraint(self):
        m = MetaData()
        t = Table("t", m, Column("x", Integer))
        ck = CheckConstraint(t.c.x > 0, name="ck_x_positive")
        op_obj = ops.CreateCheckConstraintOp.from_constraint(ck)

        result = autogenerate.render_op_text(self.autogen_context, op_obj)

        assert "op.create_check_constraint(" in result
        assert "'ck_x_positive'" in result
        assert "'t'" in result

    def test_render_add_check_constraint_string_sqltext(self):
        m = MetaData()
        t = Table("t", m, Column("x", Integer))
        ck = CheckConstraint("x > 0", name="ck_x_positive")
        t.append_constraint(ck)
        op_obj = ops.CreateCheckConstraintOp.from_constraint(ck)

        result = autogenerate.render_op_text(self.autogen_context, op_obj)

        assert "op.create_check_constraint(" in result
        assert "'ck_x_positive'" in result

    def test_render_drop_check_constraint(self):
        m = MetaData()
        t = Table("t", m, Column("x", Integer))
        ck = CheckConstraint(t.c.x > 0, name="ck_x_positive")
        op_obj = ops.DropConstraintOp.from_constraint(ck)

        result = autogenerate.render_op_text(self.autogen_context, op_obj)

        assert "op.drop_constraint(" in result
        assert "'ck_x_positive'" in result

    def test_render_add_check_constraint_with_schema(self):
        m = MetaData()
        t = Table("t", m, Column("x", Integer), schema="test_schema")
        ck = CheckConstraint(t.c.x > 0, name="ck_x_positive")
        op_obj = ops.CreateCheckConstraintOp.from_constraint(ck)

        result = autogenerate.render_op_text(self.autogen_context, op_obj)

        assert "op.create_check_constraint(" in result
        assert "'ck_x_positive'" in result
        assert "schema='test_schema'" in result


class AutogenCheckConstraintPluginOptInTest(AutogenFixtureTest, TestBase):
    __backend__ = True
    __requires__ = ("check_constraint_reflection",)

    def test_default_plugins_do_not_detect(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        diffs = self._fixture(m1, m2)

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])

    def test_opted_in_plugin_does_detect(self):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "ck_t_x_positive")


class AutogenCheckConstraintNamingConvTest(AutogenFixtureTest, TestBase):
    __backend__ = True
    __requires__ = ("check_constraint_reflection",)

    def test_add_named_via_convention(self):
        m1 = MetaData()
        m2 = MetaData(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )

        Table("t", m1, Column("x", Integer))

        Table(
            "t",
            m2,
            Column("x", Integer),
            CheckConstraint("x > 0", name="x_positive"),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "ck_t_x_positive")

    def test_remove_named_via_convention(self):
        m1 = MetaData()
        m2 = MetaData(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )

        Table(
            "t",
            m1,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        Table("t", m2, Column("x", Integer))

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "remove_constraint")
        eq_(diffs[0][1].name, "ck_t_x_positive")

    def test_no_change_named_via_convention(self):
        m1 = MetaData()
        m2 = MetaData(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )

        Table(
            "t",
            m1,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_t_x_positive"),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            CheckConstraint("x > 0", name="x_positive"),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_opts)

        eq_(diffs, [])
