import os
from alembic import util
import shutil
import re
import inspect
import datetime

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

    def walk_revisions(self):
        """Iterate through all revisions.

        This is actually a breadth-first tree traversal,
        with leaf nodes being heads.

        """
        heads = set(self._get_heads())
        base = self._get_rev("base")
        while heads:
            todo = set(heads)
            heads = set()
            for head in todo:
                if head in heads:
                    break
                for sc in self._revs(head, base):
                    if sc.is_branch_point and sc.revision not in todo:
                        heads.add(sc.revision)
                        break
                    else:
                        yield sc

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
            downrev = script.down_revision
            script = self._revision_map[downrev]
            if script is None and lower is not None:
                raise util.CommandError("Couldn't find revision %s" % downrev)

    # TODO: call range_ok -> as_sql and do as_sql validation
    # here - range is required in as_sql mode, not allowed in 
    # non-as_sql mode. split into upgrade_to/upgrade_to_as_sql
    def upgrade_from(self, range_ok, destination, current_rev):
        if destination is not None and ':' in destination:
            if not range_ok:
                raise util.CommandError("Range revision not allowed")
            revs = self._revs(*reversed(destination.split(':', 2)))
        else:
            revs = self._revs(destination, current_rev)
        return [
            (script.module.upgrade, script.down_revision, script.revision) for script in 
            reversed(list(revs))
            ]

    # TODO: call range_ok -> as_sql and do as_sql validation
    # here - range is required in as_sql mode, not allowed in 
    # non-as_sql mode.  split into downgrade_to/downgrade_to_as_sql
    def downgrade_to(self, range_ok, destination, current_rev):
        if destination is not None and ':' in destination:
            if not range_ok:
                raise util.CommandError("Range revision not allowed")
            revs = self._revs(*destination.split(':', 2))
        else:
            revs = self._revs(current_rev, destination)

        return [
            (script.module.downgrade, script.revision, script.down_revision) for script in 
            revs
            ]

    def run_env(self):
        """Run the script environment.
        
        This basically runs the ``env.py`` script present
        in the migration environment.   It is called exclusively
        by the command functions in :mod:`alembic.command`.
        
        As ``env.py`` runs :func:`.context.configure_connection`, 
        the connection environment should be set up first.   This
        is typically achieved using the :func:`.context.opts`.
        
        
        """
        util.load_python_file(self.dir, 'env.py')

    @util.memoized_property
    def _revision_map(self):
        map_ = {}
        for file_ in os.listdir(self.versions):
            script = Script.from_filename(self.versions, file_)
            if script is None:
                continue
            if script.revision in map_:
                util.warn("Revision %s is present more than once" %
                                script.revision)
            map_[script.revision] = script
        for rev in map_.values():
            if rev.down_revision is None:
                continue
            if rev.down_revision not in map_:
                util.warn("Revision %s referenced from %s is not present"
                            % (rev.down_revision, rev))
                rev.down_revision = None
            else:
                map_[rev.down_revision].add_nextrev(rev.revision)
        map_[None] = None
        return map_

    def _rev_path(self, rev_id):
        filename = "%s.py" % rev_id
        return os.path.join(self.versions, filename)

    def write(self, rev_id, content):
        path = self._rev_path(rev_id)
        open(path, 'w').write(content)
        pyc_path = util.pyc_file_from_path(path)
        if os.access(pyc_path, os.F_OK):
            os.unlink(pyc_path)
        script = Script.from_path(path)
        old = self._revision_map[script.revision]
        if old.down_revision != script.down_revision:
            raise Exception("Can't change down_revision "
                                "on a refresh operation.")
        self._revision_map[script.revision] = script
        script.nextrev = old.nextrev

    def _current_head(self):
        current_heads = self._get_heads()
        if len(current_heads) > 1:
            raise Exception("Only a single head supported so far...")
        if current_heads:
            return current_heads[0]
        else:
            return None

    def _get_heads(self):
        heads = []
        for script in self._revision_map.values():
            if script and script.is_head:
                heads.append(script.revision)
        return heads

    def _get_origin(self):
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
        path = self._rev_path(revid)
        self.generate_template(
            os.path.join(self.dir, "script.py.mako"),
            path,
            up_revision=str(revid),
            down_revision=current_head,
            create_date=datetime.datetime.now(),
            message=message if message is not None else ("empty message")
        )
        script = Script.from_path(path)
        self._revision_map[script.revision] = script
        if script.down_revision:
            self._revision_map[script.down_revision].\
                    add_nextrev(script.revision)
        return script

class Script(object):
    nextrev = frozenset()

    def __init__(self, module, rev_id):
        self.module = module
        self.revision = rev_id
        self.down_revision = getattr(module, 'down_revision', None)

    @property
    def doc(self):
        return re.split(r"\n\n", self.module.__doc__)[0]

    def add_nextrev(self, rev):
        self.nextrev = self.nextrev.union([rev])

    @property
    def is_head(self):
        return not bool(self.nextrev)

    @property
    def is_branch_point(self):
        return len(self.nextrev) > 1

    def __str__(self):
        return "%s -> %s%s%s, %s" % (
                        self.down_revision, 
                        self.revision, 
                        " (head)" if self.is_head else "", 
                        " (branchpoint)" if self.is_branch_point else "",
                        self.doc)

    @classmethod
    def from_path(cls, path):
        dir_, filename = os.path.split(path)
        return cls.from_filename(dir_, filename)

    @classmethod
    def from_filename(cls, dir_, filename):
        m = _rev_file.match(filename)
        if not m:
            return None
        module = util.load_python_file(dir_, filename)
        return Script(module, m.group(1))
