import collections
import inspect
import io
import os
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Type

is_posix = os.name == "posix"

ArgSpec = collections.namedtuple(
    "ArgSpec", ["args", "varargs", "keywords", "defaults"]
)


def inspect_getargspec(func: Callable) -> ArgSpec:
    """getargspec based on fully vendored getfullargspec from Python 3.3."""

    if inspect.ismethod(func):
        func = func.__func__  # type: ignore
    if not inspect.isfunction(func):
        raise TypeError("{!r} is not a Python function".format(func))

    co = func.__code__
    if not inspect.iscode(co):
        raise TypeError("{!r} is not a code object".format(co))

    nargs = co.co_argcount
    names = co.co_varnames
    nkwargs = co.co_kwonlyargcount
    args = list(names[:nargs])

    nargs += nkwargs
    varargs = None
    if co.co_flags & inspect.CO_VARARGS:
        varargs = co.co_varnames[nargs]
        nargs = nargs + 1
    varkw = None
    if co.co_flags & inspect.CO_VARKEYWORDS:
        varkw = co.co_varnames[nargs]

    return ArgSpec(args, varargs, varkw, func.__defaults__)  # type: ignore


string_types = (str,)
binary_type = bytes
text_type = str


def _formatannotation(annotation, base_module=None):
    """vendored from python 3.7"""

    if getattr(annotation, "__module__", None) == "typing":
        return repr(annotation).replace("typing.", "")
    if isinstance(annotation, type):
        if annotation.__module__ in ("builtins", base_module):
            return annotation.__qualname__
        return annotation.__module__ + "." + annotation.__qualname__
    return repr(annotation)


def inspect_formatargspec(
    args: List[str],
    varargs: Optional[str] = None,
    varkw: Optional[str] = None,
    defaults: Optional[Any] = None,
    kwonlyargs: tuple = (),
    kwonlydefaults: Dict[Any, Any] = {},
    annotations: Dict[Any, Any] = {},
    formatarg: Type[str] = str,
    formatvarargs: Callable = lambda name: "*" + name,
    formatvarkw: Callable = lambda name: "**" + name,
    formatvalue: Callable = lambda value: "=" + repr(value),
    formatreturns: Callable = lambda text: " -> " + text,
    formatannotation: Callable = _formatannotation,
) -> str:
    """Copy formatargspec from python 3.7 standard library.

    Python 3 has deprecated formatargspec and requested that Signature
    be used instead, however this requires a full reimplementation
    of formatargspec() in terms of creating Parameter objects and such.
    Instead of introducing all the object-creation overhead and having
    to reinvent from scratch, just copy their compatibility routine.

    """

    def formatargandannotation(arg):
        result = formatarg(arg)
        if arg in annotations:
            result += ": " + formatannotation(annotations[arg])
        return result

    specs = []
    if defaults:
        firstdefault = len(args) - len(defaults)
    for i, arg in enumerate(args):
        spec = formatargandannotation(arg)
        if defaults and i >= firstdefault:
            spec = spec + formatvalue(defaults[i - firstdefault])
        specs.append(spec)
    if varargs is not None:
        specs.append(formatvarargs(formatargandannotation(varargs)))
    else:
        if kwonlyargs:
            specs.append("*")
    if kwonlyargs:
        for kwonlyarg in kwonlyargs:
            spec = formatargandannotation(kwonlyarg)
            if kwonlydefaults and kwonlyarg in kwonlydefaults:
                spec += formatvalue(kwonlydefaults[kwonlyarg])
            specs.append(spec)
    if varkw is not None:
        specs.append(formatvarkw(formatargandannotation(varkw)))
    result = "(" + ", ".join(specs) + ")"
    if "return" in annotations:
        result += formatreturns(formatannotation(annotations["return"]))
    return result


# produce a wrapper that allows encoded text to stream
# into a given buffer, but doesn't close it.
# not sure of a more idiomatic approach to this.
class EncodedIO(io.TextIOWrapper):
    def close(self) -> None:
        pass
