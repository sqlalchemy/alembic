import ConfigParser
import inspect
import os
import sys
from alembic import util
    
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

            