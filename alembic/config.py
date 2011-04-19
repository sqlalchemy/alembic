from alembic import command, util, package_dir
from argparse import ArgumentParser
import ConfigParser
import inspect
import os

class Config(object):
    def __init__(self, file_):
        self.config_file_name = file_

    @util.memoized_property
    def file_config(self):
        file_config = ConfigParser.ConfigParser()
        file_config.read([self.config_file_name])
        return file_config

    def get_template_directory(self):
        return os.path.join(package_dir, 'templates')

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

    def add_options(parser, positional, kwargs):
        parser.add_argument("-c", "--config", 
                            type=str, 
                            default="alembic.ini", 
                            help="Alternate config file")
        if 'template' in kwargs:
            parser.add_argument("-t", "--template",
                            default='generic',
                            type=str,
                            help="Setup template for use with 'init'")
        if 'message' in kwargs:
            parser.add_argument("-m", "--message",
                            type=str,
                            help="Message string to use with 'revision'")
        if 'sql' in kwargs:
            parser.add_argument("--sql",
                            action="store_true",
                            help="Don't emit SQL to database - dump to "
                                    "standard output instead")

        positional_help = {
            'directory':"location of scripts directory",
            'revision':"revision identifier"
        }
        for arg in positional:
            subparser.add_argument(arg, help=positional_help.get(arg))

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

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

            subparser =  subparsers.add_parser(
                                fn.__name__, 
                                help=fn.__doc__)
            add_options(subparser, positional, kwarg)
            subparser.set_defaults(cmd=(fn, positional, kwarg))

    options = parser.parse_args()

    fn, positional, kwarg = options.cmd

    cfg = Config(options.config)
    try:
        fn(cfg, 
                    *[getattr(options, k) for k in positional], 
                    **dict((k, getattr(options, k)) for k in kwarg)
                )
    except util.CommandError, e:
        util.err(str(e))
