from alembic.testing.env import clear_staging_env, staging_env
from alembic.testing import assert_raises_message, eq_
from alembic import util
from alembic.testing.fixtures import TestBase

from alembic.migration import MigrationStep
up_ = MigrationStep.upgrade_from_script
down_ = MigrationStep.downgrade_from_script


class RevisionPathTest(TestBase):

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
                up_(d),
                up_(e)
            ]
        )

        eq_(
            self.env._upgrade_revs(c.revision, None),
            [
                up_(a, True),
                up_(b),
                up_(c),
            ]
        )

    def test_relative_upgrade_path(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e
        eq_(
            self.env._upgrade_revs("+2", a.revision),
            [
                up_(b),
                up_(c),
            ]
        )

        eq_(
            self.env._upgrade_revs("+1", a.revision),
            [
                up_(b)
            ]
        )

        eq_(
            self.env._upgrade_revs("+3", b.revision),
            [up_(c), up_(d), up_(e)]
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
            [down_(e), down_(d)]
        )

        eq_(
            self.env._downgrade_revs(None, c.revision),
            [down_(c), down_(b), down_(a, True)]
        )

    def test_relative_downgrade_path(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e
        eq_(
            self.env._downgrade_revs("-1", c.revision),
            [down_(c)]
        )

        eq_(
            self.env._downgrade_revs("-3", e.revision),
            [down_(e), down_(d), down_(c)]
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
            r"Revision\(s\) %s is not an ancestor "
            "of revision\(s\) base" % b.revision,
            self.env._downgrade_revs, b.revision[0:3], None
        )

    def test_invalid_move_higher_to_lower(self):
        a, b, c, d, e = self.a, self.b, self.c, self.d, self.e

        assert_raises_message(
            util.CommandError,
            r"Revision\(s\) %s is not an ancestor "
            "of revision\(s\) %s" % (c.revision, b.revision),
            self.env._downgrade_revs, c.revision[0:4], b.revision
        )


class BranchedPathTest(TestBase):

    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a = env.generate_revision(util.rev_id(), '->a', refresh=True)
        cls.b = env.generate_revision(util.rev_id(), 'a->b', refresh=True)

        cls.c1 = env.generate_revision(util.rev_id(), 'b->c1', refresh=True)
        cls.d1 = env.generate_revision(util.rev_id(), 'c1->d1', refresh=True)

        cls.c2 = env.generate_revision(
            util.rev_id(), 'b->c2',
            head=cls.b.revision, refresh=True)
        cls.d2 = env.generate_revision(
            util.rev_id(), 'c2->d2',
            head=cls.c2.revision, refresh=True)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_upgrade_single_branch(self):
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )

        eq_(
            self.env._upgrade_revs(d1.revision, b.revision),
            [up_(c1), up_(d1)]
        )

    def test_upgrade_multiple_branch(self):
        # move from a single head to multiple heads
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )

        eq_(
            self.env._upgrade_revs((d1.revision, d2.revision), a.revision),
            [up_(b), up_(c2), up_(d2), up_(c1, True), up_(d1)]
        )

    def test_downgrade_multiple_branch(self):
        a, b, c1, d1, c2, d2 = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2
        )
        eq_(
            self.env._downgrade_revs(a.revision, (d1.revision, d2.revision)),
            [down_(d1), down_(c1), down_(d2), down_(c2, True), down_(b)]
        )


class ForestTest(TestBase):
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

    def test_base_to_head(self):
        a1, b1, a2, b2 = self.a1, self.b1, self.a2, self.b2
        eq_(
            self.env._upgrade_revs("head", "base"),
            [up_(a2, True), up_(b2), up_(a1, True), up_(b1), ]
        )


class MergedPathTest(TestBase):

    @classmethod
    def setup_class(cls):
        cls.env = env = staging_env()
        cls.a = env.generate_revision(util.rev_id(), '->a', refresh=True)
        cls.b = env.generate_revision(util.rev_id(), 'a->b', refresh=True)

        cls.c1 = env.generate_revision(util.rev_id(), 'b->c1', refresh=True)
        cls.d1 = env.generate_revision(util.rev_id(), 'c1->d1', refresh=True)

        cls.c2 = env.generate_revision(
            util.rev_id(), 'b->c2',
            head=cls.b.revision, refresh=True)
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

    def test_upgrade_across_merge_point(self):
        a, b, c1, d1, c2, d2, e, f = (
            self.a, self.b, self.c1, self.d1, self.c2, self.d2,
            self.e, self.f
        )

        eq_(
            self.env._upgrade_revs(f.revision, b.revision),
            [
                up_(c2),
                up_(d2),
                up_(c1, True),  # b->c1, create new branch
                up_(d1),
                up_(e),  # d1/d2 -> e, merge branches
                         # (DELETE d2, UPDATE d1->e)
                up_(f)
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
                down_(f),
                down_(e),  # e -> d1 and d2, unmerge branches
                           # (UPDATE e->d1, INSERT d2)
                down_(d1),
                down_(c1),
                down_(d2),
                down_(c2, True),  # c2->b, delete branch
            ]
        )
