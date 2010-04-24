import os

class ScriptDirectory(object):
    def __init__(self, dir):
        self.dir = dir
        
    @classmethod
    def from_options(cls, options, file_config):
        if options.dir:
            d = options.dir
        elif file_config.get('alembic', 'dir'):
            d = file_config.get('alembic', 'dir')
        else:
            d = os.path.join(os.path.curdir, "alembic_scripts")
        return Script(d)
        
    
    def init(self):
        if not os.access(self.dir, os.F_OK):
            os.makedirs(self.dir)
        f = open(os.path.join(self.dir, "env.py"), 'w')
        f.write(
        "def startup(options, file_config):"
        "    pass # TOOD"
        )
        f.close()
        
