from mako.template import Template
import sys
import os
import textwrap
from sqlalchemy import util

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

def status(message, fn, *arg, **kw):
    msg(message + "...", False)
    try:
        ret = fn(*arg, **kw)
        sys.stdout.write("done\n")
        return ret
    except:
        sys.stdout.write("FAILED\n")
        raise


def msg(msg, newline=True):
    lines = textwrap.wrap(msg, width)
    if len(lines) > 1:
        for line in lines[0:-1]:
            sys.stdout.write("  " +line + "\n")
    sys.stdout.write("  " + lines[-1] + ("\n" if newline else ""))
