

class Options(object):
    def __init__(self, options):
        self.options = options
        self.file_config = ConfigParser.ConfigParser()
        # TODO: cfg file can come from options
        self.file_config.read(['alembic.cfg'])
        
    def get_main_option(self, name, default=None):
        if getattr(self.options, name):
            return getattr(self.options, name)
        elif self.file_config.get('alembic', name):
            return self.file_config.get('alembic', name)
        else:
            return default
            
            