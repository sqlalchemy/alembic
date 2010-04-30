from alembic import command, util
from optparse import OptionParser
import ConfigParser
import inspect
import os
import sys
    
class Config(object):
    def __init__(self, file_):
        self.config_file_name = file_
    
    @util.memoized_property
    def file_config(self):
        file_config = ConfigParser.ConfigParser()
        file_config.read([self.config_file_name])
        return file_config
        
    def get_template_directory(self):
        # TODO: what's the official way to get at
        # setuptools-installed datafiles ?
        return os.path.join(os.path.dirname(__file__), '..', 'templates')

    def get_section(self, name):
        return dict(self.file_config.items(name))

    def get_main_option(self, name, default=None):
        if not self.file_config.has_section('alembic'):
            util.err("No config file %r found, or file has no "
                                "'[alembic]' section" % self.config_file_name)
        if self.file_config.get('alembic', name):
            return self.file_config.get('alembic', name)
        else:
            return default

def main(argv):

    # TODO: 
    # OK, what's the super option parser library that 
    # allows <command> plus command-specfic sub-options,
    # and derives everything from callables ?
    # we're inventing here a bit.

    commands = {}
    for fn in [getattr(command, n) for n in dir(command)]:
        if inspect.isfunction(fn) and \
            fn.__name__[0] != '_' and \
            fn.__module__ == 'alembic.command':

            spec = inspect.getargspec(fn)
            if spec[3]:
                positional = spec[0][1:-len(spec[3])]
                kwarg = spec[0][-len(spec[3]):]
            else:
                positional = spec[0][1:]
                kwarg = []

            commands[fn.__name__] = {
                'name':fn.__name__,
                'fn':fn,
                'positional':positional,
                'kwargs':kwarg
            }

    def format_cmd(cmd):
        return "%s %s" % (
            cmd['name'], 
            " ".join(["<%s>" % p for p in cmd['positional']])
        )

    def format_opt(cmd, padding=32):
        opt = format_cmd(cmd)
        return "  " + opt + \
                ((padding - len(opt)) * " ") + cmd['fn'].__doc__

    parser = OptionParser(
                "usage: %prog [options] <command> [command arguments]\n\n"
                "Available Commands:\n" +
                "\n".join(sorted([
                    format_opt(cmd)
                    for cmd in commands.values()
                ])) +
                "\n\n<revision> is a hex revision id, 'head' or 'base'."
                )

    parser.add_option("-c", "--config", 
                        type="string", 
                        default="alembic.ini", 
                        help="Alternate config file")
    parser.add_option("-t", "--template",
                        default='generic',
                        type="string",
                        help="Setup template for use with 'init'")
    parser.add_option("-m", "--message",
                        type="string",
                        help="Message string to use with 'revision'")
    parser.add_option("--sql",
                        action="store_true",
                        help="Dump output to a SQL file")

    cmd_line_options, cmd_line_args = parser.parse_args(argv[1:])

    if len(cmd_line_args) < 1:
        util.err("no command specified")

    cmd = cmd_line_args.pop(0).replace('-', '_')

    try:
        cmd_fn = commands[cmd]
    except KeyError:
        util.err("no such command %r" % cmd)

    kw = dict(
        (k, getattr(cmd_line_options, k)) 
        for k in cmd_fn['kwargs']
    )

    if len(cmd_line_args) != len(cmd_fn['positional']):
        util.err("Usage: %s %s [options]" % (
                        os.path.basename(argv[0]), 
                        format_cmd(cmd_fn)
                    ))

    cfg = Config(cmd_line_options.config)
    try:
        cmd_fn['fn'](cfg, *cmd_line_args, **kw)
    except util.CommandError, e:
        util.err(str(e))
