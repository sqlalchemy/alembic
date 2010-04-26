from mako.template import Template
import sys
import os
import textwrap
from sqlalchemy import util

NO_VALUE = util.symbol("NO_VALUE")


def template_to_file(template_file, dest, **kw):
    f = open(dest, 'w')
    f.write(
        Template(filename=template_file).render(**kw)
    )
    f.close()


def format_opt(opt, hlp, padding=22):
    return "  " + opt + \
        ((padding - len(opt)) * " ") + hlp

def status(msg, fn, *arg, **kw):
    sys.stdout.write("  " + msg + "...")
    try:
        ret = fn(*arg, **kw)
        sys.stdout.write("done\n")
        return ret
    except:
        sys.stdout.write("FAILED\n")
        raise


def msg(msg):
    sys.stdout.write(textwrap.wrap(msg))