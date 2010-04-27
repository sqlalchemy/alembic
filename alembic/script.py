import os
from alembic import util
import shutil

class ScriptDirectory(object):
    def __init__(self, dir):
        self.dir = dir
        
    @classmethod
    def from_options(cls, options):
        return ScriptDirectory(options.get_main_option('script_location'))

    def generate_template(self, src, dest, **kw):
        util.status("Generating %s" % os.path.abspath(src),
            util.template_to_file,
            src, 
            dest,
            **kw
        )
        
    def copy_file(self, src, dest):
        util.status("Generating %s" % os.path.abspath(dest), 
                    shutil.copy, 
                    src, dest)
        