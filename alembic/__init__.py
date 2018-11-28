from os import path

__version__ = '1.0.5'

package_dir = path.abspath(path.dirname(__file__))


from . import op  # noqa
from . import context  # noqa

import sys
from .runtime import environment
from .runtime import migration
sys.modules['alembic.migration'] = migration
sys.modules['alembic.environment'] = environment
