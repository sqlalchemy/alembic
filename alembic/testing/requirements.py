from sqlalchemy.testing.requirements import Requirements
from sqlalchemy.testing import exclusions
from alembic import util


class SuiteRequirements(Requirements):
    @property
    def schemas(self):
        """Target database must support external schemas, and have one
        named 'test_schema'."""

        return exclusions.open()

    @property
    def sqlalchemy_08(self):

        return exclusions.skip_if(
            lambda config: not util.sqla_08,
            "SQLAlchemy 0.8.0b2 or greater required"
        )

    @property
    def sqlalchemy_09(self):
        return exclusions.skip_if(
            lambda config: not util.sqla_09,
            "SQLAlchemy 0.9.0 or greater required"
        )

    @property
    def sqlalchemy_092(self):
        return exclusions.skip_if(
            lambda config: not util.sqla_092,
            "SQLAlchemy 0.9.2 or greater required"
        )

    @property
    def sqlalchemy_094(self):
        return exclusions.skip_if(
            lambda config: not util.sqla_094,
            "SQLAlchemy 0.9.4 or greater required"
        )
