from .fixtures import TestBase
from .assertions import eq_, ne_, is_, assert_raises_message, \
    eq_ignore_whitespace, assert_raises

from sqlalchemy.testing import config
from alembic import util
if not util.sqla_100:
    config.test_schema = "test_schema"


from sqlalchemy.testing.config import requirements as requires
