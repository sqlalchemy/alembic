import re
import collections

from . import util
from sqlalchemy import util as sqlautil


_relative_destination = re.compile(r'(?:\+|-)\d+')


class MultipleRevisions(Exception):
    pass


class RevisionMap(object):
    """Maintains a map of :class:`.Revision` objects.

    :class:`.RevisionMap` is used by :class:`.ScriptDirectory` to maintain
    and traverse the collection of :class:`.Script` objects, which are
    themselves instances of :class:`.Revision`.

    """

    def __init__(self, generator):
        self._generator = generator

    @util.memoized_property
    def heads(self):
        """All "head" revisions as strings.

        This is normally a tuple of length one,
        unless unmerged branches are present.

        :return: a tuple of string revision numbers.

        """
        self._revision_map
        return self.heads

    @util.memoized_property
    def bases(self):
        """All "base" revisions as  strings.

        These are revisions that have a ``down_revision`` of None,
        or empty tuple.

        :return: a tuple of string revision numbers.

        """
        self._revision_map
        return self.bases

    @util.memoized_property
    def _revision_map(self):
        map_ = {}

        heads = sqlautil.OrderedSet()
        self.bases = ()

        for revision in self._generator():
            if revision.revision in map_:
                util.warn("Revision %s is present more than once" %
                          revision.revision)
            map_[revision.revision] = revision
            heads.add(revision.revision)
            if revision.is_base:
                self.bases += (revision.revision, )

        for rev in map_.values():
            for downrev in rev.down_revision:
                if downrev not in map_:
                    util.warn("Revision %s referenced from %s is not present"
                              % (rev.down_revision, rev))
                map_[downrev].add_nextrev(rev.revision)
                heads.discard(downrev)
        map_[None] = map_[()] = None
        self.heads = tuple(heads)
        return map_

    def add_revision(self, revision):
        map_ = self._revision_map
        if revision.revision in map_:
            util.warn("Revision %s is present more than once" %
                      revision.revision)
        map_[revision.revision] = revision
        if revision.is_base:
            self.bases += (revision.revision, )
        for downrev in revision.down_revision:
            if downrev not in map_:
                util.warn("Revision %s referenced from %s is not present"
                          % (revision.down_revision, revision))
            map_[downrev].add_nextrev(revision.revision)
        if revision.is_head:
            self.heads = tuple(
                head for head in self.heads
                if head not in set(revision.down_revision)
            ) + (revision.revision,)

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
        current_heads = self.heads
        if len(current_heads) > 1:
            raise util.CommandError(
                'The script directory has multiple heads (due to branching).'
                'Please use get_heads(), or merge the branches using '
                'alembic merge.')

        if current_heads:
            return current_heads[0]
        else:
            return None

    def get_revisions(self, id_):
        """Return the :class:`.Revision` instances with the given rev id
        or identifiers.

        May be given a single identifier, a sequence of identifiers, or the
        special symbols "head" or "base".  The result is a tuple of one
        or more identifiers.

        Supports partial identifiers, where the given identifier
        is matched against all identifiers that start with the given
        characters; if there is exactly one match, that determines the
        full revision.

        """
        resolved_id = self._resolve_revision_symbol(id_)
        return tuple(self.get_revision(rev_id) for rev_id in resolved_id)

    def get_revision(self, id_):
        """Return the :class:`.Revision` instance with the given rev id.

        If a symbolic name such as "head" or "base" is given, resolves
        the identifier into the current head or base revision.  If the symbolic
        name refers to multiples, :class:`.MultipleRevisions` is raised.

        Supports partial identifiers, where the given identifier
        is matched against all identifiers that start with the given
        characters; if there is exactly one match, that determines the
        full revision.

        """

        resolved_id = self._resolve_revision_symbol(id_)
        if len(resolved_id) > 1:
            raise MultipleRevisions(
                "Identifier %r corresponds to multiple revisions; "
                "please use get_revisions()" % id_)
        else:
            resolved_id = resolved_id[0]

        try:
            return self._revision_map[resolved_id]
        except KeyError:
            # do a partial lookup
            revs = [x for x in self._revision_map
                    if x and x.startswith(resolved_id)]
            if not revs:
                raise util.CommandError("No such revision '%s'" % id_)
            elif len(revs) > 1:
                raise util.CommandError(
                    "Multiple revisions start "
                    "with '%s': %s..." % (
                        id_,
                        ", ".join("'%s'" % r for r in revs[0:3])
                    ))
            else:
                return self._revision_map[revs[0]]

    def _resolve_revision_symbol(self, id_):
        if id_ == 'head':
            return self.heads
        elif id_ == 'base':
            return self.bases
        else:
            return util.to_tuple(id_, default=())

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
            return self._iterate_revisions(upper, lower, inclusive=False)

    def _get_descendant_nodes(self, targets):
        total_descendants = set()
        for target in targets:
            descendants = set()
            todo = collections.deque([target])
            while todo:
                rev = todo.pop()
                todo.extend(
                    self._revision_map[rev_id] for rev_id in rev.nextrev)
                descendants.add(rev)
            if descendants.intersection(
                tg for tg in targets if tg is not target
            ):
                raise util.CommandError(
                    "Requested base revision %s overlaps with "
                    "other requested base revisions" % target.revision)
            total_descendants.update(descendants)
        return total_descendants

    def _get_ancestor_nodes(self, targets):
        total_ancestors = set()
        for target in targets:
            ancestors = set()
            todo = collections.deque([target])
            while todo:
                rev = todo.pop()
                todo.extend(
                    self._revision_map[rev_id] for rev_id in rev.down_revision)
                ancestors.add(rev)
            if ancestors.intersection(
                tg for tg in targets if tg is not target
            ):
                raise util.CommandError(
                    "Requested head revision %s overlaps with "
                    "other requested head revisions" % target.revision)
            total_ancestors.update(ancestors)
        return total_ancestors

    def _iterate_revisions(self, upper, lower, inclusive=True):
        """iterate revisions from upper to lower.

        The traversal is depth-first within branches, and breadth-first
        across branches as a whole.

        """
        if not lower:  # lower of None or (), we go to the bases.
            lower = self.bases
            inclusive = True
        lowers = self.get_revisions(lower)
        uppers = self.get_revisions(upper)

        total_space = set(
            rev.revision for rev
            in self._get_ancestor_nodes(uppers)
        ).intersection(
            rev.revision for rev in self._get_descendant_nodes(lowers)
        )

        branch_endpoints = set(
            rev.revision for rev in
            (self._revision_map[rev] for rev in total_space)
            if rev.is_branch_point and
            len(total_space.intersection(rev.nextrev)) > 1
        )

        todo = collections.deque(uppers)
        stop = set(lowers)
        while todo:
            stop.update(
                rev.revision for rev in todo
                if rev.revision in branch_endpoints)
            rev = todo.popleft()

            # do depth first for elements within the branches
            todo.extendleft([
                self._revision_map[downrev]
                for downrev in reversed(rev.down_revision)
                if downrev not in branch_endpoints and downrev not in stop
                and downrev in total_space])

            # then put the actual branch points at the end of the
            # list for subsequent traversal
            todo.extend([
                self._revision_map[downrev]
                for downrev in rev.down_revision
                if downrev in branch_endpoints and downrev not in stop
                and downrev in total_space
            ])
            if inclusive or rev not in lowers:
                yield rev


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
