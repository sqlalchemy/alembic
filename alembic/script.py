import os

class ScriptDirectory(object):
    def __init__(self, dir):
        self.dir = dir
        
    @classmethod
    def from_options(cls, options):
        return ScriptDirectory(options.get_main_option('script_location'))

