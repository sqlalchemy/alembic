import sys

from sqlalchemy.testing import exclusions
from sqlalchemy.testing.requirements import Requirements

from alembic import util
from alembic.util import sqla_compat


class SuiteRequirements(Requirements):
    @property
    def schemas(self):
        """Target database must support external schemas, and have one
        named 'test_schema'."""

        return exclusions.open()

    @property
    def unique_constraint_reflection(self):
        def doesnt_have_check_uq_constraints(config):
            from sqlalchemy import inspect

            # temporary
            if config.db.name == "oracle":
                return True

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
    def foreign_key_match(self):
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
    def sqlalchemy_issue_3740(self):
        """Fixes percent sign escaping for paramstyles that don't require it"""
        return exclusions.skip_if(
            lambda config: not util.sqla_120,
            "SQLAlchemy 1.2 or greater required",
        )

    @property
    def sqlalchemy_12(self):
        return exclusions.skip_if(
            lambda config: not util.sqla_1216,
            "SQLAlchemy 1.2.16 or greater required",
        )

    @property
    def sqlalchemy_1115(self):
        return exclusions.skip_if(
            lambda config: not util.sqla_1115,
            "SQLAlchemy 1.1.15 or greater required",
        )

    @property
    def sqlalchemy_110(self):
        return exclusions.skip_if(
            lambda config: not util.sqla_110,
            "SQLAlchemy 1.1.0 or greater required",
        )

    @property
    def sqlalchemy_issue_4436(self):
        def check(config):
            vers = sqla_compat._vers

            if vers == (1, 3, 0, "b1"):
                return True
            elif vers >= (1, 2, 16):
                return False
            else:
                return True

        return exclusions.skip_if(
            check, "SQLAlchemy 1.2.16, 1.3.0b2 or greater required"
        )

    @property
    def python3(self):
        return exclusions.skip_if(
            lambda: sys.version_info < (3,), "Python version 3.xx is required."
        )

    @property
    def pep3147(self):

        return exclusions.only_if(lambda config: util.compat.has_pep3147())

    @property
    def comments(self):
        return exclusions.only_if(
            lambda config: sqla_compat._dialect_supports_comments(
                config.db.dialect
            )
        )

    @property
    def comments_api(self):
        return exclusions.only_if(lambda config: util.sqla_120)

    @property
    def alter_column(self):
        return exclusions.open()
