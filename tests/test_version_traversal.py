from alembic.testing.env import clear_staging_env, staging_env
from alembic.testing import assert_raises_message, eq_
from alembic import util
from alembic.testing.fixtures import TestBase
from alembic.testing import mock
from alembic.migration import MigrationStep, HeadMaintainer


class MigrationTest(TestBase):
    def up_(self, rev):
        return MigrationStep.upgrade_from_script(
            self.env.revision_map, rev)

    def down_(self, rev):
        return MigrationStep.downgrade_from_script(
            self.env.revision_map, rev)

    def _assert_downgrade(self, destination, source, expected, expected_heads):
        revs = self.env._downgrade_revs(destination, source)
        eq_(
            revs, expected
        )
        heads = set(util.to_tuple(source, default=()))
        head = HeadMaintainer(mock.Mock(), heads)
        for rev in revs:
            head.update_to_step(rev)
        eq_(head.heads, expected_heads)

    def _assert_upgrade(self, destination, source, expected, expected_heads):
        revs = self.env._upgrade_revs(destination, source)
        eq_(
            revs, expected
        )
        heads = set(util.to_tuple(source, default=()))
        head = HeadMaintainer(mock.Mock(), heads)
        for rev in revs:
            head.update_to_step(rev)
        eq_(head.heads, expected_heads)


class RevisionPathTest(MigrationTest):

    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a = env.generate_revision(util.rev_id(), '->a')
        cls.b = env.generate_revision(util.rev_id(), 'a->b')
        cls.c = env.generate_revision(util.rev_id(), 'b->c')
        cls.d = env.generate_revision(util.rev_id(), 'c->d')
        cls.e = env.generate_revision(util.rev_id(), 'd->e')

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_upgrade_path(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e
        self._assert_upgrade(
            e.revision, c.revision,
            [
                self.up_(d),
                self.up_(e)
            ],
            set([e.revision])
        )

        self._assert_upgrade(
            c.revision, None,
            [
                self.up_(a),
                self.up_(b),
                self.up_(c),
            ],
            set([c.revision])
        )

    def test_relative_upgrade_path(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e
        self._assert_upgrade(
            "+2", a.revision,
            [
                self.up_(b),
                self.up_(c),
            ],
            set([c.revision])
        )

        self._assert_upgrade(
            "+1", a.revision,
            [
                self.up_(b)
            ],
            set([b.revision])
        )

        self._assert_upgrade(
            "+3", b.revision,
            [self.up_(c), self.up_(d), self.up_(e)],
            set([e.revision])
        )

    def test_invalid_relative_upgrade_path(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e
        assert_raises_message(
            util.CommandError,
            "Relative revision -2 didn't produce 2 migrations",
            self.env._upgrade_revs, "-2", b.revision
        )

        assert_raises_message(
            util.CommandError,
            r"Relative revision \+5 didn't produce 5 migrations",
            self.env._upgrade_revs, "+5", b.revision
        )

    def test_downgrade_path(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e

        self._assert_downgrade(
            c.revision, e.revision,
            [self.down_(e), self.down_(d)],
            set([c.revision])
        )

        self._assert_downgrade(
            None, c.revision,
            [self.down_(c), self.down_(b), self.down_(a)],
            set()
        )

    def test_relative_downgrade_path(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e
        self._assert_downgrade(
            "-1", c.revision,
            [self.down_(c)],
            set([b.revision])
        )

        self._assert_downgrade(
            "-3", e.revision,
            [self.down_(e), self.down_(d), self.down_(c)],
            set([b.revision])
        )

    def test_invalid_relative_downgrade_path(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e
        assert_raises_message(
            util.CommandError,
            "Relative revision -5 didn't produce 5 migrations",
            self.env._downgrade_revs, "-5", b.revision
        )

        assert_raises_message(
            util.CommandError,
            r"Relative revision \+2 didn't produce 2 migrations",
            self.env._downgrade_revs, "+2", b.revision
        )

    def test_invalid_move_rev_to_none(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e
        assert_raises_message(
            util.CommandError,
            r"Destination %s is not a valid downgrade "
            "target from current head\(s\)" % b.revision[0:3],
            self.env._downgrade_revs, b.revision[0:3], None
        )

    def test_invalid_move_higher_to_lower(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e

        assert_raises_message(
            util.CommandError,
            r"Destination %s is not a valid downgrade "
            "target from current head\(s\)" % c.revision[0:4],
            self.env._downgrade_revs, c.revision[0:4], b.revision
        )


class BranchedPathTest(MigrationTest):

    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a = env.generate_revision(util.rev_id(), '->a')
        cls.b = env.generate_revision(util.rev_id(), 'a->b')

        cls.c1 = env.generate_revision(
            util.rev_id(), 'b->c1',
            branch_labels='c1branch',
            refresh=True)
        cls.d1 = env.generate_revision(util.rev_id(), 'c1->d1')

        cls.c2 = env.generate_revision(
            util.rev_id(), 'b->c2',
            branch_labels='c2branch',
            head=cls.b.revision, splice=True)
        cls.d2 = env.generate_revision(
            util.rev_id(), 'c2->d2',
            head=cls.c2.revision)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_stamp_down_across_multiple_branch_to_branchpoint(self):
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )
        heads = [self.d1.revision, self.c2.revision]
        revs = self.env._stamp_revs(
            self.b.revision, heads)
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents(heads),
            # DELETE d1 revision, UPDATE c2 to b
            ([self.d1.revision], self.c2.revision, self.b.revision)
        )

    def test_stamp_to_labeled_base_multiple_heads(self):
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )
        revs = self.env._stamp_revs(
            "c1branch@base", [self.d1.revision, self.c2.revision])
        eq_(len(revs), 1)
        assert revs[0].should_delete_branch
        eq_(revs[0].delete_version_num, self.d1.revision)

    def test_stamp_to_labeled_head_multiple_heads(self):
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )
        heads = [self.d1.revision, self.c2.revision]
        revs = self.env._stamp_revs(
            "c2branch@head", heads)
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents(heads),
            # the c1branch remains unchanged
            ([], self.c2.revision, self.d2.revision)
        )

    def test_upgrade_single_branch(self):
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )

        self._assert_upgrade(
            d1.revision, b.revision,
            [self.up_(c1), self.up_(d1)],
            set([d1.revision])
        )

    def test_upgrade_multiple_branch(self):
        # move from a single head to multiple heads
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )

        self._assert_upgrade(
            (d1.revision, d2.revision), a.revision,
            [self.up_(b), self.up_(c2), self.up_(d2),
             self.up_(c1), self.up_(d1)],
            set([d1.revision, d2.revision])
        )

    def test_downgrade_multiple_branch(self):
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )
        self._assert_downgrade(
            a.revision, (d1.revision, d2.revision),
            [self.down_(d1), self.down_(c1), self.down_(d2),
             self.down_(c2), self.down_(b)],
            set([a.revision])
        )


class BranchFromMergepointTest(MigrationTest):
    """this is a form that will come up frequently in the
    "many independent roots with cross-dependencies" case.

    """

    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision(util.rev_id(), '->a1')
        cls.b1 = env.generate_revision(util.rev_id(), 'a1->b1')
        cls.c1 = env.generate_revision(util.rev_id(), 'b1->c1')

        cls.a2 = env.generate_revision(
            util.rev_id(), '->a2', head=(),
            refresh=True)
        cls.b2 = env.generate_revision(
            util.rev_id(), 'a2->b2', head=cls.a2.revision)
        cls.c2 = env.generate_revision(
            util.rev_id(), 'b2->c2', head=cls.b2.revision)

        # mergepoint between c1, c2
        # d1 dependent on c2
        cls.d1 = env.generate_revision(
            util.rev_id(), 'd1', head=(cls.c1.revision, cls.c2.revision),
            refresh=True)

        # but then c2 keeps going into d2
        cls.d2 = env.generate_revision(
            util.rev_id(), 'd2', head=cls.c2.revision,
            refresh=True, splice=True)

    def test_mergepoint_to_only_one_side_upgrade(self):
        a1, b1, c1, a2, b2, c2, d1, d2 = (
            self.a1, self.b1, self.c1, self.a2, self.b2, self.c2,
            self.d1, self.d2
        )

        self._assert_upgrade(
            d1.revision, (d2.revision, b1.revision),
            [self.up_(c1), self.up_(d1)],
            set([d2.revision, d1.revision])
        )

    def test_mergepoint_to_only_one_side_downgrade(self):
        a1, b1, c1, a2, b2, c2, d1, d2 = (
            self.a1, self.b1, self.c1, self.a2, self.b2, self.c2,
            self.d1, self.d2
        )

        self._assert_downgrade(
            b1.revision, (d2.revision, d1.revision),
            [self.down_(d1), self.down_(c1)],
            set([d2.revision, b1.revision])
        )


class BranchFrom3WayMergepointTest(MigrationTest):
    """this is a form that will come up frequently in the
    "many independent roots with cross-dependencies" case.

    """

    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision(util.rev_id(), '->a1')
        cls.b1 = env.generate_revision(util.rev_id(), 'a1->b1')
        cls.c1 = env.generate_revision(util.rev_id(), 'b1->c1')

        cls.a2 = env.generate_revision(
            util.rev_id(), '->a2', head=(),
            refresh=True)
        cls.b2 = env.generate_revision(
            util.rev_id(), 'a2->b2', head=cls.a2.revision)
        cls.c2 = env.generate_revision(
            util.rev_id(), 'b2->c2', head=cls.b2.revision)

        cls.a3 = env.generate_revision(
            util.rev_id(), '->a3', head=(),
            refresh=True)
        cls.b3 = env.generate_revision(
            util.rev_id(), 'a3->b3', head=cls.a3.revision)
        cls.c3 = env.generate_revision(
            util.rev_id(), 'b3->c3', head=cls.b3.revision)

        # mergepoint between c1, c2, c3
        # d1 dependent on c2, c3
        cls.d1 = env.generate_revision(
            util.rev_id(), 'd1', head=(
                cls.c1.revision, cls.c2.revision, cls.c3.revision),
            refresh=True)

        # but then c2 keeps going into d2
        cls.d2 = env.generate_revision(
            util.rev_id(), 'd2', head=cls.c2.revision,
            refresh=True, splice=True)

        # c3 keeps going into d3
        cls.d3 = env.generate_revision(
            util.rev_id(), 'd3', head=cls.c3.revision,
            refresh=True, splice=True)

    def test_mergepoint_to_only_one_side_upgrade(self):
        a1, b1, c1, a2, b2, c2, d1, d2, a3, b3, c3, d3 = (
            self.a1, self.b1, self.c1, self.a2, self.b2, self.c2,
            self.d1, self.d2, self.a3, self.b3, self.c3, self.d3
        )

        self._assert_upgrade(
            d1.revision, (d3.revision, d2.revision, b1.revision),
            [self.up_(c1), self.up_(d1)],
            set([d3.revision, d2.revision, d1.revision])
        )

    def test_mergepoint_to_only_one_side_downgrade(self):
        a1, b1, c1, a2, b2, c2, d1, d2, a3, b3, c3, d3 = (
            self.a1, self.b1, self.c1, self.a2, self.b2, self.c2,
            self.d1, self.d2, self.a3, self.b3, self.c3, self.d3
        )

        self._assert_downgrade(
            b1.revision, (d3.revision, d2.revision, d1.revision),
            [self.down_(d1), self.down_(c1)],
            set([d3.revision, d2.revision, b1.revision])
        )

    def test_mergepoint_to_two_sides_upgrade(self):
        a1, b1, c1, a2, b2, c2, d1, d2, a3, b3, c3, d3 = (
            self.a1, self.b1, self.c1, self.a2, self.b2, self.c2,
            self.d1, self.d2, self.a3, self.b3, self.c3, self.d3
        )

        self._assert_upgrade(
            d1.revision, (d3.revision, b2.revision, b1.revision),
            [self.up_(c2), self.up_(c1), self.up_(d1)],
            # this will merge b2 and b1 into d1
            set([d3.revision, d1.revision])
        )

        # but then!  b2 will break out again if we keep going with it
        self._assert_upgrade(
            d2.revision, (d3.revision, d1.revision),
            [self.up_(d2)],
            set([d3.revision, d2.revision, d1.revision])
        )


class DependsOnBranchTestOne(MigrationTest):
    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision(
            util.rev_id(), '->a1',
            branch_labels=['lib1'])
        cls.b1 = env.generate_revision(util.rev_id(), 'a1->b1')
        cls.c1 = env.generate_revision(util.rev_id(), 'b1->c1')

        cls.a2 = env.generate_revision(util.rev_id(), '->a2', head=())
        cls.b2 = env.generate_revision(
            util.rev_id(), 'a2->b2', head=cls.a2.revision)
        cls.c2 = env.generate_revision(
            util.rev_id(), 'b2->c2', head=cls.b2.revision,
            depends_on=cls.c1.revision)

        cls.d1 = env.generate_revision(
            util.rev_id(), 'c1->d1',
            head=cls.c1.revision)
        cls.e1 = env.generate_revision(
            util.rev_id(), 'd1->e1',
            head=cls.d1.revision)
        cls.f1 = env.generate_revision(
            util.rev_id(), 'e1->f1',
            head=cls.e1.revision)

    def test_downgrade_to_dependency(self):
        heads = [self.c2.revision, self.d1.revision]
        head = HeadMaintainer(mock.Mock(), heads)
        head.update_to_step(self.down_(self.d1))
        eq_(head.heads, set([self.c2.revision]))


class DependsOnBranchTestTwo(MigrationTest):
    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision(util.rev_id(), '->a1', head='base')
        cls.a2 = env.generate_revision(util.rev_id(), '->a2', head='base')
        cls.a3 = env.generate_revision(util.rev_id(), '->a3', head='base')
        cls.amerge = env.generate_revision(util.rev_id(), 'amerge', head=[
            cls.a1.revision, cls.a2.revision, cls.a3.revision
        ])

        cls.b1 = env.generate_revision(util.rev_id(), '->b1', head='base')
        cls.b2 = env.generate_revision(util.rev_id(), '->b2', head='base')
        cls.bmerge = env.generate_revision(util.rev_id(), 'bmerge', head=[
            cls.b1.revision, cls.b2.revision
        ])

        cls.c1 = env.generate_revision(util.rev_id(), '->c1', head='base')
        cls.c2 = env.generate_revision(util.rev_id(), '->c2', head='base')
        cls.c3 = env.generate_revision(util.rev_id(), '->c3', head='base')
        cls.cmerge = env.generate_revision(util.rev_id(), 'cmerge', head=[
            cls.c1.revision, cls.c2.revision, cls.c3.revision
        ])

        cls.d1 = env.generate_revision(
            util.rev_id(), 'overmerge',
            head="base",
            depends_on=[
                cls.a3.revision, cls.b2.revision, cls.c1.revision
            ])

    def test_kaboom(self):
        # here's the upgrade path:
        # ['->c1', '->b2', '->a3', 'overmerge', '->c3', '->c2', 'cmerge',
        # '->b1', 'bmerge', '->a2', '->a1', 'amerge'],

        heads = [
            self.amerge.revision,
            self.bmerge.revision, self.cmerge.revision,
            self.d1.revision
        ]

        self._assert_downgrade(
            self.b2.revision, heads,
            [self.down_(self.bmerge), self.down_(self.d1)],
            set([
                self.amerge.revision, self.b2.revision,
                self.b1.revision, self.cmerge.revision])
        )

        heads = [
            self.amerge.revision, self.b2.revision,
            self.b1.revision, self.cmerge.revision]
        self._assert_downgrade(
            "base", heads,
            [
                self.down_(self.amerge), self.down_(self.a1),
                self.down_(self.a2), self.down_(self.a3),
                self.down_(self.b2), self.down_(self.b1),
                self.down_(self.cmerge), self.down_(self.c1),
                self.down_(self.c2), self.down_(self.c3)
            ],
            set([])
        )


class ForestTest(MigrationTest):
    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision(util.rev_id(), '->a1')
        cls.b1 = env.generate_revision(util.rev_id(), 'a1->b1')

        cls.a2 = env.generate_revision(
            util.rev_id(), '->a2', head=(),
            refresh=True)
        cls.b2 = env.generate_revision(
            util.rev_id(), 'a2->b2', head=cls.a2.revision)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_base_to_heads(self):
        a1, b1, a2, b2 = self.a1, self.b1, self.a2, self.b2
        eq_(
            self.env._upgrade_revs("heads", "base"),
            [self.up_(a2), self.up_(b2), self.up_(a1), self.up_(b1), ]
        )


class MergedPathTest(MigrationTest):

    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a = env.generate_revision(util.rev_id(), '->a')
        cls.b = env.generate_revision(util.rev_id(), 'a->b')

        cls.c1 = env.generate_revision(util.rev_id(), 'b->c1')
        cls.d1 = env.generate_revision(util.rev_id(), 'c1->d1')

        cls.c2 = env.generate_revision(
            util.rev_id(), 'b->c2',
            branch_labels='c2branch',
            head=cls.b.revision, splice=True)
        cls.d2 = env.generate_revision(
            util.rev_id(), 'c2->d2',
            head=cls.c2.revision)

        cls.e = env.generate_revision(
            util.rev_id(), 'merge d1 and d2',
            head=(cls.d1.revision, cls.d2.revision)
        )

        cls.f = env.generate_revision(util.rev_id(), 'e->f')

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_stamp_down_across_merge_point_branch(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )
        heads = [self.e.revision]
        revs = self.env._stamp_revs(self.c2.revision, heads)
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents(heads),
            # no deletes, UPDATE e to c2
            ([], self.e.revision, self.c2.revision)
        )

    def test_stamp_down_across_merge_prior_branching(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )
        heads = [self.e.revision]
        revs = self.env._stamp_revs(self.a.revision, heads)
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents(heads),
            # no deletes, UPDATE e to c2
            ([], self.e.revision, self.a.revision)
        )

    def test_stamp_up_across_merge_from_single_branch(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )
        revs = self.env._stamp_revs(self.e.revision, [self.c2.revision])
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents([self.c2.revision]),
            # no deletes, UPDATE e to c2
            ([], self.c2.revision, self.e.revision)
        )

    def test_stamp_labled_head_across_merge_from_multiple_branch(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )
        # this is testing that filter_for_lineage() checks for
        # d1 both in terms of "c2branch" as well as that the "head"
        # revision "f" is the head of both d1 and d2
        revs = self.env._stamp_revs(
            "c2branch@head", [self.d1.revision, self.c2.revision])
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents([self.d1.revision, self.c2.revision]),
            # DELETE d1 revision, UPDATE c2 to e
            ([self.d1.revision], self.c2.revision, self.f.revision)
        )

    def test_stamp_up_across_merge_from_multiple_branch(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )
        heads = [self.d1.revision, self.c2.revision]
        revs = self.env._stamp_revs(
            self.e.revision, heads)
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents(heads),
            # DELETE d1 revision, UPDATE c2 to e
            ([self.d1.revision], self.c2.revision, self.e.revision)
        )

    def test_stamp_up_across_merge_prior_branching(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )
        heads = [self.b.revision]
        revs = self.env._stamp_revs(self.e.revision, heads)
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents(heads),
            # no deletes, UPDATE e to c2
            ([], self.b.revision, self.e.revision)
        )

    def test_upgrade_across_merge_point(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )

        eq_(
            self.env._upgrade_revs(f.revision, b.revision),
            [
                self.up_(c2),
                self.up_(d2),
                self.up_(c1),  # b->c1, create new branch
                self.up_(d1),
                self.up_(e),  # d1/d2 -> e, merge branches
                              # (DELETE d2, UPDATE d1->e)
                self.up_(f)
            ]
        )

    def test_downgrade_across_merge_point(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )

        eq_(
            self.env._downgrade_revs(b.revision, f.revision),
            [
                self.down_(f),
                self.down_(e),  # e -> d1 and d2, unmerge branches
                                # (UPDATE e->d1, INSERT d2)
                self.down_(d1),
                self.down_(c1),
                self.down_(d2),
                self.down_(c2),  # c2->b, delete branch
            ]
        )
