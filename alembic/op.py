from alembic.operations import Operations
from alembic import util

# create proxy functions for
# each method on the Operations class.
util.create_module_class_proxy(Operations, globals(), locals())
