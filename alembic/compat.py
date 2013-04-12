import sys


py3k = sys.version_info >= (3, 0)
py3kwarning = getattr(sys, 'py3kwarning', False) or py3k
py26 = sys.version_info >= (2, 6)
jython = sys.platform.startswith('java')
win32 = sys.platform.startswith('win')
pypy = hasattr(sys, 'pypy_version_info')

if py3k:
    import builtins as compat_builtins
    string_types = str,
    binary_type = bytes
    text_type = str
else:
    import __builtin__ as compat_builtins
    string_types = basestring,
    binary_type = str
    text_type = unicode

if py3kwarning:
    def callable(fn):
        return hasattr(fn, '__call__')
else:
    callable = callable


################################################
# cross-compatible metaclass implementation
# Copyright (c) 2010-2012 Benjamin Peterson
def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("%sBase" % meta.__name__, (base,), {})
################################################
