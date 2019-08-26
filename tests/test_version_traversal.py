from alembic import util
from alembic.migration import HeadMaintainer
from alembic.migration import MigrationStep
from alembic.testing import assert_raises_message
from alembic.testing import eq_
from alembic.testing import mock
from alembic.testing.env import clear_staging_env
from alembic.testing.env import staging_env
from alembic.testing.fixtures import TestBase


class MigrationTest(TestBase):
    def up_(self, rev):
        return MigrationStep.upgrade_from_script(self.env.revision_map, rev)

    def down_(self, rev):
        return MigrationStep.downgrade_from_script(self.env.revision_map, rev)

    def _assert_downgrade(self, destination, source, expected, expected_heads):
        revs = self.env._downgrade_revs(destination, source)
        eq_(revs, expected)
        heads = set(util.to_tuple(source, default=()))
        head = HeadMaintainer(mock.Mock(), heads)
        for rev in revs:
            head.update_to_step(rev)
        eq_(head.heads, expected_heads)

    def _assert_upgrade(self, destination, source, expected, expected_heads):
        revs = self.env._upgrade_revs(destination, source)
        eq_(revs, expected)
        heads = set(util.to_tuple(source, default=()))
        head = HeadMaintainer(mock.Mock(), heads)
        for rev in revs:
            head.update_to_step(rev)
        eq_(head.heads, expected_heads)


class RevisionPathTest(MigrationTest):
    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a = env.generate_revision(util.rev_id(), "->a")
        cls.b = env.generate_revision(util.rev_id(), "a->b")
        cls.c = env.generate_revision(util.rev_id(), "b->c")
        cls.d = env.generate_revision(util.rev_id(), "c->d")
        cls.e = env.generate_revision(util.rev_id(), "d->e")

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_upgrade_path(self):
        self._assert_upgrade(
            self.e.revision,
            self.c.revision,
            [self.up_(self.d), self.up_(self.e)],
            set([self.e.revision]),
        )

        self._assert_upgrade(
            self.c.revision,
            None,
            [self.up_(self.a), self.up_(self.b), self.up_(self.c)],
            set([self.c.revision]),
        )

    def test_relative_upgrade_path(self):
        self._assert_upgrade(
            "+2",
            self.a.revision,
            [self.up_(self.b), self.up_(self.c)],
            set([self.c.revision]),
        )

        self._assert_upgrade(
            "+1", self.a.revision, [self.up_(self.b)], set([self.b.revision])
        )

        self._assert_upgrade(
            "+3",
            self.b.revision,
            [self.up_(self.c), self.up_(self.d), self.up_(self.e)],
            set([self.e.revision]),
        )

        self._assert_upgrade(
            "%s+2" % self.b.revision,
            self.a.revision,
            [self.up_(self.b), self.up_(self.c), self.up_(self.d)],
            set([self.d.revision]),
        )

        self._assert_upgrade(
            "%s-2" % self.d.revision,
            self.a.revision,
            [self.up_(self.b)],
            set([self.b.revision]),
        )

    def test_invalid_relative_upgrade_path(self):

        assert_raises_message(
            util.CommandError,
            "Relative revision -2 didn't produce 2 migrations",
            self.env._upgrade_revs,
            "-2",
            self.b.revision,
        )

        assert_raises_message(
            util.CommandError,
            r"Relative revision \+5 didn't produce 5 migrations",
            self.env._upgrade_revs,
            "+5",
            self.b.revision,
        )

    def test_downgrade_path(self):

        self._assert_downgrade(
            self.c.revision,
            self.e.revision,
            [self.down_(self.e), self.down_(self.d)],
            set([self.c.revision]),
        )

        self._assert_downgrade(
            None,
            self.c.revision,
            [self.down_(self.c), self.down_(self.b), self.down_(self.a)],
            set(),
        )

    def test_relative_downgrade_path(self):

        self._assert_downgrade(
            "-1", self.c.revision, [self.down_(self.c)], set([self.b.revision])
        )

        self._assert_downgrade(
            "-3",
            self.e.revision,
            [self.down_(self.e), self.down_(self.d), self.down_(self.c)],
            set([self.b.revision]),
        )

        self._assert_downgrade(
            "%s+2" % self.a.revision,
            self.d.revision,
            [self.down_(self.d)],
            set([self.c.revision]),
        )

        self._assert_downgrade(
            "%s-2" % self.c.revision,
            self.d.revision,
            [self.down_(self.d), self.down_(self.c), self.down_(self.b)],
            set([self.a.revision]),
        )

    def test_invalid_relative_downgrade_path(self):

        assert_raises_message(
            util.CommandError,
            "Relative revision -5 didn't produce 5 migrations",
            self.env._downgrade_revs,
            "-5",
            self.b.revision,
        )

        assert_raises_message(
            util.CommandError,
            r"Relative revision \+2 didn't produce 2 migrations",
            self.env._downgrade_revs,
            "+2",
            self.b.revision,
        )

    def test_invalid_move_rev_to_none(self):

        assert_raises_message(
            util.CommandError,
            r"Destination %s is not a valid downgrade "
            r"target from current head\(s\)" % self.b.revision[0:3],
            self.env._downgrade_revs,
            self.b.revision[0:3],
            None,
        )

    def test_invalid_move_higher_to_lower(self):

        assert_raises_message(
            util.CommandError,
            r"Destination %s is not a valid downgrade "
            r"target from current head\(s\)" % self.c.revision[0:4],
            self.env._downgrade_revs,
            self.c.revision[0:4],
            self.b.revision,
        )

    def test_stamp_to_base(self):
        revs = self.env._stamp_revs("base", self.d.revision)
        eq_(len(revs), 1)
        assert revs[0].should_delete_branch
        eq_(revs[0].delete_version_num, self.d.revision)


class BranchedPathTest(MigrationTest):
    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a = env.generate_revision(util.rev_id(), "->a")
        cls.b = env.generate_revision(util.rev_id(), "a->b")

        cls.c1 = env.generate_revision(
            util.rev_id(), "b->c1", branch_labels="c1branch", refresh=True
        )
        cls.d1 = env.generate_revision(util.rev_id(), "c1->d1")

        cls.c2 = env.generate_revision(
            util.rev_id(),
            "b->c2",
            branch_labels="c2branch",
            head=cls.b.revision,
            splice=True,
        )
        cls.d2 = env.generate_revision(
            util.rev_id(), "c2->d2", head=cls.c2.revision
        )

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_stamp_down_across_multiple_branch_to_branchpoint(self):
        heads = [self.d1.revision, self.c2.revision]
        revs = self.env._stamp_revs(self.b.revision, heads)
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents(heads),
            # DELETE d1 revision, UPDATE c2 to b
            ([self.d1.revision], self.c2.revision, self.b.revision),
        )

    def test_stamp_to_labeled_base_multiple_heads(self):
        revs = self.env._stamp_revs(
            "c1branch@base", [self.d1.revision, self.c2.revision]
        )
        eq_(len(revs), 1)
        assert revs[0].should_delete_branch
        eq_(revs[0].delete_version_num, self.d1.revision)

    def test_stamp_to_labeled_head_multiple_heads(self):
        heads = [self.d1.revision, self.c2.revision]
        revs = self.env._stamp_revs("c2branch@head", heads)
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents(heads),
            # the c1branch remains unchanged
            ([], self.c2.revision, self.d2.revision),
        )

    def test_upgrade_single_branch(self):

        self._assert_upgrade(
            self.d1.revision,
            self.b.revision,
            [self.up_(self.c1), self.up_(self.d1)],
            set([self.d1.revision]),
        )

    def test_upgrade_multiple_branch(self):
        # move from a single head to multiple heads

        self._assert_upgrade(
            (self.d1.revision, self.d2.revision),
            self.a.revision,
            [
                self.up_(self.b),
                self.up_(self.c2),
                self.up_(self.d2),
                self.up_(self.c1),
                self.up_(self.d1),
            ],
            set([self.d1.revision, self.d2.revision]),
        )

    def test_downgrade_multiple_branch(self):
        self._assert_downgrade(
            self.a.revision,
            (self.d1.revision, self.d2.revision),
            [
                self.down_(self.d1),
                self.down_(self.c1),
                self.down_(self.d2),
                self.down_(self.c2),
                self.down_(self.b),
            ],
            set([self.a.revision]),
        )

    def test_relative_upgrade(self):

        self._assert_upgrade(
            "c2branch@head-1",
            self.b.revision,
            [self.up_(self.c2)],
            set([self.c2.revision]),
        )

    def test_relative_downgrade(self):

        self._assert_downgrade(
            "c2branch@base+2",
            [self.d2.revision, self.d1.revision],
            [self.down_(self.d2), self.down_(self.c2), self.down_(self.d1)],
            set([self.c1.revision]),
        )


class BranchFromMergepointTest(MigrationTest):

    """this is a form that will come up frequently in the
    "many independent roots with cross-dependencies" case.

    """

    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision(util.rev_id(), "->a1")
        cls.b1 = env.generate_revision(util.rev_id(), "a1->b1")
        cls.c1 = env.generate_revision(util.rev_id(), "b1->c1")

        cls.a2 = env.generate_revision(
            util.rev_id(), "->a2", head=(), refresh=True
        )
        cls.b2 = env.generate_revision(
            util.rev_id(), "a2->b2", head=cls.a2.revision
        )
        cls.c2 = env.generate_revision(
            util.rev_id(), "b2->c2", head=cls.b2.revision
        )

        # mergepoint between c1, c2
        # d1 dependent on c2
        cls.d1 = env.generate_revision(
            util.rev_id(),
            "d1",
            head=(cls.c1.revision, cls.c2.revision),
            refresh=True,
        )

        # but then c2 keeps going into d2
        cls.d2 = env.generate_revision(
            util.rev_id(),
            "d2",
            head=cls.c2.revision,
            refresh=True,
            splice=True,
        )

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_mergepoint_to_only_one_side_upgrade(self):

        self._assert_upgrade(
            self.d1.revision,
            (self.d2.revision, self.b1.revision),
            [self.up_(self.c1), self.up_(self.d1)],
            set([self.d2.revision, self.d1.revision]),
        )

    def test_mergepoint_to_only_one_side_downgrade(self):

        self._assert_downgrade(
            self.b1.revision,
            (self.d2.revision, self.d1.revision),
            [self.down_(self.d1), self.down_(self.c1)],
            set([self.d2.revision, self.b1.revision]),
        )


class BranchFrom3WayMergepointTest(MigrationTest):

    """this is a form that will come up frequently in the
    "many independent roots with cross-dependencies" case.

    """

    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision(util.rev_id(), "->a1")
        cls.b1 = env.generate_revision(util.rev_id(), "a1->b1")
        cls.c1 = env.generate_revision(util.rev_id(), "b1->c1")

        cls.a2 = env.generate_revision(
            util.rev_id(), "->a2", head=(), refresh=True
        )
        cls.b2 = env.generate_revision(
            util.rev_id(), "a2->b2", head=cls.a2.revision
        )
        cls.c2 = env.generate_revision(
            util.rev_id(), "b2->c2", head=cls.b2.revision
        )

        cls.a3 = env.generate_revision(
            util.rev_id(), "->a3", head=(), refresh=True
        )
        cls.b3 = env.generate_revision(
            util.rev_id(), "a3->b3", head=cls.a3.revision
        )
        cls.c3 = env.generate_revision(
            util.rev_id(), "b3->c3", head=cls.b3.revision
        )

        # mergepoint between c1, c2, c3
        # d1 dependent on c2, c3
        cls.d1 = env.generate_revision(
            util.rev_id(),
            "d1",
            head=(cls.c1.revision, cls.c2.revision, cls.c3.revision),
            refresh=True,
        )

        # but then c2 keeps going into d2
        cls.d2 = env.generate_revision(
            util.rev_id(),
            "d2",
            head=cls.c2.revision,
            refresh=True,
            splice=True,
        )

        # c3 keeps going into d3
        cls.d3 = env.generate_revision(
            util.rev_id(),
            "d3",
            head=cls.c3.revision,
            refresh=True,
            splice=True,
        )

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_mergepoint_to_only_one_side_upgrade(self):

        self._assert_upgrade(
            self.d1.revision,
            (self.d3.revision, self.d2.revision, self.b1.revision),
            [self.up_(self.c1), self.up_(self.d1)],
            set([self.d3.revision, self.d2.revision, self.d1.revision]),
        )

    def test_mergepoint_to_only_one_side_downgrade(self):
        self._assert_downgrade(
            self.b1.revision,
            (self.d3.revision, self.d2.revision, self.d1.revision),
            [self.down_(self.d1), self.down_(self.c1)],
            set([self.d3.revision, self.d2.revision, self.b1.revision]),
        )

    def test_mergepoint_to_two_sides_upgrade(self):

        self._assert_upgrade(
            self.d1.revision,
            (self.d3.revision, self.b2.revision, self.b1.revision),
            [self.up_(self.c2), self.up_(self.c1), self.up_(self.d1)],
            # this will merge b2 and b1 into d1
            set([self.d3.revision, self.d1.revision]),
        )

        # but then!  b2 will break out again if we keep going with it
        self._assert_upgrade(
            self.d2.revision,
            (self.d3.revision, self.d1.revision),
            [self.up_(self.d2)],
            set([self.d3.revision, self.d2.revision, self.d1.revision]),
        )


class TwinMergeTest(MigrationTest):
    """Test #297, where we have two mergepoints from the same set of
    originating branches.

    """

    @classmethod
    def setup_class(cls):
        """

        33e21c000cfe -> 178d4e761bbd (head),
        2bef33cb3a58, 3904558db1c6, 968330f320d -> 33e21c000cfe (mergepoint)
        46c99f866004 -> 18f46b42410d (head),
        2bef33cb3a58, 3904558db1c6, 968330f320d -> 46c99f866004 (mergepoint)
        f0fa4315825 -> 3904558db1c6 (branchpoint),

        --------------------------

        A -> B2 (branchpoint),

        B1, B2, B3 -> C1 (mergepoint)
        B1, B2, B3 -> C2 (mergepoint)

        C1 -> D1 (head),

        C2 -> D2 (head),


        """
        cls.env = env = staging_env()

        cls.a = env.generate_revision("a", "a")
        cls.b1 = env.generate_revision("b1", "b1", head=cls.a.revision)
        cls.b2 = env.generate_revision(
            "b2", "b2", splice=True, head=cls.a.revision
        )
        cls.b3 = env.generate_revision(
            "b3", "b3", splice=True, head=cls.a.revision
        )

        cls.c1 = env.generate_revision(
            "c1",
            "c1",
            head=(cls.b1.revision, cls.b2.revision, cls.b3.revision),
        )

        cls.c2 = env.generate_revision(
            "c2",
            "c2",
            splice=True,
            head=(cls.b1.revision, cls.b2.revision, cls.b3.revision),
        )

        cls.d1 = env.generate_revision("d1", "d1", head=cls.c1.revision)

        cls.d2 = env.generate_revision("d2", "d2", head=cls.c2.revision)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_upgrade(self):
        head = HeadMaintainer(mock.Mock(), [self.a.revision])

        steps = [
            (self.up_(self.b3), ("b3",)),
            (self.up_(self.b1), ("b1", "b3")),
            (self.up_(self.b2), ("b1", "b2", "b3")),
            (self.up_(self.c2), ("c2",)),
            (self.up_(self.d2), ("d2",)),
            (self.up_(self.c1), ("c1", "d2")),
            (self.up_(self.d1), ("d1", "d2")),
        ]
        for step, assert_ in steps:
            head.update_to_step(step)
            eq_(head.heads, set(assert_))


class NotQuiteTwinMergeTest(MigrationTest):
    """Test a variant of #297.

    """

    @classmethod
    def setup_class(cls):
        """
        A -> B2 (branchpoint),

        B1, B2 -> C1 (mergepoint)
        B2, B3 -> C2 (mergepoint)

        C1 -> D1 (head),

        C2 -> D2 (head),


        """
        cls.env = env = staging_env()

        cls.a = env.generate_revision("a", "a")
        cls.b1 = env.generate_revision("b1", "b1", head=cls.a.revision)
        cls.b2 = env.generate_revision(
            "b2", "b2", splice=True, head=cls.a.revision
        )
        cls.b3 = env.generate_revision(
            "b3", "b3", splice=True, head=cls.a.revision
        )

        cls.c1 = env.generate_revision(
            "c1", "c1", head=(cls.b1.revision, cls.b2.revision)
        )

        cls.c2 = env.generate_revision(
            "c2", "c2", splice=True, head=(cls.b2.revision, cls.b3.revision)
        )

        cls.d1 = env.generate_revision("d1", "d1", head=cls.c1.revision)

        cls.d2 = env.generate_revision("d2", "d2", head=cls.c2.revision)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_upgrade(self):
        head = HeadMaintainer(mock.Mock(), [self.a.revision])

        """
        upgrade a -> b2, b2
        upgrade a -> b3, b3
        upgrade b2, b3 -> c2, c2
        upgrade c2 -> d2, d2
        upgrade a -> b1, b1
        upgrade b1, b2 -> c1, c1
        upgrade c1 -> d1, d1
        """

        steps = [
            (self.up_(self.b2), ("b2",)),
            (self.up_(self.b3), ("b2", "b3")),
            (self.up_(self.c2), ("c2",)),
            (self.up_(self.d2), ("d2",)),
            (self.up_(self.b1), ("b1", "d2")),
            (self.up_(self.c1), ("c1", "d2")),
            (self.up_(self.d1), ("d1", "d2")),
        ]
        for step, assert_ in steps:
            head.update_to_step(step)
            eq_(head.heads, set(assert_))


class DependsOnBranchTestOne(MigrationTest):
    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision(
            util.rev_id(), "->a1", branch_labels=["lib1"]
        )
        cls.b1 = env.generate_revision(util.rev_id(), "a1->b1")
        cls.c1 = env.generate_revision(util.rev_id(), "b1->c1")

        cls.a2 = env.generate_revision(util.rev_id(), "->a2", head=())
        cls.b2 = env.generate_revision(
            util.rev_id(), "a2->b2", head=cls.a2.revision
        )
        cls.c2 = env.generate_revision(
            util.rev_id(),
            "b2->c2",
            head=cls.b2.revision,
            depends_on=cls.c1.revision,
        )

        cls.d1 = env.generate_revision(
            util.rev_id(), "c1->d1", head=cls.c1.revision
        )
        cls.e1 = env.generate_revision(
            util.rev_id(), "d1->e1", head=cls.d1.revision
        )
        cls.f1 = env.generate_revision(
            util.rev_id(), "e1->f1", head=cls.e1.revision
        )

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_downgrade_to_dependency(self):
        heads = [self.c2.revision, self.d1.revision]
        head = HeadMaintainer(mock.Mock(), heads)
        head.update_to_step(self.down_(self.d1))
        eq_(head.heads, set([self.c2.revision]))

    def test_stamp_across_dependency(self):
        heads = [self.e1.revision, self.c2.revision]
        head = HeadMaintainer(mock.Mock(), heads)
        for step in self.env._stamp_revs(self.b1.revision, heads):
            head.update_to_step(step)
        eq_(head.heads, set([self.b1.revision]))


class DependsOnBranchTestTwo(MigrationTest):
    @classmethod
    def setup_class(cls):
        """
        Structure::

            a1 ---+
                  |
            a2 ---+--> amerge
                  |
            a3 ---+
             ^
             |
             +---------------------------+
                                         |
            b1 ---+                      |
                  +--> bmerge        overmerge / d1
            b2 ---+                     |  |
             ^                          |  |
             |                          |  |
             +--------------------------+  |
                                           |
             +-----------------------------+
             |
             v
            c1 ---+
                  |
            c2 ---+--> cmerge
                  |
            c3 ---+

        """
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision("a1", "->a1", head="base")
        cls.a2 = env.generate_revision("a2", "->a2", head="base")
        cls.a3 = env.generate_revision("a3", "->a3", head="base")
        cls.amerge = env.generate_revision(
            "amerge",
            "amerge",
            head=[cls.a1.revision, cls.a2.revision, cls.a3.revision],
        )

        cls.b1 = env.generate_revision("b1", "->b1", head="base")
        cls.b2 = env.generate_revision("b2", "->b2", head="base")
        cls.bmerge = env.generate_revision(
            "bmerge", "bmerge", head=[cls.b1.revision, cls.b2.revision]
        )

        cls.c1 = env.generate_revision("c1", "->c1", head="base")
        cls.c2 = env.generate_revision("c2", "->c2", head="base")
        cls.c3 = env.generate_revision("c3", "->c3", head="base")
        cls.cmerge = env.generate_revision(
            "cmerge",
            "cmerge",
            head=[cls.c1.revision, cls.c2.revision, cls.c3.revision],
        )

        cls.d1 = env.generate_revision(
            "d1",
            "o",
            head="base",
            depends_on=[cls.a3.revision, cls.b2.revision, cls.c1.revision],
        )

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_kaboom(self):
        # here's the upgrade path:
        # ['->c1', '->b2', '->a3', 'overmerge', '->c3', '->c2', 'cmerge',
        # '->b1', 'bmerge', '->a2', '->a1', 'amerge'],

        heads = [
            self.amerge.revision,
            self.bmerge.revision,
            self.cmerge.revision,
            self.d1.revision,
        ]

        self._assert_downgrade(
            self.b2.revision,
            heads,
            [self.down_(self.bmerge)],
            set(
                [
                    self.amerge.revision,
                    self.b1.revision,
                    self.cmerge.revision,
                    self.d1.revision,
                ]
            ),
        )

        # start with those heads..
        heads = [
            self.amerge.revision,
            self.d1.revision,
            self.b1.revision,
            self.cmerge.revision,
        ]

        # downgrade d1...
        self._assert_downgrade(
            "d1@base",
            heads,
            [self.down_(self.d1)],
            # b2 has to be INSERTed, because it was implied by d1
            set(
                [
                    self.amerge.revision,
                    self.b1.revision,
                    self.b2.revision,
                    self.cmerge.revision,
                ]
            ),
        )

        # start with those heads ...
        heads = [
            self.amerge.revision,
            self.b1.revision,
            self.b2.revision,
            self.cmerge.revision,
        ]

        self._assert_downgrade(
            "base",
            heads,
            [
                self.down_(self.amerge),
                self.down_(self.a1),
                self.down_(self.a2),
                self.down_(self.a3),
                self.down_(self.b1),
                self.down_(self.b2),
                self.down_(self.cmerge),
                self.down_(self.c1),
                self.down_(self.c2),
                self.down_(self.c3),
            ],
            set([]),
        )


class DependsOnBranchTestThree(MigrationTest):
    @classmethod
    def setup_class(cls):
        """
        issue #377

        Structure::

            <base> -> a1 --+--> a2 -------> a3
                           |     ^          |
                           |     |   +------+
                           |     |   |
                           |     +---|------+
                           |         |      |
                           |         v      |
                           +-------> b1 --> b2 --> b3

        """
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision("a1", "->a1", head="base")
        cls.a2 = env.generate_revision("a2", "->a2")

        cls.b1 = env.generate_revision("b1", "->b1", head="base")
        cls.b2 = env.generate_revision(
            "b2", "->b2", depends_on="a2", head="b1"
        )
        cls.b3 = env.generate_revision("b3", "->b3", head="b2")

        cls.a3 = env.generate_revision(
            "a3", "->a3", head="a2", depends_on="b1"
        )

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_downgrade_over_crisscross(self):
        # this state was not possible prior to
        # #377.  a3 would be considered half of a merge point
        # between a3 and b2, and the head would be forced down
        # to b1.   In this test however, we're not allowed to remove
        # b2 because a2 is dependent on it, hence we add the ability
        # to remove half of a merge point.
        self._assert_downgrade(
            "b1",
            ["a3", "b2"],
            [self.down_(self.b2)],
            set(["a3"]),  # we have b1 also, which is implied by a3
        )


class DependsOnBranchLabelTest(MigrationTest):
    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision(
            util.rev_id(), "->a1", branch_labels=["lib1"]
        )
        cls.b1 = env.generate_revision(util.rev_id(), "a1->b1")
        cls.c1 = env.generate_revision(
            util.rev_id(), "b1->c1", branch_labels=["c1lib"]
        )

        cls.a2 = env.generate_revision(util.rev_id(), "->a2", head=())
        cls.b2 = env.generate_revision(
            util.rev_id(), "a2->b2", head=cls.a2.revision
        )
        cls.c2 = env.generate_revision(
            util.rev_id(), "b2->c2", head=cls.b2.revision, depends_on=["c1lib"]
        )

        cls.d1 = env.generate_revision(
            util.rev_id(), "c1->d1", head=cls.c1.revision
        )
        cls.e1 = env.generate_revision(
            util.rev_id(), "d1->e1", head=cls.d1.revision
        )
        cls.f1 = env.generate_revision(
            util.rev_id(), "e1->f1", head=cls.e1.revision
        )

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_upgrade_path(self):
        self._assert_upgrade(
            self.c2.revision,
            self.a2.revision,
            [
                self.up_(self.a1),
                self.up_(self.b1),
                self.up_(self.c1),
                self.up_(self.b2),
                self.up_(self.c2),
            ],
            set([self.c2.revision]),
        )


class ForestTest(MigrationTest):
    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision(util.rev_id(), "->a1")
        cls.b1 = env.generate_revision(util.rev_id(), "a1->b1")

        cls.a2 = env.generate_revision(
            util.rev_id(), "->a2", head=(), refresh=True
        )
        cls.b2 = env.generate_revision(
            util.rev_id(), "a2->b2", head=cls.a2.revision
        )

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_base_to_heads(self):
        eq_(
            self.env._upgrade_revs("heads", "base"),
            [
                self.up_(self.a2),
                self.up_(self.b2),
                self.up_(self.a1),
                self.up_(self.b1),
            ],
        )

    def test_stamp_to_heads(self):
        revs = self.env._stamp_revs("heads", ())
        eq_(len(revs), 2)
        eq_(
            set(r.to_revisions for r in revs),
            set([(self.b1.revision,), (self.b2.revision,)]),
        )

    def test_stamp_to_heads_no_moves_needed(self):
        revs = self.env._stamp_revs(
            "heads", (self.b1.revision, self.b2.revision)
        )
        eq_(len(revs), 0)


class MergedPathTest(MigrationTest):
    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a = env.generate_revision(util.rev_id(), "->a")
        cls.b = env.generate_revision(util.rev_id(), "a->b")

        cls.c1 = env.generate_revision(util.rev_id(), "b->c1")
        cls.d1 = env.generate_revision(util.rev_id(), "c1->d1")

        cls.c2 = env.generate_revision(
            util.rev_id(),
            "b->c2",
            branch_labels="c2branch",
            head=cls.b.revision,
            splice=True,
        )
        cls.d2 = env.generate_revision(
            util.rev_id(), "c2->d2", head=cls.c2.revision
        )

        cls.e = env.generate_revision(
            util.rev_id(),
            "merge d1 and d2",
            head=(cls.d1.revision, cls.d2.revision),
        )

        cls.f = env.generate_revision(util.rev_id(), "e->f")

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_stamp_down_across_merge_point_branch(self):
        heads = [self.e.revision]
        revs = self.env._stamp_revs(self.c2.revision, heads)
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents(heads),
            # no deletes, UPDATE e to c2
            ([], self.e.revision, self.c2.revision),
        )

    def test_stamp_down_across_merge_prior_branching(self):
        heads = [self.e.revision]
        revs = self.env._stamp_revs(self.a.revision, heads)
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents(heads),
            # no deletes, UPDATE e to c2
            ([], self.e.revision, self.a.revision),
        )

    def test_stamp_up_across_merge_from_single_branch(self):
        revs = self.env._stamp_revs(self.e.revision, [self.c2.revision])
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents([self.c2.revision]),
            # no deletes, UPDATE e to c2
            ([], self.c2.revision, self.e.revision),
        )

    def test_stamp_labled_head_across_merge_from_multiple_branch(self):
        # this is testing that filter_for_lineage() checks for
        # d1 both in terms of "c2branch" as well as that the "head"
        # revision "f" is the head of both d1 and d2
        revs = self.env._stamp_revs(
            "c2branch@head", [self.d1.revision, self.c2.revision]
        )
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents([self.d1.revision, self.c2.revision]),
            # DELETE d1 revision, UPDATE c2 to e
            ([self.d1.revision], self.c2.revision, self.f.revision),
        )

    def test_stamp_up_across_merge_from_multiple_branch(self):
        heads = [self.d1.revision, self.c2.revision]
        revs = self.env._stamp_revs(self.e.revision, heads)
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents(heads),
            # DELETE d1 revision, UPDATE c2 to e
            ([self.d1.revision], self.c2.revision, self.e.revision),
        )

    def test_stamp_up_across_merge_prior_branching(self):
        heads = [self.b.revision]
        revs = self.env._stamp_revs(self.e.revision, heads)
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents(heads),
            # no deletes, UPDATE e to c2
            ([], self.b.revision, self.e.revision),
        )

    def test_upgrade_across_merge_point(self):

        eq_(
            self.env._upgrade_revs(self.f.revision, self.b.revision),
            [
                self.up_(self.c2),
                self.up_(self.d2),
                self.up_(self.c1),  # b->c1, create new branch
                self.up_(self.d1),
                self.up_(self.e),  # d1/d2 -> e, merge branches
                # (DELETE d2, UPDATE d1->e)
                self.up_(self.f),
            ],
        )

    def test_downgrade_across_merge_point(self):

        eq_(
            self.env._downgrade_revs(self.b.revision, self.f.revision),
            [
                self.down_(self.f),
                self.down_(self.e),  # e -> d1 and d2, unmerge branches
                # (UPDATE e->d1, INSERT d2)
                self.down_(self.d1),
                self.down_(self.c1),
                self.down_(self.d2),
                self.down_(self.c2),  # c2->b, delete branch
            ],
        )
