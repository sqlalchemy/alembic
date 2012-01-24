from alembic.operations import Operations

# create proxy functions for 
# each method on the Operations class.

# TODO: this is a quick and dirty version of this.
# Ideally, we'd be duplicating method signatures 
# and such, using eval(), etc.

_proxy = None
def _create_op_proxy(name):
    def go(*arg, **kw):
        return getattr(_proxy, name)(*arg, **kw)
    go.__name__ = name
    return go

for methname in dir(Operations):
    if not methname.startswith('_'):
        locals()[methname] = _create_op_proxy(methname)