from os import path

__version__ = '0.2.0'

package_dir = path.abspath(path.dirname(__file__))


class _OpProxy(object):
    _proxy = None
    def __getattr__(self, key):
        return getattr(self._proxy, key)
op = _OpProxy()
