from optparse import OptionParser
import ConfigParser
import textwrap

def get_option_parser():
    # TODO: 
    # OK, what's the super option parser library that 
    # allows <command> plus command-specfic sub-options ?
    
    # TODO: pull the commands from command.py directly here
    parser = OptionParser(
                "usage: %prog [options] <command>\n\n"
                "Available Commands:\n"
                "  list-templates\n"
                "  init\n"
                "  revision\n"
                "  upgrade\n"
                "  revert\n"
                "  history\n"
                "  splice\n"
                "  branches"
                )
    parser.add_option("-c", "--config", 
                        type="string", 
                        default="alembic.ini", 
                        help="Alternate config file")
    parser.add_option("-t", "--template",
                        type="string",
                        help="Setup template for use with 'init'")
    parser.add_option("-r", "--rev",
                        type="string",
                        help="Revsion identifier for usage with 'revert'"
    )
    return parser
    
class Options(object):
    def __init__(self, cmd_line_options):
        self.cmd_line_options = cmd_line_options
        self.file_config = ConfigParser.ConfigParser()
        # TODO: cfg file can come from options
        self.file_config.read(['alembic.cfg'])
    
    def get_section(self, name):
        return dict(self.file_config.items(name))
        
    def get_main_option(self, name, default=None):
        if self.file_config.get('alembic', name):
            return self.file_config.get('alembic', name)
        else:
            return default
            
            