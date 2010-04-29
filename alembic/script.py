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
            raise util.CommandError("Path doesn't exist: %r.  Please use "
                        "the 'init' command to create a new "
                        "scripts folder." % dir)
        
    @classmethod
    def from_config(cls, config):
        return ScriptDirectory(
                    config.get_main_option('script_location'))
    
    def _get_rev(self, id_):
        if id_ == 'head':
            id_ = self._current_head()
        elif id_ == 'base':
            id_ = None
        try:
            return self._revision_map[id_]
        except KeyError:
            raise util.CommandError("No such revision %s" % id_)
            
    def _revs(self, upper, lower):
        lower = self._get_rev(lower)
        upper = self._get_rev(upper)
        script = upper
        while script != lower:
            yield script
            script = self._revision_map[script.down_revision]
        
    def upgrade_from(self, destination, current_rev):
        return [
            (script.module.upgrade, script.revision) for script in 
            reversed(list(self._revs(destination, current_rev)))
            ]
        
    def downgrade_to(self, destination, current_rev):
        return [
            (script.module.downgrade, script.down_revision) for script in 
            self._revs(current_rev, destination)
            ]
        
    def run_env(self):
        util.load_python_file(self.dir, 'env.py')

    @util.memoized_property
    def _revision_map(self):
        map_ = {}
        for file_ in os.listdir(self.versions):
            script = Script.from_path(self.versions, file_)
            if script is None:
                continue
            if script.revision in map_:
                util.warn("Revision %s is present more than once" % script.revision)
            map_[script.revision] = script
        for rev in map_.values():
            if rev.down_revision is None:
                continue
            if rev.down_revision not in map_:
                util.warn("Revision %s referenced from %s is not present"
                            % (rev.down_revision, rev))
                rev.down_revision = None
            else:
                map_[rev.down_revision].nextrev = rev.revision
        map_[None] = None
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
            if script and script.nextrev is None:
                heads.append(script.revision)
        return heads
    
    def _get_origin(self):
        # TODO: keep map sorted chronologically
        
        for script in self._revision_map.values():
            if script.down_revision is None \
                and script.revision in self._revision_map:
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
        self._revision_map[script.revision] = script
        if script.down_revision:
            self._revision_map[script.down_revision].nextrev = script.revision
        return script
        
class Script(object):
    nextrev = None
    
    def __init__(self, module, rev_id):
        self.module = module
        self.revision = rev_id
        self.down_revision = getattr(module, 'down_revision', None)
    
    def __str__(self):
        return "revision %s" % self.revision
    
    @classmethod
    def from_path(cls, dir_, filename):
        m = _rev_file.match(filename)
        if not m:
            return None
        
        module = util.load_python_file(dir_, filename)
        return Script(module, m.group(1))
        