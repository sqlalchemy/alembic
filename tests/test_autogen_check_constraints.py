from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import Table

from alembic import autogenerate
from alembic.autogenerate import api
from alembic.ddl._autogen import ComparisonResult
from alembic.ddl.impl import DefaultImpl
from alembic.migration import MigrationContext
from alembic.operations import ops
from alembic.testing import config
from alembic.testing import eq_
from alembic.testing import eq_ignore_whitespace
from alembic.testing import fixture
from alembic.testing import TestBase
from alembic.testing import util
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.suite._autogen_fixtures import AutogenFixtureTest

_ck_plugin_disabled_opts = {
    "autogenerate_plugins": [
        "alembic.autogenerate.*",
        "~alembic.autogenerate.checkconstraint_byname",
    ]
}


@fixture(params=["table", "column"])
def col_and_check(request):
    if (
        request.param == "column"
        and not config.requirements.inline_check_constraint_reflection.enabled
    ):
        config.skip_test("does not support column bound check constraints")

    def make(name, type_, check):
        if request.param == "table":
            return [Column(name, type_), check]
        else:
            return [Column(name, type_, check)]

    return make


class AutogenCheckConstraintTest(AutogenFixtureTest, TestBase):
    __backend__ = True
    __requires__ = ("check_constraint_reflection",)

    def test_add_check_constraint(self, col_and_check):
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
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        diffs = self._fixture(m1, m2)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "ck_t_x_positive")

    def test_can_be_disabled_via_exclusion(self, col_and_check):
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
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        diffs = self._fixture(m1, m2, opts=_ck_plugin_disabled_opts)

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])

    def test_remove_check_constraint(self, col_and_check):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
        )

        diffs = self._fixture(m1, m2)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "remove_constraint")
        eq_(diffs[0][1].name, "ck_t_x_positive")

    def test_same_name_different_expression_no_change(self, col_and_check):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        Table(
            "t",
            m2,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 5", name="ck_t_x_positive")
            ),
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_compare_check_constraint_is_different(
        self, col_and_check, monkeypatch
    ):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        Table(
            "t",
            m2,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 5", name="ck_t_x_positive")
            ),
        )

        monkeypatch.setattr(
            DefaultImpl,
            "compare_check_constraint",
            lambda self, metadata_constraint, reflected_constraint: (
                ComparisonResult.Different("expression changed")
            ),
        )

        diffs = self._fixture(m1, m2)

        eq_(len(diffs), 2)
        eq_(
            {diffs[0][0], diffs[1][0]},
            {"add_constraint", "remove_constraint"},
        )

    def test_compare_check_constraint_is_skip(
        self, col_and_check, monkeypatch
    ):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        Table(
            "t",
            m2,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 5", name="ck_t_x_positive")
            ),
        )

        monkeypatch.setattr(
            DefaultImpl,
            "compare_check_constraint",
            lambda self, metadata_constraint, reflected_constraint: (
                ComparisonResult.Skip("cannot compare")
            ),
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_no_change_check_constraint(self, col_and_check):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        Table(
            "t",
            m2,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])

    def test_unnamed_check_constraint_in_metadata_ignored(self, col_and_check):
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
            *col_and_check("x", Integer, CheckConstraint("x > 0")),
        )

        diffs = self._fixture(m1, m2)

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

        diffs = self._fixture(m1, m2)

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])

    def test_multiple_check_constraints(self, col_and_check):
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
            CheckConstraint("x > 0", name="ck_x"),
            *col_and_check(
                "y", Integer, CheckConstraint("y > 0", name="ck_y")
            ),
        )

        diffs = self._fixture(m1, m2)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "ck_y")

    def test_remove_one_of_multiple(self, col_and_check):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            CheckConstraint("x > 0", name="ck_x"),
            *col_and_check(
                "y", Integer, CheckConstraint("y > 0", name="ck_y")
            ),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            Column("y", Integer),
            CheckConstraint("x > 0", name="ck_x"),
        )

        diffs = self._fixture(m1, m2)

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

        diffs = self._fixture(m1, m2)

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

        diffs = self._fixture(m1, m2)

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


class AutogenCheckConstraintSchemaTest(AutogenFixtureTest, TestBase):
    __only_on__ = "postgresql"
    __backend__ = True
    __requires__ = ("check_constraint_reflection",)

    def test_add_check_constraint_schema(self, col_and_check):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            Column("x", Integer),
            schema=config.test_schema,
        )

        Table(
            "t",
            m2,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
            schema=config.test_schema,
        )

        diffs = self._fixture(m1, m2, include_schemas=True)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "ck_t_x_positive")
        eq_(diffs[0][1].table.schema, config.test_schema)

    def test_remove_check_constraint_schema(self, col_and_check):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
            schema=config.test_schema,
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
            schema=config.test_schema,
        )

        diffs = self._fixture(m1, m2, include_schemas=True)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "remove_constraint")
        eq_(diffs[0][1].name, "ck_t_x_positive")
        eq_(diffs[0][1].table.schema, config.test_schema)


class AutogenCheckConstraintFilterTest(AutogenFixtureTest, TestBase):
    __backend__ = True
    __requires__ = ("check_constraint_reflection",)

    def test_include_name_excludes_reflected_check_constraint(
        self, col_and_check
    ):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
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
        )

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])

    def test_include_object_excludes_add(self, col_and_check):
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
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        def include_object(obj, name, type_, reflected, compare_to):
            if type_ == "check_constraint":
                return False
            return True

        diffs = self._fixture(
            m1,
            m2,
            object_filters=include_object,
        )

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])

    def test_include_object_excludes_remove(self, col_and_check):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
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
        )

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])

    def test_include_object_receives_correct_args_for_add(self, col_and_check):
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
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
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
        )

        eq_(len(calls), 1)
        eq_(calls[0][0], "ck_t_x_positive")
        eq_(calls[0][1], "check_constraint")
        eq_(calls[0][2], False)
        eq_(calls[0][3], None)

    def test_include_object_receives_correct_args_for_remove(
        self, col_and_check
    ):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
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
        eng.dialect.get_multi_check_constraints = unimpl

    def test_no_reflection_graceful_skip_add(self, col_and_check):
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
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        diffs = self._fixture(m1, m2)

        check_diffs = [
            d
            for d in diffs
            if d[0] in ("add_constraint", "remove_constraint")
            and isinstance(d[1], CheckConstraint)
        ]
        eq_(check_diffs, [])

    def test_no_reflection_graceful_skip_remove(self, col_and_check):
        m1 = MetaData()
        m2 = MetaData()

        Table(
            "t",
            m1,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        Table(
            "t",
            m2,
            Column("x", Integer),
        )

        diffs = self._fixture(m1, m2)

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

        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_check_constraint('ck_x_positive', 't', 'x > 0')",
        )

    def test_render_add_check_constraint_string_sqltext(self):
        m = MetaData()
        t = Table("t", m, Column("x", Integer))
        ck = CheckConstraint("x > 0", name="ck_x_positive")
        t.append_constraint(ck)
        op_obj = ops.CreateCheckConstraintOp.from_constraint(ck)

        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_check_constraint('ck_x_positive', 't', 'x > 0')",
        )

    def test_render_drop_check_constraint(self):
        m = MetaData()
        t = Table("t", m, Column("x", Integer))
        ck = CheckConstraint(t.c.x > 0, name="ck_x_positive")
        op_obj = ops.DropConstraintOp.from_constraint(ck)

        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.drop_constraint('ck_x_positive', 't', type_='check')",
        )

    def test_render_add_check_constraint_with_schema(self):
        m = MetaData()
        t = Table("t", m, Column("x", Integer), schema="test_schema")
        ck = CheckConstraint(t.c.x > 0, name="ck_x_positive")
        op_obj = ops.CreateCheckConstraintOp.from_constraint(ck)

        eq_ignore_whitespace(
            autogenerate.render_op_text(self.autogen_context, op_obj),
            "op.create_check_constraint('ck_x_positive', 't', 'x > 0', "
            "schema='test_schema')",
        )


class AutogenCheckConstraintNamingConvTest(AutogenFixtureTest, TestBase):
    __backend__ = True
    __requires__ = ("check_constraint_reflection",)

    def test_add_named_via_convention(self, col_and_check):
        m1 = MetaData()
        m2 = MetaData(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )

        Table("t", m1, Column("x", Integer))

        Table(
            "t",
            m2,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="x_positive")
            ),
        )

        diffs = self._fixture(m1, m2)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "add_constraint")
        eq_(diffs[0][1].name, "ck_t_x_positive")

    def test_remove_named_via_convention(self, col_and_check):
        m1 = MetaData()
        m2 = MetaData(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )

        Table(
            "t",
            m1,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        Table("t", m2, Column("x", Integer))

        diffs = self._fixture(m1, m2)

        eq_(len(diffs), 1)
        eq_(diffs[0][0], "remove_constraint")
        eq_(diffs[0][1].name, "ck_t_x_positive")

    def test_no_change_named_via_convention(self, col_and_check):
        m1 = MetaData()
        m2 = MetaData(
            naming_convention={"ck": "ck_%(table_name)s_%(constraint_name)s"}
        )

        Table(
            "t",
            m1,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="ck_t_x_positive")
            ),
        )

        Table(
            "t",
            m2,
            *col_and_check(
                "x", Integer, CheckConstraint("x > 0", name="x_positive")
            ),
        )

        diffs = self._fixture(m1, m2)

        eq_(diffs, [])
