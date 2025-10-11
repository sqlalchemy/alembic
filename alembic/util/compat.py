# mypy: no-warn-unused-ignores

from __future__ import annotations

from configparser import ConfigParser
from importlib import metadata
from importlib.metadata import EntryPoint
import io
import os
from pathlib import Path
import sys
import typing
from typing import Any
from typing import Iterator
from typing import Sequence

if True:
    # zimports hack for too-long names
    from sqlalchemy.util import (  # noqa: F401
        inspect_getfullargspec as inspect_getfullargspec,
    )
    from sqlalchemy.util.compat import (  # noqa: F401
        inspect_formatargspec as inspect_formatargspec,
    )

is_posix = os.name == "posix"

py314 = sys.version_info >= (3, 14)
py313 = sys.version_info >= (3, 13)
py312 = sys.version_info >= (3, 12)
py311 = sys.version_info >= (3, 11)


# produce a wrapper that allows encoded text to stream
# into a given buffer, but doesn't close it.
# not sure of a more idiomatic approach to this.
class EncodedIO(io.TextIOWrapper):
    def close(self) -> None:
        pass


if py311:
    import tomllib as tomllib
else:
    import tomli as tomllib  # type: ignore  # noqa


if py312:

    def path_walk(
        path: Path, *, top_down: bool = True
    ) -> Iterator[tuple[Path, list[str], list[str]]]:
        return Path.walk(path)

    def path_relative_to(
        path: Path, other: Path, *, walk_up: bool = False
    ) -> Path:
        return path.relative_to(other, walk_up=walk_up)

else:

    def path_walk(
        path: Path, *, top_down: bool = True
    ) -> Iterator[tuple[Path, list[str], list[str]]]:
        for root, dirs, files in os.walk(path, topdown=top_down):
            yield Path(root), dirs, files

    def path_relative_to(
        path: Path, other: Path, *, walk_up: bool = False
    ) -> Path:
        """
        Calculate the relative path of 'path' with respect to 'other',
        optionally allowing 'path' to be outside the subtree of 'other'.

        OK I used AI for this, sorry

        """
        try:
            return path.relative_to(other)
        except ValueError:
            if walk_up:
                other_ancestors = list(other.parents) + [other]
                for ancestor in other_ancestors:
                    try:
                        return path.relative_to(ancestor)
                    except ValueError:
                        continue
                raise ValueError(
                    f"{path} is not in the same subtree as {other}"
                )
            else:
                raise


def importlib_metadata_get(group: str) -> Sequence[EntryPoint]:
    """provide a facade for metadata.entry_points().

    This is no longer a "compat" function as of Python 3.10, however
    the function is widely referenced in the test suite and elsewhere so is
    still in this module for compatibility reasons.

    """
    return metadata.entry_points().select(group=group)


def formatannotation_fwdref(
    annotation: Any, base_module: Any | None = None
) -> str:
    """vendored from python 3.7"""
    # copied over _formatannotation from sqlalchemy 2.0

    if isinstance(annotation, str):
        return annotation

    if getattr(annotation, "__module__", None) == "typing":
        return repr(annotation).replace("typing.", "").replace("~", "")
    if isinstance(annotation, type):
        if annotation.__module__ in ("builtins", base_module):
            return repr(annotation.__qualname__)
        return annotation.__module__ + "." + annotation.__qualname__
    elif isinstance(annotation, typing.TypeVar):
        return repr(annotation).replace("~", "")
    return repr(annotation).replace("~", "")


def read_config_parser(
    file_config: ConfigParser,
    file_argument: list[str | os.PathLike[str]],
) -> list[str]:
    return file_config.read(file_argument, encoding="locale")
