from alembic.testing.requirements import SuiteRequirements
from alembic.testing import exclusions
from alembic import util


class DefaultRequirements(SuiteRequirements):

    @property
    def schemas(self):
        """Target database must support external schemas, and have one
        named 'test_schema'."""

        return exclusions.skip_if([
            "sqlite",
            "firebird"
        ], "no schema support")

    @property
    def no_referential_integrity(self):
        """test will fail if referential integrity is enforced"""

        return exclusions.fails_on_everything_except("sqlite")

    @property
    def non_native_boolean(self):
        """test will fail if native boolean is provided"""

        return exclusions.fails_if(
            exclusions.LambdaPredicate(
                lambda config: config.db.dialect.supports_native_boolean
            )
        )

    @property
    def no_fk_names(self):
        """foreign key constraints *never* have names in the DB"""

        return exclusions.only_if(
            lambda config: exclusions.against(config, "sqlite")
            and not util.sqla_100
        )

    @property
    def check_constraints_w_enforcement(self):
        return exclusions.fails_on("mysql")

    @property
    def unnamed_constraints(self):
        """constraints without names are supported."""
        return exclusions.only_on(['sqlite'])

    @property
    def fk_names(self):
        """foreign key constraints always have names in the DB"""
        return exclusions.fails_on('sqlite')

    @property
    def reflects_fk_options(self):
        return exclusions.only_on(['postgresql', 'mysql'])

    @property
    def fk_initially(self):
        """backend supports INITIALLY option in foreign keys"""
        return exclusions.only_on(['postgresql'])

    @property
    def fk_deferrable(self):
        """backend supports DEFERRABLE option in foreign keys"""
        return exclusions.only_on(['postgresql'])

    @property
    def reflects_unique_constraints_unambiguously(self):
        return exclusions.fails_on("mysql")

    @property
    def reflects_pk_names(self):
        """Target driver reflects the name of primary key constraints."""

        return exclusions.fails_on_everything_except(
            'postgresql', 'oracle', 'mssql', 'sybase')
