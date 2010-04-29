import os
from alembic import util
import shutil
import re
import inspect

_rev_file = re.compile(r'([a-z0-9]+)\.py$')
_mod_def_re = re.compile(r'(upgrade|downgrade)_([a-z0-9]+)')

class ScriptDirectory(object):
    def __init__(self, dir):
        self.dir = dir
        self.versions = os.path.join(self.dir, 'versions')
        
        if not os.access(dir, os.F_OK):
            util.err("Path doesn't exist: %r.  Please use "
                        "the 'init' command to create a new "
                        "scripts folder." % dir)
        
    @classmethod
    def from_config(cls, options):
        return ScriptDirectory(
                    options.get_main_option('script_location'))

    def upgrade_from(self, current_rev):
        head = self._current_head()
        script = self._revision_map[head]
        scripts = []
        while script.upgrade != current_rev:
            scripts.append((script.module.upgrade, script.upgrade))
            script = self._revision_map[script.downgrade]
        return reversed(scripts)
        
    def downgrade_to(self, destination, current_rev):
        return []
        
    def run_env(self):
        util.load_python_file(self.dir, 'env.py')

    @util.memoized_property
    def _revision_map(self):
        map_ = {}
        for file_ in os.listdir(self.versions):
            script = Script.from_path(self.versions, file_)
            if script is None:
                continue
            if script.upgrade in map_:
                util.warn("Revision %s is present more than once" % script.upgrade)
            map_[script.upgrade] = script
        for rev in map_.values():
            if rev.downgrade is None:
                continue
            if rev.downgrade not in map_:
                util.warn("Revision %s referenced from %s is not present"
                            % (rev.downgrade, rev))
                rev.downgrade = None
            else:
                map_[rev.downgrade].nextrev = rev.upgrade
        return map_
    
    def _current_head(self):
        current_heads = self._get_heads()
        if len(current_heads) > 1:
            raise Exception("Only a single head supported so far...")
        if current_heads:
            return current_heads[0]
        else:
            return None
        
    def _get_heads(self):
        # TODO: keep map sorted chronologically
        heads = []
        for script in self._revision_map.values():
            if script.nextrev is None:
                heads.append(script.upgrade)
        return heads
    
    def _get_origin(self):
        # TODO: keep map sorted chronologically
        
        for script in self._revision_map.values():
            if script.downgrade is None \
                and script.upgrade in self._revision_map:
                return script
        else:
            return None
        
    def generate_template(self, src, dest, **kw):
        util.status("Generating %s" % os.path.abspath(dest),
            util.template_to_file,
            src, 
            dest,
            **kw
        )
        
    def copy_file(self, src, dest):
        util.status("Generating %s" % os.path.abspath(dest), 
                    shutil.copy, 
                    src, dest)
    
    def generate_rev(self, revid, message):
        current_head = self._current_head()
        filename = "%s.py" % revid
        self.generate_template(
            os.path.join(self.dir, "script.py.mako"),
            os.path.join(self.versions, filename), 
            up_revision=str(revid),
            down_revision=current_head,
            message=message if message is not None else ("Alembic revision %s" % revid)
        )
        script = Script.from_path(self.versions, filename)
        self._revision_map[script.upgrade] = script
        if script.downgrade:
            self._revision_map[script.downgrade].nextrev = script.upgrade
        return script
        
class Script(object):
    nextrev = None
    
    def __init__(self, module, rev_id):
        self.module = module
        self.upgrade = rev_id
        self.downgrade = getattr(module, 'down_revision', None)
    
    def __str__(self):
        return "revision %s" % self.upgrade
        
    @classmethod
    def from_path(cls, dir_, filename):
        m = _rev_file.match(filename)
        if not m:
            return None
        
        module = util.load_python_file(dir_, filename)
        return Script(module, m.group(1))
        