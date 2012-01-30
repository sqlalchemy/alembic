from __future__ import with_statement

import os
from alembic import util
import shutil
import re
import inspect
import datetime

_rev_file = re.compile(r'([a-z0-9A-Z]+)(?:_.*)?\.py$')
_legacy_rev = re.compile(r'([a-f0-9]+)\.py$')
_mod_def_re = re.compile(r'(upgrade|downgrade)_([a-z0-9]+)')
_slug_re = re.compile(r'\w+')
_default_file_template = "%(rev)s_%(slug)s"

class ScriptDirectory(object):
    """Provides operations upon an Alembic script directory.
    
    """
    def __init__(self, dir, file_template=_default_file_template):
        self.dir = dir
        self.versions = os.path.join(self.dir, 'versions')
        self.file_template = file_template

        if not os.access(dir, os.F_OK):
            raise util.CommandError("Path doesn't exist: %r.  Please use "
                        "the 'init' command to create a new "
                        "scripts folder." % dir)

    @classmethod
    def from_config(cls, config):
        return ScriptDirectory(
                    config.get_main_option('script_location'),
                    file_template = config.get_main_option(
                                        'file_template', 
                                        _default_file_template)
                    )

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
        id_ = self._as_rev_number(id_)
        try:
            return self._revision_map[id_]
        except KeyError:
            # do a partial lookup
            revs = [x for x in self._revision_map 
                    if x is not None and x.startswith(id_)]
            if not revs:
                raise util.CommandError("No such revision '%s'" % id_)
            elif len(revs) > 1:
                raise util.CommandError(
                            "Multiple revisions start "
                            "with '%s', %s..." % (
                                id_,
                                ", ".join("'%s'" % r for r in revs[0:3])
                            ))
            else:
                return self._revision_map[revs[0]]

    def _as_rev_number(self, id_):
        if id_ == 'head':
            id_ = self._current_head()
        elif id_ == 'base':
            id_ = None
        return id_

    def _revs(self, upper, lower):
        lower = self._get_rev(lower)
        upper = self._get_rev(upper)
        script = upper
        while script != lower:
            yield script
            downrev = script.down_revision
            script = self._revision_map[downrev]
            if script is None and lower is not None:
                raise util.CommandError(
                        "Couldn't find revision %s" % downrev)

    def upgrade_from(self, destination, current_rev, context):
        revs = self._revs(destination, current_rev)
        return [
            (script.module.upgrade, script.down_revision, script.revision)
            for script in reversed(list(revs))
            ]

    def downgrade_to(self, destination, current_rev, context):
        revs = self._revs(current_rev, destination)
        return [
            (script.module.downgrade, script.revision, script.down_revision)
            for script in revs
            ]

    def run_env(self):
        """Run the script environment.
        
        This basically runs the ``env.py`` script present
        in the migration environment.   It is called exclusively
        by the command functions in :mod:`alembic.command`.
        
        
        """
        util.load_python_file(self.dir, 'env.py')

    @property
    def env_py_location(self):
        return os.path.abspath(os.path.join(self.dir, "env.py"))

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

    def _rev_path(self, rev_id, message):
        slug = "_".join(_slug_re.findall(message or "")).lower()[0:20]
        filename = "%s.py" % (
            self.file_template % {'rev':rev_id, 'slug':slug}
        )
        return os.path.join(self.versions, filename)

    def _current_head(self):
        current_heads = self._get_heads()
        if len(current_heads) > 1:
            raise util.CommandError("Only a single head supported so far...")
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

    def generate_rev(self, revid, message, refresh=False, **kw):
        current_head = self._current_head()
        path = self._rev_path(revid, message)
        self.generate_template(
            os.path.join(self.dir, "script.py.mako"),
            path,
            up_revision=str(revid),
            down_revision=current_head,
            create_date=datetime.datetime.now(),
            message=message if message is not None else ("empty message"),
            **kw
        )
        if refresh:
            script = Script.from_path(path)
            self._revision_map[script.revision] = script
            if script.down_revision:
                self._revision_map[script.down_revision].\
                        add_nextrev(script.revision)
            return script
        else:
            return revid


class Script(object):
    """Represent a single revision file in a ``versions/`` directory."""
    nextrev = frozenset()

    def __init__(self, module, rev_id, path):
        self.module = module
        self.revision = rev_id
        self.path = path
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
        if not hasattr(module, "revision"):
            # attempt to get the revision id from the script name,
            # this for legacy only
            m = _legacy_rev.match(filename)
            if not m:
                raise util.CommandError(
                        "Could not determine revision id from filename %s. "
                        "Be sure the 'revision' variable is "
                        "declared inside the script (please see 'Upgrading "
                        "from Alembic 0.1 to 0.2' in the documentation)." 
                        % filename)
            else:
                revision = m.group(1)
        else:
            revision = module.revision
        return Script(module, revision, os.path.join(dir_, filename))
