
def get_option_parser():
    parser = OptionParser("usage: %prog [options] <command>")
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
            
            