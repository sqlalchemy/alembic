from alembic.testing.requirements import SuiteRequirements
from sqlalchemy.testing import exclusions


class DefaultRequirements(SuiteRequirements):
    @property
    def schemas(self):
        """Target database must support external schemas, and have one
        named 'test_schema'."""

        return exclusions.skip_if([
            "sqlite",
            "firebird"
        ], "no schema support")
