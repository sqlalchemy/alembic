from optparse import OptionParser
import ConfigParser
import inspect
import os
import sys
from alembic import util
    
def get_option_parser():
    from alembic import command

    # TODO: 
    # OK, what's the super option parser library that 
    # allows <command> plus command-specfic sub-options ?
    # we're inventing here a bit.
    
    commands = [
        (fn.__name__.replace('_', '-'), fn.__doc__) for fn in
        [getattr(command, name) for name in sorted(dir(command))]
        if inspect.isfunction(fn) and 
            fn.__name__[0] != '_' and 
            fn.__module__ == 'alembic.command'
    ]
    
    parser = OptionParser(
                "usage: %prog [options] <command> [command arguments]\n\n"
                "Available Commands:\n" +
                "\n".join([
                    util.format_opt(cmd, hlp)
                    for cmd, hlp in commands
                ])
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
    return parser
    
class Options(object):
    def __init__(self, parser, argv):
        self.parser = parser
        self.cmd_line_options, \
                self.cmd_line_args = parser.parse_args(argv[1:])
        if len(self.cmd_line_args) < 1:
            self.err("no command specified")
    
    @util.memoized_property
    def file_config(self):
        self.config_file_name = self.cmd_line_options.config
        file_config = ConfigParser.ConfigParser()
        file_config.read([self.config_file_name])
        return file_config
        
    def get_command(self):
        return self.cmd_line_args[0]
    
    def get_command_args(self, count, err):
        if len(self.cmd_line_args[1:]) != count:
            self.err(
                        "Command %r syntax: %r" % 
                        (self.get_command(), err))
        return self.cmd_line_args[1:]
    
    def get_template_directory(self):
        # TODO: what's the official way to get at
        # setuptools-installed datafiles ?
        return os.path.join(os.path.dirname(__file__), '..', 'templates')
        
    def get_section(self, name):
        return dict(self.file_config.items(name))
     
    def err(self, msg):
        util.msg(msg)
        sys.exit(-1)
        
    def get_main_option(self, name, default=None):
        if not self.file_config.has_section('alembic'):
            self.err("No config file %r found, or file has no "
                                "'[alembic]' section" % self.config_file_name)
        if self.file_config.get('alembic', name):
            return self.file_config.get('alembic', name)
        else:
            return default
            
            