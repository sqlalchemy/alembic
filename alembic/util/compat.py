import io
import os
import sys

from sqlalchemy.util import inspect_getfullargspec  # noqa
from sqlalchemy.util.compat import inspect_formatargspec  # noqa

is_posix = os.name == "posix"

py39 = sys.version_info >= (3, 9)
py38 = sys.version_info >= (3, 8)
py37 = sys.version_info >= (3, 7)

string_types = (str,)
binary_type = bytes
text_type = str


# produce a wrapper that allows encoded text to stream
# into a given buffer, but doesn't close it.
# not sure of a more idiomatic approach to this.
class EncodedIO(io.TextIOWrapper):
    def close(self) -> None:
        pass


if py39:
    from importlib import resources as importlib_resources
else:
    import importlib_resources  # type:ignore[no-redef] # noqa

if py38:
    from importlib import metadata as importlib_metadata
else:
    import importlib_metadata  # type:ignore[no-redef] # noqa


def importlib_metadata_get(group):
    ep = importlib_metadata.entry_points()
    if hasattr(ep, "select"):
        return ep.select(group=group)
    else:
        return ep.get(group, ())
