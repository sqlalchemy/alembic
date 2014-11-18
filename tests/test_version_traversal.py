from alembic.testing.env import clear_staging_env, staging_env
from alembic.testing import assert_raises_message, eq_
from alembic import util
from alembic.testing.fixtures import TestBase

from alembic.migration import MigrationStep


class MigrationTest(TestBase):
    def up_(self, rev):
        return MigrationStep.upgrade_from_script(
            self.env.revision_map, rev)

    def down_(self, rev):
        return MigrationStep.downgrade_from_script(
            self.env.revision_map, rev)


class RevisionPathTest(MigrationTest):

    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a = env.generate_revision(util.rev_id(), '->a', refresh=True)
        cls.b = env.generate_revision(util.rev_id(), 'a->b', refresh=True)
        cls.c = env.generate_revision(util.rev_id(), 'b->c', refresh=True)
        cls.d = env.generate_revision(util.rev_id(), 'c->d', refresh=True)
        cls.e = env.generate_revision(util.rev_id(), 'd->e', refresh=True)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_upgrade_path(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e
        eq_(
            self.env._upgrade_revs(e.revision, c.revision),
            [
                self.up_(d),
                self.up_(e)
            ]
        )

        eq_(
            self.env._upgrade_revs(c.revision, None),
            [
                self.up_(a),
                self.up_(b),
                self.up_(c),
            ]
        )

    def test_relative_upgrade_path(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e
        eq_(
            self.env._upgrade_revs("+2", a.revision),
            [
                self.up_(b),
                self.up_(c),
            ]
        )

        eq_(
            self.env._upgrade_revs("+1", a.revision),
            [
                self.up_(b)
            ]
        )

        eq_(
            self.env._upgrade_revs("+3", b.revision),
            [self.up_(c), self.up_(d), self.up_(e)]
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

        eq_(
            self.env._downgrade_revs(c.revision, e.revision),
            [self.down_(e), self.down_(d)]
        )

        eq_(
            self.env._downgrade_revs(None, c.revision),
            [self.down_(c), self.down_(b), self.down_(a)]
        )

    def test_relative_downgrade_path(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e
        eq_(
            self.env._downgrade_revs("-1", c.revision),
            [self.down_(c)]
        )

        eq_(
            self.env._downgrade_revs("-3", e.revision),
            [self.down_(e), self.down_(d), self.down_(c)]
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
        cls.a = env.generate_revision(util.rev_id(), '->a', refresh=True)
        cls.b = env.generate_revision(util.rev_id(), 'a->b', refresh=True)

        cls.c1 = env.generate_revision(
            util.rev_id(), 'b->c1',
            branch_names='c1branch',
            refresh=True)
        cls.d1 = env.generate_revision(util.rev_id(), 'c1->d1', refresh=True)

        cls.c2 = env.generate_revision(
            util.rev_id(), 'b->c2',
            branch_names='c2branch',
            head=cls.b.revision, refresh=True, splice=True)
        cls.d2 = env.generate_revision(
            util.rev_id(), 'c2->d2',
            head=cls.c2.revision, refresh=True)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_stamp_down_across_multiple_branch_to_branchpoint(self):
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )
        revs = self.env._stamp_revs(
            self.b.revision, [self.d1.revision, self.c2.revision])
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents,
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
        revs = self.env._stamp_revs(
            "c2branch@head", [self.d1.revision, self.c2.revision])
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents,
            # the c1branch remains unchanged
            ([], self.c2.revision, self.d2.revision)
        )

    def test_upgrade_single_branch(self):
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )

        eq_(
            self.env._upgrade_revs(d1.revision, b.revision),
            [self.up_(c1), self.up_(d1)]
        )

    def test_upgrade_multiple_branch(self):
        # move from a single head to multiple heads
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )

        eq_(
            self.env._upgrade_revs((d1.revision, d2.revision), a.revision),
            [self.up_(b), self.up_(c2), self.up_(d2), self.up_(c1), self.up_(d1)]
        )

    def test_downgrade_multiple_branch(self):
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )
        eq_(
            self.env._downgrade_revs(a.revision, (d1.revision, d2.revision)),
            [self.down_(d1), self.down_(c1), self.down_(d2), self.down_(c2), self.down_(b)]
        )


class ForestTest(MigrationTest):
    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a1 = env.generate_revision(util.rev_id(), '->a1', refresh=True)
        cls.b1 = env.generate_revision(util.rev_id(), 'a1->b1', refresh=True)

        cls.a2 = env.generate_revision(
            util.rev_id(), '->a2', head=(),
            refresh=True)
        cls.b2 = env.generate_revision(
            util.rev_id(), 'a2->b2', head=cls.a2.revision, refresh=True)

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
        cls.a = env.generate_revision(util.rev_id(), '->a', refresh=True)
        cls.b = env.generate_revision(util.rev_id(), 'a->b', refresh=True)

        cls.c1 = env.generate_revision(util.rev_id(), 'b->c1', refresh=True)
        cls.d1 = env.generate_revision(util.rev_id(), 'c1->d1', refresh=True)

        cls.c2 = env.generate_revision(
            util.rev_id(), 'b->c2',
            branch_names='c2branch',
            head=cls.b.revision, refresh=True, splice=True)
        cls.d2 = env.generate_revision(
            util.rev_id(), 'c2->d2',
            head=cls.c2.revision, refresh=True)

        cls.e = env.generate_revision(
            util.rev_id(), 'merge d1 and d2',
            head=(cls.d1.revision, cls.d2.revision), refresh=True
        )

        cls.f = env.generate_revision(util.rev_id(), 'e->f', refresh=True)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_stamp_down_across_merge_point_branch(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )
        revs = self.env._stamp_revs(self.c2.revision, [self.e.revision])
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents,
            # no deletes, UPDATE e to c2
            ([], self.e.revision, self.c2.revision)
        )

    def test_stamp_down_across_merge_prior_branching(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )
        revs = self.env._stamp_revs(self.a.revision, [self.e.revision])
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents,
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
            revs[0].merge_branch_idents,
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
            revs[0].merge_branch_idents,
            # DELETE d1 revision, UPDATE c2 to e
            ([self.d1.revision], self.c2.revision, self.f.revision)
        )

    def test_stamp_up_across_merge_from_multiple_branch(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )
        revs = self.env._stamp_revs(
            self.e.revision, [self.d1.revision, self.c2.revision])
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents,
            # DELETE d1 revision, UPDATE c2 to e
            ([self.d1.revision], self.c2.revision, self.e.revision)
        )

    def test_stamp_up_across_merge_prior_branching(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )
        revs = self.env._stamp_revs(self.e.revision, [self.b.revision])
        eq_(len(revs), 1)
        eq_(
            revs[0].merge_branch_idents,
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
