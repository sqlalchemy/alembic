from mako.template import Template
import sys
import os
import textwrap
from sqlalchemy.engine import url
import imp
import warnings
import re
import time
import random
import uuid


class CommandError(Exception):
    pass

try:
    width = int(os.environ['COLUMNS'])
except (KeyError, ValueError):
    width = 80

def template_to_file(template_file, dest, **kw):
    f = open(dest, 'w')
    f.write(
        Template(filename=template_file).render(**kw)
    )
    f.close()


def status(_statmsg, fn, *arg, **kw):
    msg(_statmsg + "...", False)
    try:
        ret = fn(*arg, **kw)
        sys.stdout.write("done\n")
        return ret
    except:
        sys.stdout.write("FAILED\n")
        raise

def err(message):
    msg(message)
    sys.exit(-1)

def obfuscate_url_pw(u):
    u = url.make_url(u)
    if u.password:
        u.password = 'XXXXX'
    return str(u)

def warn(msg):
    warnings.warn(msg)

def msg(msg, newline=True):
    lines = textwrap.wrap(msg, width)
    if len(lines) > 1:
        for line in lines[0:-1]:
            sys.stdout.write("  " +line + "\n")
    sys.stdout.write("  " + lines[-1] + ("\n" if newline else ""))

def load_python_file(dir_, filename):
    """Load a file from the given path as a Python module."""

    module_id = re.sub(r'\W', "_", filename)
    path = os.path.join(dir_, filename)
    module = imp.load_source(module_id, path, open(path, 'rb'))
    del sys.modules[module_id]
    return module

def pyc_file_from_path(path):
    """Given a python source path, locate the .pyc.
    
    See http://www.python.org/dev/peps/pep-3147/
                        #detecting-pep-3147-availability
        http://www.python.org/dev/peps/pep-3147/#file-extension-checks
    
    """
    import imp
    has3147 = hasattr(imp, 'get_tag')
    if has3147:
        return imp.cache_from_source(path)
    else:
        return path + "c"

def rev_id():
    val = int(uuid.uuid4()) % 100000000000000
    return hex(val)[2:-1]

class memoized_property(object):
    """A read-only @property that is only evaluated once."""

    def __init__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        obj.__dict__[self.__name__] = result = self.fget(obj)
        return result

class importlater(object):
    """Deferred import object.

    e.g.::

        somesubmod = importlater("mypackage.somemodule", "somesubmod")

    is equivalent to::

        from mypackage.somemodule import somesubmod

    except evaluted upon attribute access to "somesubmod".
    
    importlater() currently requires that resolve_all() be
    called, typically at the bottom of a package's __init__.py.
    This is so that __import__ still called only at 
    module import time, and not potentially within
    a non-main thread later on.

    """

    _unresolved = set()

    def __init__(self, path, addtl=None):
        self._il_path = path
        self._il_addtl = addtl
        importlater._unresolved.add(self)

    @classmethod
    def resolve_all(cls):
        for m in list(importlater._unresolved):
            m._resolve()

    @property
    def _full_path(self):
        if self._il_addtl:
            return self._il_path + "." + self._il_addtl
        else:
            return self._il_path

    @memoized_property
    def module(self):
        if self in importlater._unresolved:
            raise ImportError(
                    "importlater.resolve_all() hasn't been called")

        m = self._initial_import
        if self._il_addtl:
            m = getattr(m, self._il_addtl)
        else:
            for token in self._il_path.split(".")[1:]:
                m = getattr(m, token)
        return m

    def _resolve(self):
        importlater._unresolved.discard(self)
        if self._il_addtl:
            self._initial_import = __import__(
                                self._il_path, globals(), locals(), 
                                [self._il_addtl])
        else:
            self._initial_import = __import__(self._il_path)

    def __getattr__(self, key):
        if key == 'module':
            raise ImportError("Could not resolve module %s" 
                                % self._full_path)
        try:
            attr = getattr(self.module, key)
        except AttributeError:
            raise AttributeError(
                        "Module %s has no attribute '%s'" %
                        (self._full_path, key)
                    )
        self.__dict__[key] = attr
        return attr
