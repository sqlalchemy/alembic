from __future__ import with_statement

from mako.template import Template
import sys
import os
import textwrap
from sqlalchemy.engine import url
import imp
import warnings
import re
import inspect
import uuid

class CommandError(Exception):
    pass

from sqlalchemy import __version__
def _safe_int(value):
    try:
        return int(value)
    except:
        return value
_vers = tuple([_safe_int(x) for x in re.findall(r'(\d+|[abc]\d)', __version__)])
sqla_07 = _vers > (0, 7, 2)
sqla_08 = _vers >= (0, 8, 0, 'b2')
if not sqla_07:
    raise CommandError(
            "SQLAlchemy 0.7.3 or greater is required. ")

from sqlalchemy.util import format_argspec_plus, update_wrapper
from sqlalchemy.util.compat import inspect_getfullargspec

try:
    width = int(os.environ['COLUMNS'])
except (KeyError, ValueError):
    width = 80

def template_to_file(template_file, dest, **kw):
    with open(dest, 'w') as f:
        f.write(
            Template(filename=template_file).render(**kw)
        )

def create_module_class_proxy(cls, globals_, locals_):
    """Create module level proxy functions for the
    methods on a given class.

    The functions will have a compatible signature
    as the methods.   A proxy is established
    using the ``_install_proxy(obj)`` function,
    and removed using ``_remove_proxy()``, both
    installed by calling this function.

    """
    attr_names = set()

    def _install_proxy(obj):
        globals_['_proxy'] = obj
        for name in attr_names:
            globals_[name] = getattr(obj, name)

    def _remove_proxy():
        globals_['_proxy'] = None
        for name in attr_names:
            del globals_[name]

    globals_['_install_proxy'] = _install_proxy
    globals_['_remove_proxy'] = _remove_proxy

    def _create_op_proxy(name):
        fn = getattr(cls, name)
        spec = inspect.getargspec(fn)
        if spec[0] and spec[0][0] == 'self':
            spec[0].pop(0)
        args = inspect.formatargspec(*spec)
        num_defaults = 0
        if spec[3]:
            num_defaults += len(spec[3])
        name_args = spec[0]
        if num_defaults:
            defaulted_vals = name_args[0 - num_defaults:]
        else:
            defaulted_vals = ()

        apply_kw = inspect.formatargspec(
                                name_args, spec[1], spec[2],
                                defaulted_vals,
                                formatvalue=lambda x: '=' + x)

        def _name_error(name):
            raise NameError(
                    "Can't invoke function '%s', as the proxy object has "\
                    "not yet been "
                    "established for the Alembic '%s' class.  "
                    "Try placing this code inside a callable." % (
                        name, cls.__name__
                    ))
        globals_['_name_error'] = _name_error

        func_text = textwrap.dedent("""\
        def %(name)s(%(args)s):
            %(doc)r
            try:
                p = _proxy
            except NameError:
                _name_error('%(name)s')
            return _proxy.%(name)s(%(apply_kw)s)
            e
        """ % {
            'name': name,
            'args': args[1:-1],
            'apply_kw': apply_kw[1:-1],
            'doc': fn.__doc__,
        })
        lcl = {}
        exec func_text in globals_, lcl
        return lcl[name]

    for methname in dir(cls):
        if not methname.startswith('_'):
            if callable(getattr(cls, methname)):
                locals_[methname] = _create_op_proxy(methname)
            else:
                attr_names.add(methname)

def coerce_resource_to_filename(fname):
    """Interpret a filename as either a filesystem location or as a package resource.

    Names that are non absolute paths and contain a colon
    are interpreted as resources and coerced to a file location.

    """
    if not os.path.isabs(fname) and ":" in fname:
        import pkg_resources
        fname = pkg_resources.resource_filename(*fname.split(':'))
    return fname

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

def asbool(value):
    return value is not None and \
        value.lower() == 'true'

def warn(msg):
    warnings.warn(msg)

def msg(msg, newline=True):
    lines = textwrap.wrap(msg, width)
    if len(lines) > 1:
        for line in lines[0:-1]:
            sys.stdout.write("  " + line + "\n")
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


class immutabledict(dict):

    def _immutable(self, *arg, **kw):
        raise TypeError("%s object is immutable" % self.__class__.__name__)

    __delitem__ = __setitem__ = __setattr__ = \
    clear = pop = popitem = setdefault = \
        update = _immutable

    def __new__(cls, *args):
        new = dict.__new__(cls)
        dict.__init__(new, *args)
        return new

    def __init__(self, *args):
        pass

    def __reduce__(self):
        return immutabledict, (dict(self), )

    def union(self, d):
        if not self:
            return immutabledict(d)
        else:
            d2 = immutabledict(self)
            dict.update(d2, d)
            return d2

    def __repr__(self):
        return "immutabledict(%s)" % dict.__repr__(self)





def _with_legacy_names(translations):
    def decorate(fn):

        spec = inspect_getfullargspec(fn)
        metadata = dict(target='target', fn='fn')
        metadata.update(format_argspec_plus(spec, grouped=False))

        has_keywords = bool(spec[2])

        if not has_keywords:
            metadata['args'] += ", **kw"
            metadata['apply_kw'] += ", **kw"

        def go(*arg, **kw):
            names = set(kw).difference(spec[0])
            for oldname, newname in translations:
                if oldname in kw:
                    kw[newname] = kw.pop(oldname)
                    names.discard(oldname)

                    warnings.warn(
                        "Argument '%s' is now named '%s' for function '%s'" %
                        (oldname, newname, fn.__name__))
            if not has_keywords and names:
                raise TypeError("Unknown arguments: %s" % ", ".join(names))
            return fn(*arg, **kw)

        code = 'lambda %(args)s: %(target)s(%(apply_kw)s)' % (
                metadata)
        decorated = eval(code, {"target": go})
        decorated.func_defaults = getattr(fn, 'im_func', fn).func_defaults
        return update_wrapper(decorated, fn)

    return decorate



