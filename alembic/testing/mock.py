from __future__ import absolute_import

from sqlalchemy.testing import mock
from sqlalchemy.testing.mock import Mock, call

from alembic import util, compat

if util.sqla_09:
    from sqlalchemy.testing.mock import patch
elif compat.py33:
    from unittest.mock import patch
else:
    from mock import patch


