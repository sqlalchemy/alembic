from alembic.environment import EnvironmentContext
from alembic import util

# create proxy functions for 
# each method on the EnvironmentContext class.
util.create_module_class_proxy(EnvironmentContext, globals(), locals())
