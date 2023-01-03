from __future__ import annotations

import io
import os
import sys
from typing import Sequence

from sqlalchemy.util import inspect_getfullargspec  # noqa
from sqlalchemy.util.compat import inspect_formatargspec  # noqa

is_posix = os.name == "posix"

py311 = sys.version_info >= (3, 11)
py39 = sys.version_info >= (3, 9)
py38 = sys.version_info >= (3, 8)


# produce a wrapper that allows encoded text to stream
# into a given buffer, but doesn't close it.
# not sure of a more idiomatic approach to this.
class EncodedIO(io.TextIOWrapper):
    def close(self) -> None:
        pass


if py39:
    from importlib import resources as importlib_resources
    from importlib import metadata as importlib_metadata
    from importlib.metadata import EntryPoint
else:
    import importlib_resources  # type:ignore # noqa
    import importlib_metadata  # type:ignore # noqa
    from importlib_metadata import EntryPoint  # type:ignore # noqa


def importlib_metadata_get(group: str) -> Sequence[EntryPoint]:
    ep = importlib_metadata.entry_points()
    if hasattr(ep, "select"):
        return ep.select(group=group)  # type: ignore
    else:
        return ep.get(group, ())  # type: ignore


def formatannotation_fwdref(annotation, base_module=None):
    """the python 3.7 _formatannotation with an extra repr() for 3rd party
    modules"""

    if getattr(annotation, "__module__", None) == "typing":
        return repr(annotation).replace("typing.", "")
    if isinstance(annotation, type):
        if annotation.__module__ in ("builtins", base_module):
            return annotation.__qualname__
        return repr(annotation.__module__ + "." + annotation.__qualname__)
    return repr(annotation)
