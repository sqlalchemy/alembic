import re

from . import util
_relative_destination = re.compile(r'(?:\+|-)\d+')


class RevisionMap(object):
    """Maintains a map of :class:`.Revision` objects.

    :class:`.RevisionMap` is used by :class:`.ScriptDirectory` to maintain
    and traverse the collection of :class:`.Script` objects, which are
    themselves instances of :class:`.Revision`.

    """
    def __init__(self, generator):
        self._generator = generator

    @util.memoized_property
    def _revision_map(self):
        map_ = {}

        for revision in self._generator():
            if revision.revision in map_:
                util.warn("Revision %s is present more than once" %
                          revision.revision)
            map_[revision.revision] = revision
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

    def walk_revisions(self, base="base", head="head"):
        """Iterate through all revisions.

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

    def get_current_head(self):
        """Return the current head revision.

        If the script directory has multiple heads
        due to branching, an error is raised;
        :meth:`.ScriptDirectory.get_heads` should be
        preferred.

        :return: a string revision number.

        .. seealso::

            :meth:`.ScriptDirectory.get_heads`

        """
        current_heads = self.get_heads()
        if len(current_heads) > 1:
            raise util.CommandError(
                'The script directory has multiple heads (due to branching).'
                'Please use get_heads(), or merge the branches using '
                'alembic merge.')

        if current_heads:
            return current_heads[0]
        else:
            return None

    def get_heads(self):
        """Return all "head" revisions as strings.

        This is normally a list of length one,
        unless branches are present.  The
        :meth:`.ScriptDirectory.get_current_head()` method
        can be used normally when a script directory
        has only one head.

        :return: a tuple of string revision numbers.

        """
        heads = []
        for script in self._revision_map.values():
            if script and script.is_head:
                heads.append(script.revision)
        return tuple(heads)

    def get_bases(self):
        """Return the "base" revision(s) as a tuple of strings.

        These are revisions that have a ``down_revision`` of None,
        or empty tuple.

        :return: a tuple of string revision numbers.

         .. versionadded:: 0.7.0

        """
        bases = []
        for script in self._revision_map.values():
            if script and script.is_base:
                # this assertion was here, not sure
                # why this would not be true
                assert script.revision in self._revision_map
                bases.append(script.revision)
        return tuple(bases)

    def get_revision(self, id_):
        """Return the :class:`.Revision` instance with the given rev id.

        """

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

    def as_revision_number(self, id_):
        """Convert a symbolic revision, i.e. 'head' or 'base', into
        an actual revision number."""

        if id_ == 'head':
            id_ = self.get_current_head()
        elif id_ == 'base':
            id_ = None
        return id_

    def iterate_revisions(self, upper, lower):
        """Iterate through script revisions, starting at the given
        upper revision identifier and ending at the lower.

        The traversal uses strictly the `down_revision`
        marker inside each migration script, so
        it is a requirement that upper >= lower,
        else you'll get nothing back.

        The iterator yields :class:`.Revision` objects.

        """
        if upper is not None and _relative_destination.match(upper):
            relative = int(upper)
            revs = list(self._iterate_revisions("head", lower))
            revs = revs[-relative:]
            if len(revs) != abs(relative):
                raise util.CommandError(
                    "Relative revision %s didn't "
                    "produce %d migrations" % (upper, abs(relative)))
            return iter(revs)
        elif lower is not None and _relative_destination.match(lower):
            relative = int(lower)
            revs = list(self._iterate_revisions(upper, "base"))
            revs = revs[0:-relative]
            if len(revs) != abs(relative):
                raise util.CommandError(
                    "Relative revision %s didn't "
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


class Revision(object):
    """Base class for revisioned objects.

    The :class:`.Revision` class is the base of the more public-facing
    :class:`.Script` object, which represents a migration script.
    The mechanics of revision management and traversal are encapsulated
    within :class:`.Revision`, while :class:`.Script` applies this logic
    to Python files in a version directory.

    """
    nextrev = frozenset()

    revision = None
    """The string revision number."""

    down_revision = None
    """The ``down_revision`` identifier(s) within the migration script."""

    def __init__(self, revision, down_revision):
        self.revision = revision
        self.down_revision = down_revision

    def add_nextrev(self, rev):
        self.nextrev = self.nextrev.union([rev])

    @property
    def is_head(self):
        """Return True if this :class:`.Revision` is a 'head' revision.

        This is determined based on whether any other :class:`.Script`
        within the :class:`.ScriptDirectory` refers to this
        :class:`.Script`.   Multiple heads can be present.

        """
        return not bool(self.nextrev)

    @property
    def is_base(self):
        """Return True if this :class:`.Revision` is a 'base' revision."""

        return self.down_revision in (None, ())

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
    def is_merge_point(self):
        """Return True if this :class:`.Script` is a merge point."""

        return len(self.down_revision) > 1

