import textwrap
import warnings
import inspect
import uuid
import collections

from .compat import callable, exec_, string_types

from sqlalchemy.util import format_argspec_plus, update_wrapper
from sqlalchemy.util.compat import inspect_getfullargspec


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

    def _add_proxied_method(methname):
        if not methname.startswith('_'):
            if callable(getattr(cls, methname)):
                locals_[methname] = _create_op_proxy(methname)
            else:
                attr_names.add(methname)

    globals_['_install_proxy'] = _install_proxy
    globals_['_remove_proxy'] = _remove_proxy
    globals_['_add_proxied_method'] = _add_proxied_method

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
                "Can't invoke function '%s', as the proxy object has "
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
        exec_(func_text, globals_, lcl)
        return lcl[name]

    for methname in dir(cls):
        _add_proxied_method(methname)


def asbool(value):
    return value is not None and \
        value.lower() == 'true'


def rev_id():
    val = int(uuid.uuid4()) % 100000000000000
    return hex(val)[2:-1]


def to_tuple(x, default=None):
    if x is None:
        return default
    elif isinstance(x, string_types):
        return (x, )
    elif isinstance(x, collections.Iterable):
        return tuple(x)
    else:
        raise ValueError("Don't know how to turn %r into a tuple" % x)


class memoized_property(object):

    """A read-only @property that is only evaluated once."""

    def __init__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return self
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
        decorated.__defaults__ = getattr(fn, '__func__', fn).__defaults__
        update_wrapper(decorated, fn)
        if hasattr(decorated, '__wrapped__'):
            # update_wrapper in py3k applies __wrapped__, which causes
            # inspect.getargspec() to ignore the extra arguments on our
            # wrapper as of Python 3.4.  We need this for the
            # "module class proxy" thing though, so just del the __wrapped__
            # for now. See #175 as well as bugs.python.org/issue17482
            del decorated.__wrapped__
        return decorated

    return decorate


class Dispatcher(object):
    def __init__(self):
        self._registry = {}

    def dispatch_for(self, target, qualifier='default'):
        def decorate(fn):
            assert isinstance(target, type)
            assert target not in self._registry
            self._registry[(target, qualifier)] = fn
            return fn
        return decorate

    def dispatch(self, obj, qualifier='default'):
        for spcls in type(obj).__mro__:
            if qualifier != 'default' and (spcls, qualifier) in self._registry:
                return self._registry[(spcls, qualifier)]
            elif (spcls, 'default') in self._registry:
                return self._registry[(spcls, 'default')]
        else:
            raise ValueError("no dispatch function for object: %s" % obj)
