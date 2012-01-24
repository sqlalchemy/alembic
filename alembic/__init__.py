from os import path

__version__ = '0.2.0'

package_dir = path.abspath(path.dirname(__file__))


from alembic import op

class _ContextProxy(object):
    """A proxy object for the current :class:`.EnvironmentContext`."""
    def __getattr__(self, key):
        return getattr(_context, key)
context = _ContextProxy()

