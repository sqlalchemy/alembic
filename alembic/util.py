from mako.template import Template
import sys
import os
import textwrap
from sqlalchemy import util
import imp
import warnings
import re

NO_VALUE = util.symbol("NO_VALUE")

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


def format_opt(opt, hlp, padding=22):
    return "  " + opt + \
        ((padding - len(opt)) * " ") + hlp

def status(_statmsg, fn, *arg, **kw):
    msg(_statmsg + "...", False)
    try:
        ret = fn(*arg, **kw)
        sys.stdout.write("done\n")
        return ret
    except:
        sys.stdout.write("FAILED\n")
        raise

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
