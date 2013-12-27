import datetime
import os
import re
import shutil
from . import util

_rev_file = re.compile(r'.*\.py$')
_legacy_rev = re.compile(r'([a-f0-9]+)\.py$')
_mod_def_re = re.compile(r'(upgrade|downgrade)_([a-z0-9]+)')
_slug_re = re.compile(r'\w+')
_default_file_template = "%(rev)s_%(slug)s"
_relative_destination = re.compile(r'(?:\+|-)\d+')

class ScriptDirectory(object):
    """Provides operations upon an Alembic script directory.

    This object is useful to get information as to current revisions,
    most notably being able to get at the "head" revision, for schemes
    that want to test if the current revision in the database is the most
    recent::

        from alembic.script import ScriptDirectory
        from alembic.config import Config
        config = Config()
        config.set_main_option("script_location", "myapp:migrations")
        script = ScriptDirectory.from_config(config)

        head_revision = script.get_current_head()



    """
    def __init__(self, dir, file_template=_default_file_template,
                    truncate_slug_length=40):
        self.dir = dir
        self.versions = os.path.join(self.dir, 'versions')
        self.file_template = file_template
        self.truncate_slug_length = truncate_slug_length or 40

        if not os.access(dir, os.F_OK):
            raise util.CommandError("Path doesn't exist: %r.  Please use "
                        "the 'init' command to create a new "
                        "scripts folder." % dir)

    @classmethod
    def from_config(cls, config):
        """Produce a new :class:`.ScriptDirectory` given a :class:`.Config`
        instance.

        The :class:`.Config` need only have the ``script_location`` key
        present.

        """
        script_location = config.get_main_option('script_location')
        if script_location is None:
            raise util.CommandError("No 'script_location' key "
                                    "found in configuration.")
        truncate_slug_length = config.get_main_option("truncate_slug_length")
        if truncate_slug_length is not None:
            truncate_slug_length = int(truncate_slug_length)
        return ScriptDirectory(
                    util.coerce_resource_to_filename(script_location),
                    file_template=config.get_main_option(
                                        'file_template',
                                        _default_file_template),
                    truncate_slug_length=truncate_slug_length
                    )

    def walk_revisions(self, base="base", head="head"):
        """Iterate through all revisions.

        This is actually a breadth-first tree traversal,
        with leaf nodes being heads.

        """
        if head == "head":
            heads = set(self.get_heads())
        else:
            heads = set([head])
        while heads:
            todo = set(heads)
            heads = set()
            for head in todo:
                if head in heads:
                    break
                for sc in self.iterate_revisions(head, base):
                    if sc.is_branch_point and sc.revision not in todo:
                        heads.add(sc.revision)
                        break
                    else:
                        yield sc

    def get_revision(self, id_):
        """Return the :class:`.Script` instance with the given rev id."""

        id_ = self.as_revision_number(id_)
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

    _get_rev = get_revision

    def as_revision_number(self, id_):
        """Convert a symbolic revision, i.e. 'head' or 'base', into
        an actual revision number."""

        if id_ == 'head':
            id_ = self.get_current_head()
        elif id_ == 'base':
            id_ = None
        return id_

    _as_rev_number = as_revision_number

    def iterate_revisions(self, upper, lower):
        """Iterate through script revisions, starting at the given
        upper revision identifier and ending at the lower.

        The traversal uses strictly the `down_revision`
        marker inside each migration script, so
        it is a requirement that upper >= lower,
        else you'll get nothing back.

        The iterator yields :class:`.Script` objects.

        """
        if upper is not None and _relative_destination.match(upper):
            relative = int(upper)
            revs = list(self._iterate_revisions("head", lower))
            revs = revs[-relative:]
            if len(revs) != abs(relative):
                raise util.CommandError("Relative revision %s didn't "
                            "produce %d migrations" % (upper, abs(relative)))
            return iter(revs)
        elif lower is not None and _relative_destination.match(lower):
            relative = int(lower)
            revs = list(self._iterate_revisions(upper, "base"))
            revs = revs[0:-relative]
            if len(revs) != abs(relative):
                raise util.CommandError("Relative revision %s didn't "
                            "produce %d migrations" % (lower, abs(relative)))
            return iter(revs)
        else:
            return self._iterate_revisions(upper, lower)

    def _iterate_revisions(self, upper, lower):
        lower = self.get_revision(lower)
        upper = self.get_revision(upper)
        orig = lower.revision if lower else 'base', \
                upper.revision if upper else 'base'
        script = upper
        while script != lower:
            if script is None and lower is not None:
                raise util.CommandError(
                        "Revision %s is not an ancestor of %s" % orig)
            yield script
            downrev = script.down_revision
            script = self._revision_map[downrev]

    def _upgrade_revs(self, destination, current_rev):
        revs = self.iterate_revisions(destination, current_rev)
        return [
            (script.module.upgrade, script.down_revision, script.revision,
                script.doc)
            for script in reversed(list(revs))
            ]

    def _downgrade_revs(self, destination, current_rev):
        revs = self.iterate_revisions(current_rev, destination)
        return [
            (script.module.downgrade, script.revision, script.down_revision,
                script.doc)
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
            script = Script._from_filename(self.versions, file_)
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

    def _rev_path(self, rev_id, message, create_date):
        slug = "_".join(_slug_re.findall(message or "")).lower()
        if len(slug) > self.truncate_slug_length:
            slug = slug[:self.truncate_slug_length].rsplit('_', 1)[0] + '_'
        filename = "%s.py" % (
            self.file_template % {
                'rev': rev_id,
                'slug': slug,
                'year': create_date.year,
                'month': create_date.month,
                'day': create_date.day,
                'hour': create_date.hour,
                'minute': create_date.minute,
                'second': create_date.second
            }
        )
        return os.path.join(self.versions, filename)

    def get_current_head(self):
        """Return the current head revision.

        If the script directory has multiple heads
        due to branching, an error is raised.

        Returns a string revision number.

        """
        current_heads = self.get_heads()
        if len(current_heads) > 1:
            raise util.CommandError('Only a single head is supported. The '
                'script directory has multiple heads (due to branching), which '
                'must be resolved by manually editing the revision files to '
                'form a linear sequence. Run `alembic branches` to see the '
                'divergence(s).')
            raise util.CommandError("Only a single head supported so far...")
        if current_heads:
            return current_heads[0]
        else:
            return None

    _current_head = get_current_head
    """the 0.2 name, for backwards compat."""

    def get_heads(self):
        """Return all "head" revisions as strings.

        Returns a list of string revision numbers.

        This is normally a list of length one,
        unless branches are present.  The
        :meth:`.ScriptDirectory.get_current_head()` method
        can be used normally when a script directory
        has only one head.

        """
        heads = []
        for script in self._revision_map.values():
            if script and script.is_head:
                heads.append(script.revision)
        return heads

    def get_base(self):
        """Return the "base" revision as a string.

        This is the revision number of the script that
        has a ``down_revision`` of None.

        Behavior is not defined if more than one script
        has a ``down_revision`` of None.

        """
        for script in self._revision_map.values():
            if script and script.down_revision is None \
                and script.revision in self._revision_map:
                return script.revision
        else:
            return None

    def _generate_template(self, src, dest, **kw):
        util.status("Generating %s" % os.path.abspath(dest),
            util.template_to_file,
            src,
            dest,
            **kw
        )

    def _copy_file(self, src, dest):
        util.status("Generating %s" % os.path.abspath(dest),
                    shutil.copy,
                    src, dest)

    def generate_revision(self, revid, message, refresh=False, **kw):
        """Generate a new revision file.

        This runs the ``script.py.mako`` template, given
        template arguments, and creates a new file.

        :param revid: String revision id.  Typically this
         comes from ``alembic.util.rev_id()``.
        :param message: the revision message, the one passed
         by the -m argument to the ``revision`` command.
        :param refresh: when True, the in-memory state of this
         :class:`.ScriptDirectory` will be updated with a new
         :class:`.Script` instance representing the new revision;
         the :class:`.Script` instance is returned.
         If False, the file is created but the state of the
         :class:`.ScriptDirectory` is unmodified; ``None``
         is returned.

        """
        current_head = self.get_current_head()
        create_date = datetime.datetime.now()
        path = self._rev_path(revid, message, create_date)
        self._generate_template(
            os.path.join(self.dir, "script.py.mako"),
            path,
            up_revision=str(revid),
            down_revision=current_head,
            create_date=create_date,
            message=message if message is not None else ("empty message"),
            **kw
        )
        if refresh:
            script = Script._from_path(path)
            self._revision_map[script.revision] = script
            if script.down_revision:
                self._revision_map[script.down_revision].\
                        add_nextrev(script.revision)
            return script
        else:
            return None


class Script(object):
    """Represent a single revision file in a ``versions/`` directory.

    The :class:`.Script` instance is returned by methods
    such as :meth:`.ScriptDirectory.iterate_revisions`.

    """

    nextrev = frozenset()

    def __init__(self, module, rev_id, path):
        self.module = module
        self.revision = rev_id
        self.path = path
        self.down_revision = getattr(module, 'down_revision', None)

    revision = None
    """The string revision number for this :class:`.Script` instance."""

    module = None
    """The Python module representing the actual script itself."""

    path = None
    """Filesystem path of the script."""

    down_revision = None
    """The ``down_revision`` identifier within the migration script."""

    @property
    def doc(self):
        """Return the docstring given in the script."""

        return re.split("\n\n", self.longdoc)[0]

    @property
    def longdoc(self):
        """Return the docstring given in the script."""

        doc = self.module.__doc__
        if doc:
            if hasattr(self.module, "_alembic_source_encoding"):
                doc = doc.decode(self.module._alembic_source_encoding)
            return doc.strip()
        else:
            return ""

    def add_nextrev(self, rev):
        self.nextrev = self.nextrev.union([rev])

    @property
    def is_head(self):
        """Return True if this :class:`.Script` is a 'head' revision.

        This is determined based on whether any other :class:`.Script`
        within the :class:`.ScriptDirectory` refers to this
        :class:`.Script`.   Multiple heads can be present.

        """
        return not bool(self.nextrev)

    @property
    def is_branch_point(self):
        """Return True if this :class:`.Script` is a branch point.

        A branchpoint is defined as a :class:`.Script` which is referred
        to by more than one succeeding :class:`.Script`, that is more
        than one :class:`.Script` has a `down_revision` identifier pointing
        here.

        """
        return len(self.nextrev) > 1

    @property
    def log_entry(self):
        return \
            "Rev: %s%s%s\n" \
            "Parent: %s\n" \
            "Path: %s\n" \
            "\n%s\n" % (
                self.revision,
                " (head)" if self.is_head else "",
                " (branchpoint)" if self.is_branch_point else "",
                self.down_revision,
                self.path,
                "\n".join(
                    "    %s" % para
                    for para in self.longdoc.splitlines()
                )
            )

    def __str__(self):
        return "%s -> %s%s%s, %s" % (
                        self.down_revision,
                        self.revision,
                        " (head)" if self.is_head else "",
                        " (branchpoint)" if self.is_branch_point else "",
                        self.doc)

    @classmethod
    def _from_path(cls, path):
        dir_, filename = os.path.split(path)
        return cls._from_filename(dir_, filename)

    @classmethod
    def _from_filename(cls, dir_, filename):
        if not _rev_file.match(filename):
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
