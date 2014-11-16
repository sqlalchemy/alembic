from alembic.testing.fixtures import TestBase
from alembic.testing import eq_, assert_raises_message
from alembic.revision import RevisionMap, Revision, MultipleHeads, \
    RevisionError


class APITest(TestBase):
    def test_add_revision_one_head(self):
        map_ = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b', ('a',)),
                Revision('c', ('b',)),
            ]
        )
        eq_(map_.heads, ('c', ))

        map_.add_revision(Revision('d', ('c', )))
        eq_(map_.heads, ('d', ))

    def test_add_revision_two_head(self):
        map_ = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b', ('a',)),
                Revision('c1', ('b',)),
                Revision('c2', ('b',)),
            ]
        )
        eq_(map_.heads, ('c1', 'c2'))

        map_.add_revision(Revision('d1', ('c1', )))
        eq_(map_.heads, ('c2', 'd1'))

    def test_get_revision_head_single(self):
        map_ = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b', ('a',)),
                Revision('c', ('b',)),
            ]
        )
        eq_(map_.get_revision('head'), map_._revision_map['c'])

    def test_get_revision_base_single(self):
        map_ = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b', ('a',)),
                Revision('c', ('b',)),
            ]
        )
        eq_(map_.get_revision('base'), None)

    def test_get_revision_head_multiple(self):
        map_ = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b', ('a',)),
                Revision('c1', ('b',)),
                Revision('c2', ('b',)),
            ]
        )
        assert_raises_message(
            MultipleHeads,
            "Multiple heads are present",
            map_.get_revision, 'head'
        )

    def test_get_revision_base_multiple(self):
        map_ = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b', ('a',)),
                Revision('c', ()),
                Revision('d', ('c',)),
            ]
        )
        eq_(map_.get_revision('base'), None)


class DownIterateTest(TestBase):
    def _assert_iteration(
            self, upper, lower, assertion, inclusive=True, map_=None,
            implicit_base=False):
        if map_ is None:
            map_ = self.map
        eq_(
            [
                rev.revision for rev in
                map_._iterate_revisions(
                    upper, lower,
                    inclusive=inclusive, implicit_base=implicit_base
                )
            ],
            assertion
        )


class DiamondTest(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b1', ('a',)),
                Revision('b2', ('a',)),
                Revision('c', ('b1', 'b2')),
                Revision('d', ('c',)),
            ]
        )

    def test_iterate_simple_diamond(self):
        self._assert_iteration(
            "d", "a",
            ["d", "c", "b1", "b2", "a"]
        )


class NamedBranchTest(DownIterateTest):
    def test_dupe_branch_collection(self):
        fn = lambda: [
            Revision('a', ()),
            Revision('b', ('a',)),
            Revision('c', ('b',), branch_names=['xy1']),
            Revision('d', ()),
            Revision('e', ('d',), branch_names=['xy1']),
            Revision('f', ('e',))
        ]
        assert_raises_message(
            RevisionError,
            "Branch name 'xy1' in revision e already used by revision c",
            getattr, RevisionMap(fn), "_revision_map"
        )

    def setUp(self):
        self.map = RevisionMap(lambda: [
            Revision('a', (), branch_names='abranch'),
            Revision('b', ('a',)),
            Revision('somelongername', ('b',)),
            Revision('c', ('somelongername',)),
            Revision('d', ()),
            Revision('e', ('d',), branch_names=['ebranch']),
            Revision('someothername', ('e',)),
            Revision('f', ('someothername',)),
        ])

    def test_iterate_head_to_named_base(self):
        self._assert_iteration(
            "heads", "ebranch@base",
            ['f', 'someothername', 'e', 'd']
        )

        self._assert_iteration(
            "heads", "abranch@base",
            ['c', 'somelongername', 'b', 'a']
        )

    def test_iterate_head_to_version_specific_base(self):
        self._assert_iteration(
            "heads", "e@base",
            ['f', 'someothername', 'e', 'd']
        )

        self._assert_iteration(
            "heads", "c@base",
            ['c', 'somelongername', 'b', 'a']
        )

    def test_partial_id_resolve(self):
        eq_(self.map.get_revision("ebranch@some").revision, "someothername")
        eq_(self.map.get_revision("abranch@some").revision, "somelongername")

    def test_branch_at_heads(self):
        assert_raises_message(
            RevisionError,
            "Branch name given with 'heads' makes no sense",
            self.map.get_revision, "abranch@heads"
        )

    def test_branch_at_syntax(self):
        eq_(self.map.get_revision("abranch@head").revision, 'c')
        eq_(self.map.get_revision("abranch@base"), None)
        eq_(self.map.get_revision("ebranch@head").revision, 'f')
        eq_(self.map.get_revision("abranch@base"), None)
        eq_(self.map.get_revision("ebranch@d").revision, 'd')

    def test_branch_at_self(self):
        eq_(self.map.get_revision("ebranch@ebranch").revision, 'e')

    def test_retrieve_branch_revision(self):
        eq_(self.map.get_revision("abranch").revision, 'a')
        eq_(self.map.get_revision("ebranch").revision, 'e')

    def test_rev_not_in_branch(self):
        assert_raises_message(
            RevisionError,
            "Revision b is not a member of branch 'ebranch'",
            self.map.get_revision, "ebranch@b"
        )

        assert_raises_message(
            RevisionError,
            "Revision d is not a member of branch 'abranch'",
            self.map.get_revision, "abranch@d"
        )

    def test_no_revision_exists(self):
        assert_raises_message(
            RevisionError,
            "No such revision or branch 'q'",
            self.map.get_revision, "abranch@q"
        )

    def test_not_actually_a_branch(self):
        eq_(self.map.get_revision("e@d").revision, "d")

    def test_not_actually_a_branch_partial_resolution(self):
        eq_(self.map.get_revision("someoth@d").revision, "d")

    def test_no_such_branch(self):
        assert_raises_message(
            RevisionError,
            "No such branch: 'x'",
            self.map.get_revision, "x@d"
        )


class MultipleBranchTest(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b1', ('a',)),
                Revision('b2', ('a',)),
                Revision('cb1', ('b1',)),
                Revision('cb2', ('b2',)),
                Revision('d1cb1', ('cb1',)),  # head
                Revision('d2cb1', ('cb1',)),  # head
                Revision('d1cb2', ('cb2',)),
                Revision('d2cb2', ('cb2',)),
                Revision('d3cb2', ('cb2',)),  # head
                Revision('d1d2cb2', ('d1cb2', 'd2cb2'))  # head + merge point
            ]
        )

    def test_iterate_from_merge_point(self):
        self._assert_iteration(
            "d1d2cb2", "a",
            ['d1d2cb2', 'd1cb2', 'd2cb2', 'cb2', 'b2', 'a']
        )

    def test_iterate_multiple_heads(self):
        self._assert_iteration(
            ["d2cb2", "d3cb2"], "a",
            ['d2cb2', 'd3cb2', 'cb2', 'b2', 'a']
        )

    def test_iterate_single_branch(self):
        self._assert_iteration(
            "d3cb2", "a",
            ['d3cb2', 'cb2', 'b2', 'a']
        )

    def test_iterate_single_branch_to_base(self):
        self._assert_iteration(
            "d3cb2", "base",
            ['d3cb2', 'cb2', 'b2', 'a']
        )

    def test_iterate_multiple_branch_to_base(self):
        self._assert_iteration(
            ["d3cb2", "cb1"], "base",
            ['d3cb2', 'cb2', 'b2', 'cb1', 'b1', 'a']
        )

    def test_iterate_multiple_heads_single_base(self):
        # head d1cb1 is omitted as it is not
        # a descendant of b2
        self._assert_iteration(
            ["d1cb1", "d2cb2", "d3cb2"], "b2",
            ["d2cb2", 'd3cb2', 'cb2', 'b2']
        )

    def test_same_branch_wrong_direction(self):
        # nodes b1 and d1cb1 are connected, but
        # db1cb1 is the descendant of b1
        assert_raises_message(
            RevisionError,
            r"Revision d1cb1 is not an ancestor of revision b1",
            list,
            self.map._iterate_revisions('b1', 'd1cb1')
        )

    def test_distinct_branches(self):
        # nodes db2cb2 and b1 have no path to each other
        assert_raises_message(
            RevisionError,
            r"Revision b1 is not an ancestor of revision d2cb2",
            list,
            self.map._iterate_revisions('d2cb2', 'b1')
        )

    def test_wrong_direction_to_base(self):
        assert_raises_message(
            RevisionError,
            r"Revision d1cb1 is not an ancestor of revision base",
            list,
            self.map._iterate_revisions(None, 'd1cb1')
        )

        assert_raises_message(
            RevisionError,
            r"Revision d1cb1 is not an ancestor of revision base",
            list,
            self.map._iterate_revisions((), 'd1cb1')
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
                Revision('a1', ()),
                Revision('a2', ('a1',)),
                Revision('a3', ('a2',)),
                Revision('b1', ('a3',)),
                Revision('b2', ('a3',)),
                Revision('cb1', ('b1',)),
                Revision('cb2', ('b2',)),
                Revision('db1', ('cb1',)),
                Revision('db2', ('cb2',)),

                Revision('e1b1', ('db1',)),
                Revision('fe1b1', ('e1b1',)),

                Revision('e2b1', ('db1',)),
                Revision('e2b2', ('db2',)),
                Revision("merge", ('e2b1', 'e2b2'))
            ]
        )

    def test_three_branches_end_in_single_branch(self):

        self._assert_iteration(
            ["merge", "fe1b1"], "a3",
            ['merge', 'e2b1', 'e2b2', 'db2', 'cb2', 'b2',
             'fe1b1', 'e1b1', 'db1', 'cb1', 'b1', 'a3']
        )

    def test_two_branches_to_root(self):

        # here we want 'a3' as a "stop" branch point, but *not*
        # 'db1', as we don't have multiple traversals on db1
        self._assert_iteration(
            "merge", "a1",
            ['merge',
                'e2b1', 'db1', 'cb1', 'b1',  # e2b1 branch
                'e2b2', 'db2', 'cb2', 'b2',  # e2b2 branch
                'a3',  # both terminate at a3
                'a2', 'a1'  # finish out
            ]  # noqa
        )

    def test_two_branches_end_in_branch(self):
        self._assert_iteration(
            "merge", "b1",
            # 'b1' is local to 'e2b1'
            # branch so that is all we get
            ['merge', 'e2b1', 'db1', 'cb1', 'b1',

        ]  # noqa
        )

    def test_two_branches_end_behind_branch(self):
        self._assert_iteration(
            "merge", "a2",
            ['merge',
                'e2b1', 'db1', 'cb1', 'b1',  # e2b1 branch
                'e2b2', 'db2', 'cb2', 'b2',  # e2b2 branch
                'a3',  # both terminate at a3
                'a2'
            ]  # noqa
        )

    def test_three_branches_to_root(self):

        # in this case, both "a3" and "db1" are stop points
        self._assert_iteration(
            ["merge", "fe1b1"], "a1",
            ['merge',
                'e2b1',  # e2b1 branch
                'e2b2', 'db2', 'cb2', 'b2',  # e2b2 branch
                'fe1b1', 'e1b1',  # fe1b1 branch
                'db1',  # fe1b1 and e2b1 branches terminate at db1
                'cb1', 'b1',  # e2b1 branch continued....might be nicer
                              # if this was before the e2b2 branch...
                'a3',  # e2b1 and e2b2 branches terminate at a3
                'a2', 'a1'  # finish out
            ]  # noqa
        )

    def test_three_branches_end_multiple_bases(self):

        # in this case, both "a3" and "db1" are stop points
        self._assert_iteration(
            ["merge", "fe1b1"], ["cb1", "cb2"],
            [
                'merge',
                'e2b1',
                'e2b2', 'db2', 'cb2',
                'fe1b1', 'e1b1',
                'db1',
                'cb1'
            ]
        )

    def test_three_branches_end_multiple_bases_exclusive(self):

        self._assert_iteration(
            ["merge", "fe1b1"], ["cb1", "cb2"],
            [
                'merge',
                'e2b1',
                'e2b2', 'db2',
                'fe1b1', 'e1b1',
                'db1',
            ],
            inclusive=False
        )

    def test_detect_invalid_head_selection(self):
        # db1 is an ancestor of fe1b1
        assert_raises_message(
            RevisionError,
            "Requested revision fe1b1 overlaps "
            "with other requested revisions",
            list,
            self.map._iterate_revisions(["db1", "b2", "fe1b1"], ())
        )

    def test_three_branches_end_multiple_bases_exclusive_blank(self):
        self._assert_iteration(
            ["e2b1", "b2", "fe1b1"], (),
            [
                'e2b1',
                'b2',
                'fe1b1', 'e1b1',
                'db1', 'cb1', 'b1', 'a3', 'a2', 'a1'
            ],
            inclusive=False
        )

    def test_iterate_to_symbolic_base(self):
        self._assert_iteration(
            ["fe1b1"], "base",
            ['fe1b1', 'e1b1', 'db1', 'cb1', 'b1', 'a3', 'a2', 'a1'],
            inclusive=False
        )


class MultipleBaseTest(DownIterateTest):
    def setUp(self):
        self.map = RevisionMap(
            lambda: [
                Revision('base1', ()),
                Revision('base2', ()),
                Revision('base3', ()),

                Revision('a1a', ('base1',)),
                Revision('a1b', ('base1',)),
                Revision('a2', ('base2',)),
                Revision('a3', ('base3',)),

                Revision('b1a', ('a1a',)),
                Revision('b1b', ('a1b',)),
                Revision('b2', ('a2',)),
                Revision('b3', ('a3',)),

                Revision('c2', ('b2',)),
                Revision('d2', ('c2',)),

                Revision('mergeb3d2', ('b3', 'd2'))
            ]
        )

    def test_heads_to_base(self):
        self._assert_iteration(
            "heads", "base",
            [
                'b1a', 'a1a',
                'b1b', 'a1b',
                'mergeb3d2',
                    'b3', 'a3', 'base3',
                    'd2', 'c2', 'b2', 'a2', 'base2',
                'base1'
            ]
        )

    def test_heads_to_base_exclusive(self):
        self._assert_iteration(
            "heads", "base",
            [
                'b1a', 'a1a',
                'b1b', 'a1b',
                'mergeb3d2',
                    'b3', 'a3', 'base3',
                    'd2', 'c2', 'b2', 'a2', 'base2',
                    'base1',
            ],
            inclusive=False
        )

    def test_heads_to_blank(self):
        self._assert_iteration(
            "heads", None,
            [
                'b1a', 'a1a',
                'b1b', 'a1b',
                'mergeb3d2',
                    'b3', 'a3', 'base3',
                    'd2', 'c2', 'b2', 'a2', 'base2',
                'base1'
            ]
        )

    def test_detect_invalid_base_selection(self):
        assert_raises_message(
            RevisionError,
            "Requested revision a2 overlaps with "
            "other requested revisions",
            list,
            self.map._iterate_revisions(["c2"], ["a2", "b2"])
        )

    def test_heads_to_revs_plus_implicit_base_exclusive(self):
        self._assert_iteration(
            "heads", ["c2"],
            [
                'b1a', 'a1a',
                'b1b', 'a1b',
                'mergeb3d2',
                    'b3', 'a3', 'base3',
                    'd2',
                'base1'
            ],
            inclusive=False,
            implicit_base=True
        )

    def test_heads_to_revs_base_exclusive(self):
        self._assert_iteration(
            "heads", ["c2"],
            [
                'mergeb3d2', 'd2'
            ],
            inclusive=False
        )

    def test_heads_to_revs_plus_implicit_base_inclusive(self):
        self._assert_iteration(
            "heads", ["c2"],
            [
                'b1a', 'a1a',
                'b1b', 'a1b',
                'mergeb3d2',
                    'b3', 'a3', 'base3',
                    'd2', 'c2',
                'base1'
            ],
            implicit_base=True
        )

    def test_specific_path_one(self):
        self._assert_iteration(
            "b3", "base3",
            ['b3', 'a3', 'base3']
        )

    def test_specific_path_two_implicit_base(self):
        self._assert_iteration(
            ["b3", "b2"], "base3",
            ['b3', 'a3', 'b2', 'a2', 'base2'],
            inclusive=False, implicit_base=True
        )
