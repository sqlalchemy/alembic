import os

class ScriptDirectory(object):
    def __init__(self, dir):
        self.dir = dir
        
    @classmethod
    def from_options(cls, options, file_config):
        return Script(file_config.get_main_option('script_location'))

    def init(self):
        if not os.access(self.dir, os.F_OK):
            os.makedirs(self.dir)
        # copy files...
