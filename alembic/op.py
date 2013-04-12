from .operations import Operations
from . import util

# create proxy functions for
# each method on the Operations class.
util.create_module_class_proxy(Operations, globals(), locals())
