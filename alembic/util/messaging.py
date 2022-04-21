from __future__ import annotations

from collections.abc import Iterable
import logging
import sys
import textwrap
from typing import Any
from typing import Callable
from typing import Optional
from typing import TextIO
from typing import Union
import warnings

from sqlalchemy.engine import url

from . import sqla_compat

log = logging.getLogger(__name__)

# disable "no handler found" errors
logging.getLogger("alembic").addHandler(logging.NullHandler())


try:
    import fcntl
    import termios
    import struct

    ioctl = fcntl.ioctl(0, termios.TIOCGWINSZ, struct.pack("HHHH", 0, 0, 0, 0))
    _h, TERMWIDTH, _hp, _wp = struct.unpack("HHHH", ioctl)
    if TERMWIDTH <= 0:  # can occur if running in emacs pseudo-tty
        TERMWIDTH = None
except (ImportError, IOError):
    TERMWIDTH = None


def write_outstream(stream: TextIO, *text) -> None:
    encoding = getattr(stream, "encoding", "ascii") or "ascii"
    for t in text:
        if not isinstance(t, bytes):
            t = t.encode(encoding, "replace")
        t = t.decode(encoding)
        try:
            stream.write(t)
        except IOError:
            # suppress "broken pipe" errors.
            # no known way to handle this on Python 3 however
            # as the exception is "ignored" (noisily) in TextIOWrapper.
            break


def status(_statmsg: str, fn: Callable, *arg, **kw) -> Any:
    newline = kw.pop("newline", False)
    msg(_statmsg + " ...", newline, True)
    try:
        ret = fn(*arg, **kw)
        write_outstream(sys.stdout, "  done\n")
        return ret
    except:
        write_outstream(sys.stdout, "  FAILED\n")
        raise


def err(message: str):
    log.error(message)
    msg("FAILED: %s" % message)
    sys.exit(-1)


def obfuscate_url_pw(input_url: str) -> str:
    u = url.make_url(input_url)
    if u.password:
        if sqla_compat.sqla_14:
            u = u.set(password="XXXXX")
        else:
            u.password = "XXXXX"  # type: ignore[misc]
    return str(u)


def warn(msg: str, stacklevel: int = 2) -> None:
    warnings.warn(msg, UserWarning, stacklevel=stacklevel)


def msg(msg: str, newline: bool = True, flush: bool = False) -> None:
    if TERMWIDTH is None:
        write_outstream(sys.stdout, msg)
        if newline:
            write_outstream(sys.stdout, "\n")
    else:
        # left indent output lines
        lines = textwrap.wrap(msg, TERMWIDTH)
        if len(lines) > 1:
            for line in lines[0:-1]:
                write_outstream(sys.stdout, "  ", line, "\n")
        write_outstream(sys.stdout, "  ", lines[-1], ("\n" if newline else ""))
    if flush:
        sys.stdout.flush()


def format_as_comma(value: Optional[Union[str, "Iterable[str]"]]) -> str:
    if value is None:
        return ""
    elif isinstance(value, str):
        return value
    elif isinstance(value, Iterable):
        return ", ".join(value)
    else:
        raise ValueError("Don't know how to comma-format %r" % value)
