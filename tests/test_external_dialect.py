from sqlalchemy import MetaData
from sqlalchemy import types as sqla_types
from sqlalchemy.engine import default

from alembic import autogenerate
from alembic.autogenerate import api
from alembic.autogenerate import render
from alembic.ddl import impl
from alembic.migration import MigrationContext
from alembic.testing import eq_
from alembic.testing import eq_ignore_whitespace
from alembic.testing.fixtures import TestBase


class CustomDialect(default.DefaultDialect):
    name = "custom_dialect"


try:
    from sqlalchemy.dialects import registry
except ImportError:
    pass
else:
    registry.register("custom_dialect", __name__, "CustomDialect")


class CustomDialectImpl(impl.DefaultImpl):
    __dialect__ = "custom_dialect"
    transactional_ddl = False

    def render_type(self, type_, autogen_context):
        if type_.__module__ == __name__:
            autogen_context.imports.add(
                "from %s import custom_dialect_types" % (__name__,)
            )
            is_external = True
        else:
            is_external = False

        if is_external and hasattr(
            self, "_render_%s_type" % type_.__visit_name__
        ):
            meth = getattr(self, "_render_%s_type" % type_.__visit_name__)
            return meth(type_, autogen_context)

        if is_external:
            return "%s.%r" % ("custom_dialect_types", type_)
        else:
            return None

    def _render_EXT_ARRAY_type(self, type_, autogen_context):
        return render._render_type_w_subtype(
            type_,
            autogen_context,
            "item_type",
            r"(.+?\()",
            prefix="custom_dialect_types.",
        )


class EXT_ARRAY(sqla_types.TypeEngine):
    __visit_name__ = "EXT_ARRAY"

    def __init__(self, item_type):
        if isinstance(item_type, type):
            item_type = item_type()
        self.item_type = item_type
        super().__init__()


class FOOBARTYPE(sqla_types.TypeEngine):
    __visit_name__ = "FOOBARTYPE"


class ExternalDialectRenderTest(TestBase):
    def setUp(self):
        ctx_opts = {
            "sqlalchemy_module_prefix": "sa.",
            "alembic_module_prefix": "op.",
            "target_metadata": MetaData(),
            "user_module_prefix": None,
        }
        context = MigrationContext.configure(
            dialect_name="custom_dialect", opts=ctx_opts
        )

        self.autogen_context = api.AutogenContext(context)

    def test_render_type(self):
        eq_ignore_whitespace(
            autogenerate.render._repr_type(FOOBARTYPE(), self.autogen_context),
            "custom_dialect_types.FOOBARTYPE()",
        )

        eq_(
            self.autogen_context.imports,
            {
                "from tests.test_external_dialect "
                "import custom_dialect_types"
            },
        )

    def test_external_nested_render_sqla_type(self):

        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                EXT_ARRAY(sqla_types.Integer), self.autogen_context
            ),
            "custom_dialect_types.EXT_ARRAY(sa.Integer())",
        )

        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                EXT_ARRAY(sqla_types.DateTime(timezone=True)),
                self.autogen_context,
            ),
            "custom_dialect_types.EXT_ARRAY(sa.DateTime(timezone=True))",
        )

        eq_(
            self.autogen_context.imports,
            {
                "from tests.test_external_dialect "
                "import custom_dialect_types"
            },
        )

    def test_external_nested_render_external_type(self):

        eq_ignore_whitespace(
            autogenerate.render._repr_type(
                EXT_ARRAY(FOOBARTYPE), self.autogen_context
            ),
            "custom_dialect_types.EXT_ARRAY"
            "(custom_dialect_types.FOOBARTYPE())",
        )

        eq_(
            self.autogen_context.imports,
            {
                "from tests.test_external_dialect "
                "import custom_dialect_types"
            },
        )
