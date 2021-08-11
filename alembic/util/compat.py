import io
import os

from sqlalchemy.util import inspect_getfullargspec  # noqa
from sqlalchemy.util.compat import inspect_formatargspec  # noqa

is_posix = os.name == "posix"


string_types = (str,)
binary_type = bytes
text_type = str


# produce a wrapper that allows encoded text to stream
# into a given buffer, but doesn't close it.
# not sure of a more idiomatic approach to this.
class EncodedIO(io.TextIOWrapper):
    def close(self) -> None:
        pass
