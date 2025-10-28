from sqlalchemy.testing.requirements import Requirements

from alembic import util
from ..testing import exclusions


class SuiteRequirements(Requirements):
    @property
    def schemas(self):
        """Target database must support external schemas, and have one
        named 'test_schema'."""

        return exclusions.open()

    @property
    def autocommit_isolation(self):
        """target database should support 'AUTOCOMMIT' isolation level"""

        return exclusions.closed()

    @property
    def materialized_views(self):
        """needed for sqlalchemy compat"""
        return exclusions.closed()

    @property
    def unique_constraint_reflection(self):
        def doesnt_have_check_uq_constraints(config):
            from sqlalchemy import inspect

            insp = inspect(config.db)
            try:
                insp.get_unique_constraints("x")
            except NotImplementedError:
                return True
            except TypeError:
                return True
            except Exception:
                pass
            return False

        return exclusions.skip_if(doesnt_have_check_uq_constraints)

    @property
    def sequences(self):
        """Target database must support SEQUENCEs."""

        return exclusions.only_if(
            [lambda config: config.db.dialect.supports_sequences],
            "no sequence support",
        )

    @property
    def foreign_key_match(self):
        return exclusions.open()

    @property
    def foreign_key_constraint_reflection(self):
        return exclusions.open()

    @property
    def check_constraints_w_enforcement(self):
        """Target database must support check constraints
        and also enforce them."""

        return exclusions.open()

    @property
    def reflects_pk_names(self):
        return exclusions.closed()

    @property
    def reflects_fk_options(self):
        return exclusions.closed()

    @property
    def sqlalchemy_1x(self):
        return exclusions.skip_if(
            lambda config: util.sqla_2,
            "SQLAlchemy 1.x test",
        )

    @property
    def sqlalchemy_2(self):
        return exclusions.skip_if(
            lambda config: not util.sqla_2,
            "SQLAlchemy 2.x test",
        )

    @property
    def asyncio(self):
        def go(config):
            try:
                import greenlet  # noqa: F401
            except ImportError:
                return False
            else:
                return True

        return exclusions.only_if(go)

    @property
    def comments(self):
        return exclusions.only_if(
            lambda config: config.db.dialect.supports_comments
        )

    @property
    def alter_column(self):
        return exclusions.open()

    @property
    def computed_columns(self):
        return exclusions.closed()

    @property
    def computed_columns_warn_no_persisted(self):
        def go(config):
            return hasattr(
                config.db.dialect, "supports_virtual_generated_columns"
            )

        return exclusions.only_if("postgresql<18") + exclusions.only_if(go)

    @property
    def autoincrement_on_composite_pk(self):
        return exclusions.closed()

    @property
    def fk_ondelete_is_reflected(self):
        return exclusions.closed()

    @property
    def fk_onupdate_is_reflected(self):
        return exclusions.closed()

    @property
    def fk_onupdate(self):
        return exclusions.open()

    @property
    def fk_ondelete_restrict(self):
        return exclusions.open()

    @property
    def fk_onupdate_restrict(self):
        return exclusions.open()

    @property
    def fk_ondelete_noaction(self):
        return exclusions.open()

    @property
    def fk_initially(self):
        return exclusions.closed()

    @property
    def fk_deferrable(self):
        return exclusions.closed()

    @property
    def fk_deferrable_is_reflected(self):
        return exclusions.closed()

    @property
    def fk_names(self):
        return exclusions.open()

    @property
    def integer_subtype_comparisons(self):
        return exclusions.open()

    @property
    def no_name_normalize(self):
        return exclusions.skip_if(
            lambda config: config.db.dialect.requires_name_normalize
        )

    @property
    def identity_columns(self):
        return exclusions.closed()

    @property
    def identity_columns_alter(self):
        return exclusions.closed()
