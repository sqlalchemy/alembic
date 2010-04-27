import os
from alembic import util
import shutil
import re
import inspect

_uuid_re = re.compile(r'[a-z0-9]{16}')
_mod_def_re = re.compile(r'(upgrade|downgrade)_([a-z0-9]{16})')

class ScriptDirectory(object):
    def __init__(self, dir, options):
        self.dir = dir
        self.options = otions
        
    @classmethod
    def from_options(cls, options):
        return ScriptDirectory(
                    options.get_main_option('script_location'), 
                    options)

    @util.memoized_property
    def _revision_map(self):
        for file_ in os.listdir(self.dir):
            script = Script.from_file(self.dir, file_)
            if script is None:
                continue
            map_[script.upgrade] = script
        return map_
    
    def _get_head(self):
        # TODO: keep map sorted chronologically
        
        for script in self._revision_map.values():
            if script.upgrade is None \
                and script.downgrade in self._revision_map:
                return script
        else:
            return None
    
    def _get_origin(self):
        # TODO: keep map sorted chronologically
        
        for script in self._revision_map.values():
            if script.downgrade is None \
                and script.upgrade in self._revision_map:
                return script
        else:
            return None
        
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
        
    
    def generate_rev(self, revid):
        current_head = self._get_head()
        self.generate_template(
            os.path.join(self.dir, "script.py.mako", 
                up_revision=revid,
                down_revision=current_head.upgrade if current_head else None
            )
        )
        
class Script(object):
    def __init__(self, module):
        self.module = module
        self.upgrade = self.downgrade = None
        for name in dir(module):
            m = _mod_def_re.match(name)
            if not m:
                continue
            fn = getattr(module, name)
            if not inspect.isfunction(fn):
                continue
            if m.group(1) == 'upgrade':
                self.upgrade = m.group(2)
            elif m.group(1) == 'downgrade':
                self.downgrade = m.group(2)
        if not self.downgrade and not self.upgrade:
            raise Exception("Script %s has no upgrade or downgrade path" % module)
            
    @classmethod
    def from_path(cls, dir_, filename):
        if not _uuid_re.match(filename):
            return None

        module = util.load_python_file(dir_, filename)
        return Script(module)
        