from alembic import util
from alembic.migration import HeadMaintainer
from alembic.migration import MigrationStep
from alembic.testing import assert_raises_message
from alembic.testing import eq_
from alembic.testing import expect_warnings
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

        cls.a = env.generate_revision("e6239818bb3a", "->a")
        cls.b = env.generate_revision("548bbb905360", "a->b")
        cls.c = env.generate_revision("b7ea43dc85e4", "b->c")
        cls.d = env.generate_revision("1bbe33445780", "c->d")
        cls.e = env.generate_revision("3975fb1a0125", "d->e")

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_downgrade_base_no_version(self):
        self._assert_downgrade("base", [], [], set())

    def test_downgrade_to_existing(self):
        """test for #838; downgrade to a revision that's already in
        current heads, but is not itself a head."""

        self._assert_downgrade(
            self.a.revision, [self.a.revision], [], {self.a.revision}
        )

    def test_downgrade_to_existing_head(self):
        """test for #839; downgrade to a revision that's already in current
        heads, which *is* itself a head."""

        self._assert_downgrade(
            self.e.revision, [self.e.revision], [], {self.e.revision}
        )

    def test_upgrade_path(self):
        self._assert_upgrade(
            self.e.revision,
            self.c.revision,
            [self.up_(self.d), self.up_(self.e)],
            {self.e.revision},
        )

        self._assert_upgrade(
            self.c.revision,
            None,
            [self.up_(self.a), self.up_(self.b), self.up_(self.c)],
            {self.c.revision},
        )

    def test_relative_upgrade_path(self):
        self._assert_upgrade(
            "+2",
            self.a.revision,
            [self.up_(self.b), self.up_(self.c)],
            {self.c.revision},
        )

        self._assert_upgrade(
            "+1", self.a.revision, [self.up_(self.b)], {self.b.revision}
        )

        self._assert_upgrade(
            "+3",
            self.b.revision,
            [self.up_(self.c), self.up_(self.d), self.up_(self.e)],
            {self.e.revision},
        )

        self._assert_upgrade(
            "%s+2" % self.b.revision,
            self.a.revision,
            [self.up_(self.b), self.up_(self.c), self.up_(self.d)],
            {self.d.revision},
        )

        self._assert_upgrade(
            "%s-2" % self.d.revision,
            self.a.revision,
            [self.up_(self.b)],
            {self.b.revision},
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
            {self.c.revision},
        )

        self._assert_downgrade(
            None,
            self.c.revision,
            [self.down_(self.c), self.down_(self.b), self.down_(self.a)],
            set(),
        )

    def test_relative_downgrade_path(self):

        self._assert_downgrade(
            "-1", self.c.revision, [self.down_(self.c)], {self.b.revision}
        )

        self._assert_downgrade(
            "-3",
            self.e.revision,
            [self.down_(self.e), self.down_(self.d), self.down_(self.c)],
            {self.b.revision},
        )

        self._assert_downgrade(
            "%s+2" % self.a.revision,
            self.d.revision,
            [self.down_(self.d)],
            {self.c.revision},
        )

        self._assert_downgrade(
            "%s-2" % self.c.revision,
            self.d.revision,
            [self.down_(self.d), self.down_(self.c), self.down_(self.b)],
            {self.a.revision},
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
            {self.d1.revision},
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
            {self.d1.revision, self.d2.revision},
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
            {self.a.revision},
        )

    def test_relative_upgrade(self):

        self._assert_upgrade(
            "c2branch@head-1",
            self.b.revision,
            [self.up_(self.c2)],
            {self.c2.revision},
        )

    def test_relative_downgrade_baseplus2(self):
        """base+2 points to b, no branch label, drop everything above b."""
        self._assert_downgrade(
            "base+2",
            [self.d2.revision, self.d1.revision],
            [
                self.down_(self.d1),
                self.down_(self.c1),
                self.down_(self.d2),
                self.down_(self.c2),
            ],
            {self.b.revision},
        )

    def test_relative_downgrade_branchplus2(self):
        """
        Correct behaviour (per
        https://github.com/sqlalchemy/alembic/pull/763#issuecomment-738741297)
        Only the c2branch should be downgraded, right back to base+2 = b
        """
        self._assert_downgrade(
            "c2branch@base+2",
            [self.d2.revision, self.d1.revision],
            [self.down_(self.d2), self.down_(self.c2)],
            {self.d1.revision},
        )

    def test_relative_downgrade_branchplus3(self):
        """c2branch@base+3 equivalent to c2."""
        self._assert_downgrade(
            self.c2.revision,
            [self.d2.revision, self.d1.revision],
            [self.down_(self.d2)],
            {self.d1.revision, self.c2.revision},
        )
        self._assert_downgrade(
            "c2branch@base+3",
            [self.d2.revision, self.d1.revision],
            [self.down_(self.d2)],
            {self.d1.revision, self.c2.revision},
        )

    # Old downgrade -1 behaviour depends on order of branch upgrades.
    # This should probably fail (ambiguous) but is currently documented
    # as a key use case in branching.

    def test_downgrade_once_order_right(self):
        with expect_warnings("downgrade -1 from multiple heads is ambiguous;"):
            self._assert_downgrade(
                "-1",
                [self.d2.revision, self.d1.revision],
                [self.down_(self.d2)],
                {self.d1.revision, self.c2.revision},
            )

    def test_downgrade_once_order_right_unbalanced(self):
        with expect_warnings("downgrade -1 from multiple heads is ambiguous;"):
            self._assert_downgrade(
                "-1",
                [self.c2.revision, self.d1.revision],
                [self.down_(self.c2)],
                {self.d1.revision},
            )

    def test_downgrade_once_order_left(self):
        with expect_warnings("downgrade -1 from multiple heads is ambiguous;"):
            self._assert_downgrade(
                "-1",
                [self.d1.revision, self.d2.revision],
                [self.down_(self.d1)],
                {self.d2.revision, self.c1.revision},
            )

    def test_downgrade_once_order_left_unbalanced(self):
        with expect_warnings("downgrade -1 from multiple heads is ambiguous;"):
            self._assert_downgrade(
                "-1",
                [self.c1.revision, self.d2.revision],
                [self.down_(self.c1)],
                {self.d2.revision},
            )

    def test_downgrade_once_order_left_unbalanced_labelled(self):
        self._assert_downgrade(
            "c1branch@-1",
            [self.d1.revision, self.d2.revision],
            [self.down_(self.d1)],
            {self.c1.revision, self.d2.revision},
        )

    # Captures https://github.com/sqlalchemy/alembic/issues/765

    def test_downgrade_relative_order_right(self):
        self._assert_downgrade(
            f"{self.d2.revision}-1",
            [self.d2.revision, self.c1.revision],
            [self.down_(self.d2)],
            {self.c1.revision, self.c2.revision},
        )

    def test_downgrade_relative_order_left(self):
        self._assert_downgrade(
            f"{self.d2.revision}-1",
            [self.c1.revision, self.d2.revision],
            [self.down_(self.d2)],
            {self.c1.revision, self.c2.revision},
        )

    def test_downgrade_single_branch_c1branch(self):
        """Use branch label to specify the branch to downgrade."""
        self._assert_downgrade(
            f"c1branch@{self.b.revision}",
            (self.c1.revision, self.d2.revision),
            [
                self.down_(self.c1),
            ],
            {self.d2.revision},
        )

    def test_downgrade_single_branch_c1branch_from_d1_head(self):
        """Use branch label to specify the branch (where the branch label is
        not on the head revision)."""
        self._assert_downgrade(
            f"c2branch@{self.b.revision}",
            (self.c1.revision, self.d2.revision),
            [
                self.down_(self.d2),
                self.down_(self.c2),
            ],
            {self.c1.revision},
        )

    def test_downgrade_single_branch_c2(self):
        """Use a revision on the branch (not head) to specify the branch."""
        self._assert_downgrade(
            f"{self.c2.revision}@{self.b.revision}",
            (self.d1.revision, self.d2.revision),
            [
                self.down_(self.d2),
                self.down_(self.c2),
            ],
            {self.d1.revision},
        )

    def test_downgrade_single_branch_d1(self):
        """Use the head revision to specify the branch."""
        self._assert_downgrade(
            f"{self.d1.revision}@{self.b.revision}",
            (self.d1.revision, self.d2.revision),
            [
                self.down_(self.d1),
                self.down_(self.c1),
            ],
            {self.d2.revision},
        )

    def test_downgrade_relative_to_branch_head(self):
        self._assert_downgrade(
            "c1branch@head-1",
            (self.d1.revision, self.d2.revision),
            [self.down_(self.d1)],
            {self.c1.revision, self.d2.revision},
        )

    def test_upgrade_other_branch_from_mergepoint(self):
        # Advance c2branch forward by one, meaning one past the mergepoint
        # in this case.
        self._assert_upgrade(
            "c2branch@+1",
            (self.c1.revision),
            [self.up_(self.c2)],
            {self.c1.revision, self.c2.revision},
        )

    def test_upgrade_one_branch_of_heads(self):
        # Still a bit of ambiguity here ... does this mean an absolute
        # revision "goto revision c2 (labelled c2branch), +1", or "move up
        # one revision from current along c2branch"?
        self._assert_upgrade(
            "c2branch@+1",
            (self.c1.revision, self.c2.revision),
            [self.up_(self.d2)],
            {self.c1.revision, self.d2.revision},
        )

    def test_ambiguous_upgrade(self):
        assert_raises_message(
            util.CommandError,
            "Ambiguous upgrade from multiple current revisions",
            self.env._upgrade_revs,
            "+1",
            [self.c1.revision, self.c2.revision],
        )

    def test_upgrade_from_base(self):
        self._assert_upgrade(
            "base+1", [], [self.up_(self.a)], {self.a.revision}
        )

    def test_upgrade_from_base_implicit(self):
        self._assert_upgrade("+1", [], [self.up_(self.a)], {self.a.revision})

    def test_downgrade_minus1_to_base(self):
        self._assert_downgrade(
            "-1", [self.a.revision], [self.down_(self.a)], set()
        )

    def test_downgrade_minus1_from_base(self):
        assert_raises_message(
            util.CommandError,
            "Relative revision -1 didn't produce 1 migrations",
            self.env._downgrade_revs,
            "-1",
            [],
        )

    def test_downgrade_no_effect_branched(self):
        """Added for good measure when there are multiple branches."""
        self._assert_downgrade(
            self.c2.revision,
            [self.d1.revision, self.c2.revision],
            [],
            {self.d1.revision, self.c2.revision},
        )
        self._assert_downgrade(
            self.d1.revision,
            [self.d1.revision, self.c2.revision],
            [],
            {self.d1.revision, self.c2.revision},
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
            {self.d2.revision, self.d1.revision},
        )

    def test_mergepoint_to_only_one_side_downgrade(self):

        self._assert_downgrade(
            self.b1.revision,
            (self.d2.revision, self.d1.revision),
            [self.down_(self.d1), self.down_(self.c1)],
            {self.d2.revision, self.b1.revision},
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
            {self.d3.revision, self.d2.revision, self.d1.revision},
        )

    def test_mergepoint_to_only_one_side_downgrade(self):
        self._assert_downgrade(
            self.b1.revision,
            (self.d3.revision, self.d2.revision, self.d1.revision),
            [self.down_(self.d1), self.down_(self.c1)],
            {self.d3.revision, self.d2.revision, self.b1.revision},
        )

    def test_mergepoint_to_two_sides_upgrade(self):

        self._assert_upgrade(
            self.d1.revision,
            (self.d3.revision, self.b2.revision, self.b1.revision),
            [self.up_(self.c2), self.up_(self.c1), self.up_(self.d1)],
            # this will merge b2 and b1 into d1
            {self.d3.revision, self.d1.revision},
        )

        # but then!  b2 will break out again if we keep going with it
        self._assert_upgrade(
            self.d2.revision,
            (self.d3.revision, self.d1.revision),
            [self.up_(self.d2)],
            {self.d3.revision, self.d2.revision, self.d1.revision},
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
    """Test a variant of #297."""

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
        eq_(head.heads, {self.c2.revision})

    def test_stamp_across_dependency(self):
        heads = [self.e1.revision, self.c2.revision]
        head = HeadMaintainer(mock.Mock(), heads)
        for step in self.env._stamp_revs(self.b1.revision, heads):
            head.update_to_step(step)
        eq_(head.heads, {self.b1.revision})


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
            {
                self.amerge.revision,
                self.b1.revision,
                self.cmerge.revision,
                # b2 isn't here, but d1 is, which implies b2. OK!
                self.d1.revision,
            },
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
            {
                self.amerge.revision,
                self.b1.revision,
                # b2 has to be INSERTed, because it was implied by d1
                self.b2.revision,
                self.cmerge.revision,
            },
        )

        # start with those heads ...
        heads = [
            self.amerge.revision,
            self.b1.revision,
            self.b2.revision,
            self.cmerge.revision,
        ]

        # this ordering can vary a lot based on what
        # sorting algorithm is in use because it's all
        # heads
        self._assert_downgrade(
            "base",
            heads,
            [
                self.down_(self.amerge),
                self.down_(self.a1),
                self.down_(self.b1),
                self.down_(self.b2),
                self.down_(self.cmerge),
                self.down_(self.c1),
                self.down_(self.a2),
                self.down_(self.a3),
                self.down_(self.c2),
                self.down_(self.c3),
            ],
            set(),
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
            {"a3"},  # we have b1 also, which is implied by a3
        )


class DependsOnOwnDownrevTest(MigrationTest):
    @classmethod
    def setup_class(cls):
        """
        test #843
        """
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision("a1", "->a1", head="base")
        cls.a2 = env.generate_revision("a2", "->a2", depends_on="a1")

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_traverse(self):
        self._assert_upgrade(
            self.a2.revision,
            None,
            [self.up_(self.a1), self.up_(self.a2)],
            {"a2"},
        )

    def test_traverse_down(self):
        self._assert_downgrade(
            self.a1.revision,
            self.a2.revision,
            [self.down_(self.a2)],
            {"a1"},
        )


class DependsOnBranchTestFour(MigrationTest):
    @classmethod
    def setup_class(cls):
        """
        test issue #789
        """
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision("a1", "->a1", head="base")
        cls.a2 = env.generate_revision("a2", "->a2")
        cls.a3 = env.generate_revision("a3", "->a3")

        cls.b1 = env.generate_revision("b1", "->b1", head="base")
        cls.b2 = env.generate_revision(
            "b2", "->b2", head="b1", depends_on="a3"
        )
        cls.b3 = env.generate_revision("b3", "->b3", head="b2")
        cls.b4 = env.generate_revision(
            "b4", "->b4", head="b3", depends_on="a3"
        )

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_dependencies_are_normalized(self):

        heads = [self.b4.revision]

        self._assert_downgrade(
            self.b3.revision,
            heads,
            [self.down_(self.b4)],
            # a3 isn't here, because b3 still implies a3
            {self.b3.revision},
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
            {self.c2.revision},
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
            {r.to_revisions for r in revs},
            {(self.b1.revision,), (self.b2.revision,)},
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


class BranchedPathTestCrossDependencies(MigrationTest):
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
            util.rev_id(),
            "c2->d2",
            head=cls.c2.revision,
            depends_on=(cls.c1.revision,),
        )

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_downgrade_independent_branch(self):
        """c2branch depends on c1branch so can be taken down on its own.
        Current behaviour also takes down the dependency unnecessarily."""
        self._assert_downgrade(
            f"c2branch@{self.b.revision}",
            (self.d1.revision, self.d2.revision),
            [
                self.down_(self.d2),
                self.down_(self.c2),
            ],
            {self.d1.revision},
        )

    def test_downgrade_branch_dependency(self):
        """c2branch depends on c1branch so taking down c1branch requires taking
        down both"""
        destination = f"c1branch@{self.b.revision}"
        source = self.d1.revision, self.d2.revision
        revs = self.env._downgrade_revs(destination, source)
        # Drops c1, d1 as requested, also drops d2 due to dependence on d1.
        # Full ordering of migrations is not consistent so verify partial
        # ordering only.
        rev_ids = [rev.revision.revision for rev in revs]
        assert set(rev_ids) == {
            self.c1.revision,
            self.d1.revision,
            self.d2.revision,
        }
        assert rev_ids.index(self.d1.revision) < rev_ids.index(
            self.c1.revision
        )
        assert rev_ids.index(self.d2.revision) < rev_ids.index(
            self.c1.revision
        )
        # Verify final state.
        heads = set(util.to_tuple(source, default=()))
        head = HeadMaintainer(mock.Mock(), heads)
        for rev in revs:
            head.update_to_step(rev)
        eq_(head.heads, {self.c2.revision})
