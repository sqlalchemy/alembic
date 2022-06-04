from sqlalchemy.testing import util as sqla_testing_util

from alembic.script.revision import CycleDetected
from alembic.script.revision import DependencyCycleDetected
from alembic.script.revision import DependencyLoopDetected
from alembic.script.revision import LoopDetected
from alembic.script.revision import MultipleHeads
from alembic.script.revision import Revision
from alembic.script.revision import RevisionError
from alembic.script.revision import RevisionMap
from alembic.testing import assert_raises_message
from alembic.testing import eq_
from alembic.testing import expect_raises_message
from alembic.testing.fixtures import TestBase
from . import _large_map


class APITest(TestBase):
    def test_invalid_datatype(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c", ("b",)),
            ]
        )
        with expect_raises_message(
            RevisionError,
            "revision identifier b'12345' is not a string; "
            "ensure database driver settings are correct",
        ):
            map_.get_revisions(b"12345")

        with expect_raises_message(
            RevisionError,
            "revision identifier b'12345' is not a string; "
            "ensure database driver settings are correct",
        ):
            map_.get_revision(b"12345")

        with expect_raises_message(
            RevisionError,
            r"revision identifier \(b'12345',\) is not a string; "
            "ensure database driver settings are correct",
        ):
            map_.get_revision((b"12345",))

        map_.get_revision(("a",))
        map_.get_revision("a")

    def test_add_revision_one_head(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c", ("b",)),
            ]
        )
        eq_(map_.heads, ("c",))

        map_.add_revision(Revision("d", ("c",)))
        eq_(map_.heads, ("d",))

    def test_add_revision_two_head(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c1", ("b",)),
                Revision("c2", ("b",)),
            ]
        )
        eq_(map_.heads, ("c1", "c2"))

        map_.add_revision(Revision("d1", ("c1",)))
        eq_(map_.heads, ("c2", "d1"))

    def test_get_revision_head_single(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c", ("b",)),
            ]
        )
        eq_(map_.get_revision("head"), map_._revision_map["c"])

    def test_get_revision_base_single(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c", ("b",)),
            ]
        )
        eq_(map_.get_revision("base"), None)

    def test_get_revision_head_multiple(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c1", ("b",)),
                Revision("c2", ("b",)),
            ]
        )
        assert_raises_message(
            MultipleHeads,
            "Multiple heads are present",
            map_.get_revision,
            "head",
        )

    def test_get_revision_heads_multiple(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c1", ("b",)),
                Revision("c2", ("b",)),
            ]
        )
        assert_raises_message(
            MultipleHeads,
            "Multiple heads are present",
            map_.get_revision,
            "heads",
        )

    def test_get_revisions_head_multiple(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c1", ("b",)),
                Revision("c2", ("b",)),
            ]
        )
        assert_raises_message(
            MultipleHeads,
            "Multiple heads are present",
            map_.get_revisions,
            "head",
        )

    def test_get_revisions_heads_multiple(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c1", ("b",)),
                Revision("c2", ("b",)),
            ]
        )
        eq_(
            map_.get_revisions("heads"),
            (
                map_._revision_map["c1"],
                map_._revision_map["c2"],
            ),
        )

    def test_get_revision_base_multiple(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c", ()),
                Revision("d", ("c",)),
            ]
        )
        eq_(map_.get_revision("base"), None)

    def test_iterate_tolerates_dupe_targets(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c", ("b",)),
            ]
        )

        eq_(
            [
                r.revision
                for r in map_.iterate_revisions(
                    ("c", "c"), "a", inclusive=False
                )
            ],
            # Not inclusive so should not traverse a
            ["c", "b"],
        )

    def test_repr_revs(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c", (), dependencies=("a", "b")),
            ]
        )
        c = map_._revision_map["c"]
        eq_(repr(c), "Revision('c', None, dependencies=('a', 'b'))")


class DownIterateTest(TestBase):
    def _assert_iteration(
        self,
        upper,
        lower,
        assertion,
        inclusive=True,
        map_=None,
        implicit_base=False,
        select_for_downgrade=False,
    ):
        if map_ is None:
            map_ = self.map

        result = [
            rev.revision
            for rev in map_.iterate_revisions(
                upper,
                lower,
                inclusive=inclusive,
                implicit_base=implicit_base,
                select_for_downgrade=select_for_downgrade,
            )
        ]

        edges = [
            (rev, child.revision)
            for child in map_._revision_map.values()
            if child is not None
            for rev in child._normalized_down_revisions
        ]

        assert sqla_testing_util.conforms_partial_ordering(
            edges, list(reversed(result))
        )

        eq_(result, assertion)


class DiamondTest(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b1", ("a",)),
                Revision("b2", ("a",)),
                Revision("c", ("b1", "b2")),
                Revision("d", ("c",)),
            ]
        )

    def test_iterate_simple_diamond(self):
        self._assert_iteration("d", "a", ["d", "c", "b1", "b2", "a"])


class EmptyMapTest(DownIterateTest):
    # see issue #258

    def setUp(self):
        self.map = RevisionMap(lambda: [])

    def test_iterate(self):
        self._assert_iteration("head", "base", [])


class LabeledBranchTest(DownIterateTest):
    def test_dupe_branch_collection(self):
        def fn():
            return [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c", ("b",), branch_labels=["xy1"]),
                Revision("d", ()),
                Revision("e", ("d",), branch_labels=["xy1"]),
                Revision("f", ("e",)),
            ]

        assert_raises_message(
            RevisionError,
            r"Branch name 'xy1' in revision (?:e|c) already "
            "used by revision (?:e|c)",
            getattr,
            RevisionMap(fn),
            "_revision_map",
        )

    def test_filter_for_lineage_labeled_head_across_merge(self):
        def fn():
            return [
                Revision("a", ()),
                Revision("b", ("a",)),
                Revision("c1", ("b",), branch_labels="c1branch"),
                Revision("c2", ("b",)),
                Revision("d", ("c1", "c2")),
            ]

        map_ = RevisionMap(fn)
        c1 = map_.get_revision("c1")
        c2 = map_.get_revision("c2")
        d = map_.get_revision("d")
        eq_(map_.filter_for_lineage([c1, c2, d], "c1branch@head"), (c1, c2, d))

    def test_filter_for_lineage_heads(self):
        eq_(
            self.map.filter_for_lineage([self.map.get_revision("f")], "heads"),
            (self.map.get_revision("f"),),
        )

    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision("a", (), branch_labels="abranch"),
                Revision("b", ("a",)),
                Revision("somelongername", ("b",)),
                Revision("c", ("somelongername",)),
                Revision("d", ()),
                Revision("e", ("d",), branch_labels=["ebranch"]),
                Revision("someothername", ("e",)),
                Revision("f", ("someothername",)),
            ]
        )

    def test_get_base_revisions_labeled(self):
        eq_(self.map._get_base_revisions("somelongername@base"), ("a",))

    def test_get_current_named_rev(self):
        eq_(self.map.get_revision("ebranch@head"), self.map.get_revision("f"))

    def test_get_base_revisions(self):
        eq_(self.map._get_base_revisions("base"), ("a", "d"))

    def test_iterate_head_to_named_base(self):
        self._assert_iteration(
            "heads", "ebranch@base", ["f", "someothername", "e", "d"]
        )

        self._assert_iteration(
            "heads", "abranch@base", ["c", "somelongername", "b", "a"]
        )

    def test_iterate_named_head_to_base(self):
        self._assert_iteration(
            "ebranch@head", "base", ["f", "someothername", "e", "d"]
        )

        self._assert_iteration(
            "abranch@head", "base", ["c", "somelongername", "b", "a"]
        )

    def test_iterate_named_head_to_heads(self):
        self._assert_iteration("heads", "ebranch@head", ["f"], inclusive=True)

    def test_iterate_named_rev_to_heads(self):
        self._assert_iteration(
            "heads",
            "ebranch@d",
            ["f", "someothername", "e", "d"],
            inclusive=True,
        )

    def test_iterate_head_to_version_specific_base(self):
        self._assert_iteration(
            "heads", "e@base", ["f", "someothername", "e", "d"]
        )

        self._assert_iteration(
            "heads", "c@base", ["c", "somelongername", "b", "a"]
        )

    def test_iterate_to_branch_at_rev(self):
        self._assert_iteration(
            "heads", "ebranch@d", ["f", "someothername", "e", "d"]
        )

    def test_branch_w_down_relative(self):
        self._assert_iteration(
            "heads", "ebranch@-2", ["f", "someothername", "e"]
        )

    def test_branch_w_up_relative(self):
        # In the absence of a branch point surely the +2 is relative to base?
        # So 'someothername' would be referenced by ebranch@+3?
        self._assert_iteration("ebranch@+2", "base", ["e", "d"])

    def test_partial_id_resolve(self):
        eq_(self.map.get_revision("ebranch@some").revision, "someothername")
        eq_(self.map.get_revision("abranch@some").revision, "somelongername")

    def test_partial_id_resolve_too_short(self):
        assert_raises_message(
            RevisionError,
            "No such revision or branch 'sos'; please ensure at least "
            "four characters are present for partial revision identifier "
            "matches",
            self.map.get_revision,
            "ebranch@sos",
        )

    def test_branch_at_heads(self):
        eq_(self.map.get_revision("abranch@heads").revision, "c")

    def test_branch_at_syntax(self):
        eq_(self.map.get_revision("abranch@head").revision, "c")
        eq_(self.map.get_revision("abranch@base"), None)
        eq_(self.map.get_revision("ebranch@head").revision, "f")
        eq_(self.map.get_revision("abranch@base"), None)
        eq_(self.map.get_revision("ebranch@d").revision, "d")

    def test_branch_at_self(self):
        eq_(self.map.get_revision("ebranch@ebranch").revision, "e")

    def test_retrieve_branch_revision(self):
        eq_(self.map.get_revision("abranch").revision, "a")
        eq_(self.map.get_revision("ebranch").revision, "e")

    def test_rev_not_in_branch(self):
        assert_raises_message(
            RevisionError,
            "Revision b is not a member of branch 'ebranch'",
            self.map.get_revision,
            "ebranch@b",
        )

        assert_raises_message(
            RevisionError,
            "Revision d is not a member of branch 'abranch'",
            self.map.get_revision,
            "abranch@d",
        )

    def test_actually_short_rev_name(self):
        eq_(self.map.get_revision("e").revision, "e")

    def test_no_revision_exists(self):
        assert_raises_message(
            RevisionError,
            "No such revision or branch 'qprstuv'$",
            self.map.get_revision,
            "abranch@qprstuv",
        )

        assert_raises_message(
            RevisionError,
            "No such revision or branch 'qpr'; please ensure at least "
            "four characters are present for partial revision identifier "
            "matches$",
            self.map.get_revision,
            "abranch@qpr",
        )

    def test_not_actually_a_branch(self):
        eq_(self.map.get_revision("e@d").revision, "d")

    def test_not_actually_a_branch_partial_resolution(self):
        eq_(self.map.get_revision("someoth@d").revision, "d")

    def test_no_such_branch(self):
        assert_raises_message(
            RevisionError, "No such branch: 'x'", self.map.get_revision, "x@d"
        )


class LongShortBranchTest(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b1", ("a",)),
                Revision("b2", ("a",)),
                Revision("c1", ("b1",)),
                Revision("d11", ("c1",)),
                Revision("d12", ("c1",)),
            ]
        )

    def test_iterate_full(self):
        self._assert_iteration(
            "heads", "base", ["b2", "d11", "d12", "c1", "b1", "a"]
        )


class MultipleBranchTest(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b1", ("a",)),
                Revision("b2", ("a",)),
                Revision("cb1", ("b1",)),
                Revision("cb2", ("b2",)),
                Revision("d1cb1", ("cb1",)),  # head
                Revision("d2cb1", ("cb1",)),  # head
                Revision("d1cb2", ("cb2",)),
                Revision("d2cb2", ("cb2",)),
                Revision("d3cb2", ("cb2",)),  # head
                Revision("d1d2cb2", ("d1cb2", "d2cb2")),  # head + merge point
            ]
        )

    def test_iterate_from_merge_point(self):
        self._assert_iteration(
            "d1d2cb2", "a", ["d1d2cb2", "d1cb2", "d2cb2", "cb2", "b2", "a"]
        )

    def test_iterate_multiple_heads(self):
        self._assert_iteration(
            ["d2cb2", "d3cb2"], "a", ["d2cb2", "d3cb2", "cb2", "b2", "a"]
        )

    def test_iterate_single_branch(self):
        self._assert_iteration("d3cb2", "a", ["d3cb2", "cb2", "b2", "a"])

    def test_iterate_single_branch_to_base(self):
        self._assert_iteration("d3cb2", "base", ["d3cb2", "cb2", "b2", "a"])

    def test_iterate_multiple_branch_to_base(self):
        self._assert_iteration(
            ["d3cb2", "cb1"], "base", ["cb1", "b1", "d3cb2", "cb2", "b2", "a"]
        )

    def test_iterate_multiple_heads_single_base(self):
        # head d1cb1 is omitted as it is not
        # a descendant of b2
        self._assert_iteration(
            ["d1cb1", "d2cb2", "d3cb2"], "b2", ["d2cb2", "d3cb2", "cb2", "b2"]
        )

    def test_same_branch_wrong_direction(self):
        # nodes b1 and d1cb1 are connected, but
        # db1cb1 is the descendant of b1
        assert_raises_message(
            RevisionError,
            r"Revision d1cb1 is not an ancestor of revision b1",
            list,
            self.map.iterate_revisions("b1", "d1cb1"),
        )

    def test_distinct_branches(self):
        # nodes db2cb2 and b1 have no path to each other
        assert_raises_message(
            RevisionError,
            r"Revision b1 is not an ancestor of revision d2cb2",
            list,
            self.map.iterate_revisions("d2cb2", "b1"),
        )

    def test_wrong_direction_to_base_as_none(self):
        # this needs to raise and not just return empty iteration
        # as added by #258
        assert_raises_message(
            RevisionError,
            r"Revision d1cb1 is not an ancestor of revision base",
            list,
            self.map.iterate_revisions(None, "d1cb1"),
        )

    def test_wrong_direction_to_base_as_empty(self):
        # this needs to raise and not just return empty iteration
        # as added by #258
        assert_raises_message(
            RevisionError,
            r"Revision d1cb1 is not an ancestor of revision base",
            list,
            self.map.iterate_revisions((), "d1cb1"),
        )


class MultipleBranchEffectiveHead(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision("y1", None, branch_labels="y"),
                Revision("x1", None, branch_labels="x"),
                Revision("y2", "y1", dependencies="x1"),
                Revision("x2", "x1"),
            ]
        )

    def test_other_downgrade(self):
        self._assert_iteration(
            ("x2", "y2"),
            "x@-1",
            ["x2"],
            inclusive=False,
            select_for_downgrade=True,
        )

    def test_use_all_current(self):
        self._assert_iteration(
            ("x1", "y2"),
            "x@-1",
            ["y2", "x1"],
            inclusive=False,
            select_for_downgrade=True,
        )

    def test_effective_head(self):
        self._assert_iteration(
            "y2",
            "x@-1",
            ["y2", "x1"],
            inclusive=False,
            select_for_downgrade=True,
        )


class BranchTravellingTest(DownIterateTest):
    """test the order of revs when going along multiple branches.

    We want depth-first along branches, but then we want to
    terminate all branches at their branch point before continuing
    to the nodes preceding that branch.

    """

    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision("a1", ()),
                Revision("a2", ("a1",)),
                Revision("a3", ("a2",)),
                Revision("b1", ("a3",)),
                Revision("b2", ("a3",)),
                Revision("cb1", ("b1",)),
                Revision("cb2", ("b2",)),
                Revision("db1", ("cb1",)),
                Revision("db2", ("cb2",)),
                Revision("e1b1", ("db1",)),
                Revision("fe1b1", ("e1b1",)),
                Revision("e2b1", ("db1",)),
                Revision("e2b2", ("db2",)),
                Revision("merge", ("e2b1", "e2b2")),
            ]
        )

    def test_iterate_one_branch_both_to_merge(self):
        # test that when we hit a merge point, implicit base will
        # ensure all branches that supply the merge point are filled in
        self._assert_iteration(
            "merge",
            "db1",
            ["merge", "e2b1", "db1", "e2b2", "db2", "cb2", "b2"],
            implicit_base=True,
        )

    def test_three_branches_end_in_single_branch(self):

        self._assert_iteration(
            ["merge", "fe1b1"],
            "a3",
            [
                "fe1b1",
                "e1b1",
                "merge",
                "e2b1",
                "db1",
                "cb1",
                "b1",
                "e2b2",
                "db2",
                "cb2",
                "b2",
                "a3",
            ],
        )

    def test_two_branches_to_root(self):

        # here we want 'a3' as a "stop" branch point, but *not*
        # 'db1', as we don't have multiple traversals on db1
        self._assert_iteration(
            "merge",
            "a1",
            [
                "merge",
                "e2b1",
                "db1",
                "cb1",
                "b1",  # e2b1 branch
                "e2b2",
                "db2",
                "cb2",
                "b2",  # e2b2 branch
                "a3",  # both terminate at a3
                "a2",
                "a1",  # finish out
            ],  # noqa
        )

    def test_two_branches_end_in_branch(self):
        self._assert_iteration(
            "merge",
            "b1",
            # 'b1' is local to 'e2b1'
            # branch so that is all we get
            ["merge", "e2b1", "db1", "cb1", "b1"],  # noqa
        )

    def test_two_branches_end_behind_branch(self):
        self._assert_iteration(
            "merge",
            "a2",
            [
                "merge",
                "e2b1",
                "db1",
                "cb1",
                "b1",  # e2b1 branch
                "e2b2",
                "db2",
                "cb2",
                "b2",  # e2b2 branch
                "a3",  # both terminate at a3
                "a2",
            ],  # noqa
        )

    def test_three_branches_to_root(self):

        # in this case, both "a3" and "db1" are stop points
        self._assert_iteration(
            ["merge", "fe1b1"],
            "a1",
            [
                "fe1b1",
                "e1b1",  # fe1b1 branch
                "merge",
                "e2b1",  # e2b1 branch
                "db1",  # fe1b1 and e2b1 branches terminate at db1
                "cb1",
                "b1",  # e2b1 branch continued....might be nicer
                # if this was before the e2b2 branch...
                "e2b2",
                "db2",
                "cb2",
                "b2",  # e2b2 branch
                "a3",  # e2b1 and e2b2 branches terminate at a3
                "a2",
                "a1",  # finish out
            ],  # noqa
        )

    def test_three_branches_end_multiple_bases(self):

        # in this case, both "a3" and "db1" are stop points
        self._assert_iteration(
            ["merge", "fe1b1"],
            ["cb1", "cb2"],
            [
                "fe1b1",
                "e1b1",
                "merge",
                "e2b1",
                "db1",
                "cb1",
                "e2b2",
                "db2",
                "cb2",
            ],
        )

    def test_three_branches_end_multiple_bases_exclusive(self):

        self._assert_iteration(
            ["merge", "fe1b1"],
            ["cb1", "cb2"],
            ["fe1b1", "e1b1", "merge", "e2b1", "db1", "e2b2", "db2"],
            inclusive=False,
        )

    def test_detect_invalid_head_selection(self):
        # db1 is an ancestor of fe1b1
        assert_raises_message(
            RevisionError,
            "Requested revision fe1b1 overlaps "
            "with other requested revisions",
            list,
            self.map.iterate_revisions(["db1", "b2", "fe1b1"], ()),
        )

    def test_three_branches_end_multiple_bases_exclusive_blank(self):
        self._assert_iteration(
            ["e2b1", "b2", "fe1b1"],
            (),
            [
                "b2",
                "fe1b1",
                "e1b1",
                "e2b1",
                "db1",
                "cb1",
                "b1",
                "a3",
                "a2",
                "a1",
            ],
            inclusive=False,
        )

    def test_iterate_to_symbolic_base(self):
        self._assert_iteration(
            ["fe1b1"],
            "base",
            ["fe1b1", "e1b1", "db1", "cb1", "b1", "a3", "a2", "a1"],
            inclusive=False,
        )

    def test_ancestor_nodes(self):
        merge = self.map.get_revision("merge")
        eq_(
            {
                rev.revision
                for rev in self.map._get_ancestor_nodes([merge], check=True)
            },
            {
                "a1",
                "e2b2",
                "e2b1",
                "cb2",
                "merge",
                "a3",
                "a2",
                "b1",
                "b2",
                "db1",
                "db2",
                "cb1",
            },
        )


class MultipleBaseTest(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision("base1", ()),
                Revision("base2", ()),
                Revision("base3", ()),
                Revision("a1a", ("base1",)),
                Revision("a1b", ("base1",)),
                Revision("a2", ("base2",)),
                Revision("a3", ("base3",)),
                Revision("b1a", ("a1a",)),
                Revision("b1b", ("a1b",)),
                Revision("b2", ("a2",)),
                Revision("b3", ("a3",)),
                Revision("c2", ("b2",)),
                Revision("d2", ("c2",)),
                Revision("mergeb3d2", ("b3", "d2")),
            ]
        )

    def test_heads_to_base(self):
        self._assert_iteration(
            "heads",
            "base",
            [
                "b1a",
                "a1a",
                "b1b",
                "a1b",
                "base1",
                "mergeb3d2",
                "b3",
                "a3",
                "base3",
                "d2",
                "c2",
                "b2",
                "a2",
                "base2",
            ],
        )

    def test_heads_to_base_exclusive(self):
        self._assert_iteration(
            "heads",
            "base",
            [
                "b1a",
                "a1a",
                "b1b",
                "a1b",
                "base1",
                "mergeb3d2",
                "b3",
                "a3",
                "base3",
                "d2",
                "c2",
                "b2",
                "a2",
                "base2",
            ],
            inclusive=False,
        )

    def test_heads_to_blank(self):
        self._assert_iteration(
            "heads",
            None,
            [
                "b1a",
                "a1a",
                "b1b",
                "a1b",
                "base1",
                "mergeb3d2",
                "b3",
                "a3",
                "base3",
                "d2",
                "c2",
                "b2",
                "a2",
                "base2",
            ],
        )

    def test_detect_invalid_base_selection(self):
        assert_raises_message(
            RevisionError,
            "overlaps with other requested revisions",
            list,
            self.map.iterate_revisions(["c2"], ["a2", "b2"]),
        )

    def test_heads_to_revs_plus_implicit_base_exclusive(self):
        self._assert_iteration(
            "heads",
            ["c2"],
            [
                "b1a",
                "a1a",
                "b1b",
                "a1b",
                "base1",
                "mergeb3d2",
                "b3",
                "a3",
                "base3",
                "d2",
            ],
            inclusive=False,
            implicit_base=True,
        )

    def test_heads_to_revs_base_exclusive(self):
        self._assert_iteration(
            "heads", ["c2"], ["mergeb3d2", "d2"], inclusive=False
        )

    def test_heads_to_revs_plus_implicit_base_inclusive(self):
        self._assert_iteration(
            "heads",
            ["c2"],
            [
                "b1a",
                "a1a",
                "b1b",
                "a1b",
                "base1",
                "mergeb3d2",
                "b3",
                "a3",
                "base3",
                "d2",
                "c2",
            ],
            implicit_base=True,
        )

    def test_specific_path_one(self):
        self._assert_iteration("b3", "base3", ["b3", "a3", "base3"])

    def test_specific_path_two_implicit_base(self):
        self._assert_iteration(
            ["b3", "b2"],
            "base3",
            ["b2", "a2", "base2", "b3", "a3"],
            inclusive=False,
            implicit_base=True,
        )


class MultipleBaseCrossDependencyTestOne(DownIterateTest):
    def setUp(self):
        """
        Structure::

            base1 -----> a1a  -> b1a
                  +----> a1b  -> b1b
                                  |
                      +-----------+
                      |
                      v
            base3 -> a3 -> b3
                      ^
                      |
                      +-----------+
                                  |
            base2 -> a2 -> b2 -> c2 -> d2

        """
        self.map = RevisionMap(
            lambda: [
                Revision("base1", (), branch_labels="b_1"),
                Revision("a1a", ("base1",)),
                Revision("a1b", ("base1",)),
                Revision("b1a", ("a1a",)),
                Revision("b1b", ("a1b",), dependencies="a3"),
                Revision("base2", (), branch_labels="b_2"),
                Revision("a2", ("base2",)),
                Revision("b2", ("a2",)),
                Revision("c2", ("b2",), dependencies="a3"),
                Revision("d2", ("c2",)),
                Revision("base3", (), branch_labels="b_3"),
                Revision("a3", ("base3",)),
                Revision("b3", ("a3",)),
            ]
        )

    def test_what_are_the_heads(self):
        eq_(self.map.heads, ("b1a", "b1b", "d2", "b3"))

    def test_heads_to_base(self):
        self._assert_iteration(
            "heads",
            "base",
            [
                "b1a",
                "a1a",
                "b1b",
                "a1b",
                "base1",
                "d2",
                "c2",
                "b2",
                "a2",
                "base2",
                "b3",
                "a3",
                "base3",
            ],
        )

    def test_heads_to_base_downgrade(self):
        self._assert_iteration(
            "heads",
            "base",
            [
                "b1a",
                "a1a",
                "b1b",
                "a1b",
                "base1",
                "d2",
                "c2",
                "b2",
                "a2",
                "base2",
                "b3",
                "a3",
                "base3",
            ],
            select_for_downgrade=True,
        )

    def test_same_branch_wrong_direction(self):
        assert_raises_message(
            RevisionError,
            r"Revision d2 is not an ancestor of revision b2",
            list,
            self.map.iterate_revisions("b2", "d2"),
        )

    def test_different_branch_not_wrong_direction(self):
        # Changed from empty list. Expect this should raise an error in
        # --sql mode (since there is not a direct path), or in upgrade mode
        # it should return revision b3, not an empty list.
        assert_raises_message(
            RevisionError,
            r"Revision d2 is not an ancestor of revision b3",
            list,
            self.map.iterate_revisions("b3", "d2"),
        )

    def test_we_need_head2_upgrade(self):
        # the 2 branch relies on the 3 branch
        self._assert_iteration(
            "b_2@head",
            "base",
            ["d2", "c2", "b2", "a2", "base2", "a3", "base3"],
        )

    def test_we_need_head2_downgrade(self):
        # the 2 branch relies on the 3 branch, but
        # on the downgrade side, don't need to touch the 3 branch
        self._assert_iteration(
            "b_2@head",
            "b_2@base",
            ["d2", "c2", "b2", "a2", "base2"],
            select_for_downgrade=True,
        )

    def test_we_need_head3_upgrade(self):
        # the 3 branch can be upgraded alone.
        self._assert_iteration("b_3@head", "base", ["b3", "a3", "base3"])

    def test_we_need_head3_downgrade(self):
        # the 3 branch can be upgraded alone.
        self._assert_iteration(
            "b_3@head",
            "base",
            ["b3", "a3", "base3"],
            select_for_downgrade=True,
        )

    def test_we_need_head1_upgrade(self):
        # the 1 branch relies on the 3 branch
        self._assert_iteration(
            "b1b@head", "base", ["b1b", "a1b", "base1", "a3", "base3"]
        )

    def test_we_need_head1_downgrade(self):
        # going down we don't need a3-> base3, as long
        # as we are limiting the base target
        self._assert_iteration(
            "b1b@head",
            "b1b@base",
            ["b1b", "a1b", "base1"],
            select_for_downgrade=True,
        )

    def test_we_need_base2_upgrade(self):
        # This is an upgrade from base, so deps should be included and
        # the result should be different to the downgrade case below
        self._assert_iteration(
            "heads",
            "b_2@base",
            ["d2", "c2", "b2", "a2", "base2", "a3", "base3"],
        )

    def test_we_need_base2_downgrade(self):
        # consider a downgrade to b_2@base - we
        # want to run through all the "2"s alone, and we're done.
        self._assert_iteration(
            "heads",
            "b_2@base",
            ["d2", "c2", "b2", "a2", "base2"],
            select_for_downgrade=True,
        )

    def test_we_need_base3_upgrade(self):
        # branch b_3 has no dependencies, so b1b/d2/c2 not needed
        self._assert_iteration("heads", "b_3@base", ["b3", "a3", "base3"])

    def test_we_need_base3_downgrade(self):
        # consider a downgrade to b_3@base - due to the a3 dependency, we
        # need to downgrade everything dependent on a3
        # as well, which means b1b and c2.  Then we can downgrade
        # the 3s.
        self._assert_iteration(
            "heads",
            "b_3@base",
            ["b1b", "d2", "c2", "b3", "a3", "base3"],
            select_for_downgrade=True,
        )


class MultipleBaseCrossDependencyTestTwo(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision("base1", (), branch_labels="b_1"),
                Revision("a1", "base1"),
                Revision("b1", "a1"),
                Revision("c1", "b1"),
                Revision("base2", (), dependencies="b_1", branch_labels="b_2"),
                Revision("a2", "base2"),
                Revision("b2", "a2"),
                Revision("c2", "b2"),
                Revision("d2", "c2"),
                Revision("base3", (), branch_labels="b_3"),
                Revision("a3", "base3"),
                Revision("b3", "a3"),
                Revision("c3", "b3", dependencies="b2"),
                Revision("d3", "c3"),
            ]
        )

    def test_what_are_the_heads(self):
        eq_(self.map.heads, ("c1", "d2", "d3"))

    def test_heads_to_base(self):
        self._assert_iteration(
            "heads",
            "base",
            [
                "c1",
                "b1",
                "a1",
                "d2",
                "c2",
                "d3",
                "c3",
                "b3",
                "a3",
                "base3",
                "b2",
                "a2",
                "base2",
                "base1",
            ],
        )

    def test_we_need_head2(self):
        self._assert_iteration(
            "b_2@head", "base", ["d2", "c2", "b2", "a2", "base2", "base1"]
        )

    def test_we_need_head3(self):
        self._assert_iteration(
            "b_3@head",
            "base",
            ["d3", "c3", "b3", "a3", "base3", "b2", "a2", "base2", "base1"],
        )

    def test_we_need_head1(self):
        self._assert_iteration("b_1@head", "base", ["c1", "b1", "a1", "base1"])

    def test_we_need_base1(self):
        # b_1 has no dependencies
        self._assert_iteration(
            "heads",
            "b_1@base",
            [
                "c1",
                "b1",
                "a1",
                "base1",
            ],
        )

    def test_we_need_base2(self):
        # base2 depends on base1, nobody depends on b_3 so removed d3,c3
        self._assert_iteration(
            "heads", "b_2@base", ["d2", "c2", "b2", "a2", "base2", "base1"]
        )

    def test_we_need_base3(self):
        # c3 depends on b2 -> add b2,a2,base2, base2 depends on base1
        self._assert_iteration(
            "heads",
            "b_3@base",
            ["d3", "c3", "b3", "a3", "base3", "b2", "a2", "base2", "base1"],
        )


class MultipleBaseCrossDependencyTestThree(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision("base1", ()),
                Revision("a1", "base1"),
                Revision("b1", "a1"),
                Revision("c2", (), dependencies="a1"),
                Revision("c3", "c2"),
            ]
        )

    def test_traverse_no_parent_but_a_dep(self):
        self._assert_iteration(
            "heads",
            "base",
            ["b1", "c3", "c2", "a1", "base1"],
        )


class LargeMapTest(DownIterateTest):
    def setUp(self):
        self.map = _large_map.map_

    def test_all(self):
        raw = [r for r in self.map._revision_map.values() if r is not None]

        revs = [rev for rev in self.map.iterate_revisions("heads", "base")]

        eq_(set(raw), set(revs))

        for idx, rev in enumerate(revs):
            ancestors = set(self.map._get_ancestor_nodes([rev])).difference(
                [rev]
            )
            descendants = set(
                self.map._get_descendant_nodes([rev])
            ).difference([rev])

            assert not ancestors.intersection(descendants)

            remaining = set(revs[idx + 1 :])
            if remaining:
                assert remaining.intersection(ancestors)


class DepResolutionFailedTest(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision("base1", ()),
                Revision("a1", "base1"),
                Revision("a2", "base1"),
                Revision("b1", "a1"),
                Revision("c1", "b1"),
            ]
        )
        # intentionally make a broken map
        self.map._revision_map["fake"] = self.map._revision_map["a2"]
        self.map._revision_map["b1"].dependencies = "fake"
        self.map._revision_map["b1"]._resolved_dependencies = ("fake",)
        self.map._revision_map["b1"]._normalized_resolved_dependencies = (
            "fake",
        )

    def test_failure_message(self):
        iter_ = self.map.iterate_revisions("c1", "base1")
        assert_raises_message(
            RevisionError, "Dependency resolution failed;", list, iter_
        )


class InvalidRevisionMapTest(TestBase):
    def _assert_raises_revision_map(self, map_, except_cls, msg):
        assert_raises_message(except_cls, msg, lambda: map_._revision_map)

    def _assert_raises_revision_map_loop(self, map_, revision):
        self._assert_raises_revision_map(
            map_,
            LoopDetected,
            r"^Self-loop is detected in revisions \(%s\)$" % revision,
        )

    def _assert_raises_revision_map_dep_loop(self, map_, revision):
        self._assert_raises_revision_map(
            map_,
            DependencyLoopDetected,
            r"^Dependency self-loop is detected in revisions \(%s\)$"
            % revision,
        )

    def _assert_raises_revision_map_cycle(self, map_, revisions):
        self._assert_raises_revision_map(
            map_,
            CycleDetected,
            r"^Cycle is detected in revisions \(\(%s\)\(, \)?\)+$"
            % "|".join(revisions),
        )

    def _assert_raises_revision_map_dep_cycle(self, map_, revisions):
        self._assert_raises_revision_map(
            map_,
            DependencyCycleDetected,
            r"^Dependency cycle is detected in revisions \(\(%s\)\(, \)?\)+$"
            % "|".join(revisions),
        )


class GraphWithLoopTest(DownIterateTest, InvalidRevisionMapTest):
    def test_revision_map_solitary_loop(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", "a"),
            ]
        )
        self._assert_raises_revision_map_loop(map_, "a")

    def test_revision_dupe_head(self):
        r1 = Revision("user_foo", None)
        r2 = Revision("user", "user_foo", dependencies="user_foo")

        self.map = RevisionMap(lambda: [r1, r2])

        self._assert_iteration("heads", None, ["user", "user_foo"])

        eq_(self.map._topological_sort([r1, r2], [r2]), ["user", "user_foo"])

    def test_revision_map_no_loop_w_overlapping_substrings(self):
        r1 = Revision("user_foo", None)
        r2 = Revision("user", "user_foo")

        self.map = RevisionMap(lambda: [r1, r2])

        self._assert_iteration("heads", None, ["user", "user_foo"])

    def test_revision_map_no_loop_w_overlapping_substrings_dependencies(self):
        r1 = Revision("user_foo", None)
        r2 = Revision("user", None, dependencies="user_foo")

        self.map = RevisionMap(lambda: [r1, r2])

        self._assert_iteration("heads", None, ["user", "user_foo"])

    def test_revision_map_base_loop(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", "a"),
                Revision("b", "a"),
                Revision("c", "b"),
            ]
        )
        self._assert_raises_revision_map_loop(map_, "a")

    def test_revision_map_head_loop(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", "a"),
                Revision("c", ("b", "c")),
            ]
        )
        self._assert_raises_revision_map_loop(map_, "c")

    def test_revision_map_branch_point_loop(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", ("a", "b")),
                Revision("c1", "b"),
                Revision("c2", "b"),
            ]
        )
        self._assert_raises_revision_map_loop(map_, "b")

    def test_revision_map_merge_point_loop(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b1", "a"),
                Revision("b2", "a"),
                Revision("c", ("b1", "b2", "c")),
            ]
        )
        self._assert_raises_revision_map_loop(map_, "c")

    def test_revision_map_solitary_dependency_loop(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", (), dependencies="a"),
            ]
        )
        self._assert_raises_revision_map_dep_loop(map_, "a")

    def test_revision_map_base_dependency_loop(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", (), dependencies="a"),
                Revision("b", "a"),
                Revision("c", "b"),
            ]
        )
        self._assert_raises_revision_map_dep_loop(map_, "a")

    def test_revision_map_head_dep_loop(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", "a"),
                Revision("c", "b", dependencies="c"),
            ]
        )
        self._assert_raises_revision_map_dep_loop(map_, "c")

    def test_revision_map_branch_point_dep_loop(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", "a", dependencies="b"),
                Revision("c1", "b"),
                Revision("c2", "b"),
            ]
        )
        self._assert_raises_revision_map_dep_loop(map_, "b")

    def test_revision_map_merge_point_dep_loop(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b1", "a"),
                Revision("b2", "a"),
                Revision("c", ("b1", "b2"), dependencies="c"),
            ]
        )
        self._assert_raises_revision_map_dep_loop(map_, "c")


class GraphWithCycleTest(InvalidRevisionMapTest):
    def test_revision_map_simple_cycle(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", "c"),
                Revision("b", "a"),
                Revision("c", "b"),
            ]
        )
        self._assert_raises_revision_map_cycle(map_, ["a", "b", "c"])

    def test_revision_map_extra_simple_cycle(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", "c"),
                Revision("b", "a"),
                Revision("c", "b"),
                Revision("d", ()),
                Revision("e", "d"),
            ]
        )
        self._assert_raises_revision_map_cycle(map_, ["a", "b", "c"])

    def test_revision_map_lower_simple_cycle(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", "c"),
                Revision("b", "a"),
                Revision("c", "b"),
                Revision("d", "c"),
                Revision("e", "d"),
            ]
        )
        self._assert_raises_revision_map_cycle(map_, ["a", "b", "c", "d", "e"])

    def test_revision_map_upper_simple_cycle(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", "a"),
                Revision("c", ("b", "e")),
                Revision("d", "c"),
                Revision("e", "d"),
            ]
        )
        self._assert_raises_revision_map_cycle(map_, ["a", "b", "c", "d", "e"])

    def test_revision_map_simple_dep_cycle(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", (), dependencies="c"),
                Revision("b", "a"),
                Revision("c", "b"),
            ]
        )
        self._assert_raises_revision_map_dep_cycle(map_, ["a", "b", "c"])

    def test_revision_map_extra_simple_dep_cycle(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", (), dependencies="c"),
                Revision("b", "a"),
                Revision("c", "b"),
                Revision("d", ()),
                Revision("e", "d"),
            ]
        )
        self._assert_raises_revision_map_dep_cycle(map_, ["a", "b", "c"])

    def test_revision_map_lower_simple_dep_cycle(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", (), dependencies="c"),
                Revision("b", "a"),
                Revision("c", "b"),
                Revision("d", "c"),
                Revision("e", "d"),
            ]
        )
        self._assert_raises_revision_map_dep_cycle(
            map_, ["a", "b", "c", "d", "e"]
        )

    def test_revision_map_upper_simple_dep_cycle(self):
        map_ = RevisionMap(
            lambda: [
                Revision("a", ()),
                Revision("b", "a"),
                Revision("c", "b", dependencies="e"),
                Revision("d", "c"),
                Revision("e", "d"),
            ]
        )
        self._assert_raises_revision_map_dep_cycle(
            map_, ["a", "b", "c", "d", "e"]
        )


class NormalizedDownRevTest(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision("a1", ()),
                Revision("a2", "a1"),
                Revision("a3", "a2"),
                Revision("b1", ()),
                Revision("b2", "b1", dependencies="a3"),
                Revision("b3", "b2"),
                Revision("b4", "b3", dependencies="a3"),
                Revision("b5", "b4", dependencies="b4"),
            ]
        )

    def test_normalized_down_revisions(self):
        b4 = self.map.get_revision("b4")

        eq_(b4._all_down_revisions, ("b3", "a3"))

        # "a3" is not included because ancestor b2 is also dependent
        eq_(b4._normalized_down_revisions, ("b3",))

    def test_dupe_dependency(self):
        b5 = self.map.get_revision("b5")
        eq_(b5._all_down_revisions, ("b4",))
        eq_(b5._normalized_down_revisions, ("b4",))

    def test_branch_traversal(self):
        self._assert_iteration(
            "b4",
            "b1@base",
            ["b4", "b3", "b2", "b1"],
            select_for_downgrade=True,
        )

    def test_all_traversal(self):
        self._assert_iteration(
            "heads",
            "base",
            ["b5", "b4", "b3", "b2", "b1", "a3", "a2", "a1"],
            select_for_downgrade=True,
        )

    def test_partial_traversal(self):
        self._assert_iteration(
            "heads",
            "a2",
            ["b5", "b4", "b3", "b2", "a3", "a2"],
            select_for_downgrade=True,
        )

    def test_partial_traversal_implicit_base_one(self):
        self._assert_iteration(
            "heads",
            "a2",
            ["b5", "b4", "b3", "b2", "b1", "a3", "a2"],
            select_for_downgrade=True,
            implicit_base=True,
        )

    def test_partial_traversal_implicit_base_two(self):
        self._assert_iteration(
            "b5",
            ("b1",),
            ["b5", "b4", "b3", "b2", "b1", "a3", "a2", "a1"],
            implicit_base=True,
        )

    def test_partial_traversal_implicit_base_three(self):
        map_ = RevisionMap(
            lambda: [
                Revision("c1", ()),
                Revision("a1", ()),
                Revision("a2", "a1", dependencies="c1"),
                Revision("a3", "a2", dependencies="c1"),
                Revision("b1", ()),
                Revision("b2", "b1", dependencies="a3"),
                Revision("b3", "b2"),
                Revision("b4", "b3", dependencies="a3"),
                Revision("b5", "b4"),
            ]
        )
        self._assert_iteration(
            "b5",
            ("b1",),
            ["b5", "b4", "b3", "b2", "b1", "a3", "a2", "a1", "c1"],
            implicit_base=True,
            map_=map_,
        )
