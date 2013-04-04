from tests import clear_staging_env, staging_env, eq_, \
    assert_raises_message
from alembic import util

env = None
a, b, c, d, e = None, None, None, None, None
cfg = None

def setup():
    global env
    env = staging_env()
    global a, b, c, d, e
    a = env.generate_revision(util.rev_id(), '->a', refresh=True)
    b = env.generate_revision(util.rev_id(), 'a->b', refresh=True)
    c = env.generate_revision(util.rev_id(), 'b->c', refresh=True)
    d = env.generate_revision(util.rev_id(), 'c->d', refresh=True)
    e = env.generate_revision(util.rev_id(), 'd->e', refresh=True)

def teardown():
    clear_staging_env()


def test_upgrade_path():

    eq_(
        env._upgrade_revs(e.revision, c.revision),
        [
            (d.module.upgrade, c.revision, d.revision, d.doc),
            (e.module.upgrade, d.revision, e.revision, e.doc),
        ]
    )

    eq_(
        env._upgrade_revs(c.revision, None),
        [
            (a.module.upgrade, None, a.revision, a.doc),
            (b.module.upgrade, a.revision, b.revision, b.doc),
            (c.module.upgrade, b.revision, c.revision, c.doc),
        ]
    )

def test_relative_upgrade_path():
    eq_(
        env._upgrade_revs("+2", a.revision),
        [
            (b.module.upgrade, a.revision, b.revision, b.doc),
            (c.module.upgrade, b.revision, c.revision, c.doc),
        ]
    )

    eq_(
        env._upgrade_revs("+1", a.revision),
        [
            (b.module.upgrade, a.revision, b.revision, b.doc),
        ]
    )

    eq_(
        env._upgrade_revs("+3", b.revision),
        [
            (c.module.upgrade, b.revision, c.revision, c.doc),
            (d.module.upgrade, c.revision, d.revision, d.doc),
            (e.module.upgrade, d.revision, e.revision, e.doc),
        ]
    )

def test_invalid_relative_upgrade_path():
    assert_raises_message(
        util.CommandError,
        "Relative revision -2 didn't produce 2 migrations",
        env._upgrade_revs, "-2", b.revision
    )

    assert_raises_message(
        util.CommandError,
        r"Relative revision \+5 didn't produce 5 migrations",
        env._upgrade_revs, "+5", b.revision
    )

def test_downgrade_path():

    eq_(
        env._downgrade_revs(c.revision, e.revision),
        [
            (e.module.downgrade, e.revision, e.down_revision, e.doc),
            (d.module.downgrade, d.revision, d.down_revision, d.doc),
        ]
    )

    eq_(
        env._downgrade_revs(None, c.revision),
        [
            (c.module.downgrade, c.revision, c.down_revision, c.doc),
            (b.module.downgrade, b.revision, b.down_revision, b.doc),
            (a.module.downgrade, a.revision, a.down_revision, a.doc),
        ]
    )

def test_relative_downgrade_path():
    eq_(
        env._downgrade_revs("-1", c.revision),
        [
            (c.module.downgrade, c.revision, c.down_revision, c.doc),
        ]
    )

    eq_(
        env._downgrade_revs("-3", e.revision),
        [
            (e.module.downgrade, e.revision, e.down_revision, e.doc),
            (d.module.downgrade, d.revision, d.down_revision, d.doc),
            (c.module.downgrade, c.revision, c.down_revision, c.doc),
        ]
    )

def test_invalid_relative_downgrade_path():
    assert_raises_message(
        util.CommandError,
        "Relative revision -5 didn't produce 5 migrations",
        env._downgrade_revs, "-5", b.revision
    )

    assert_raises_message(
        util.CommandError,
        r"Relative revision \+2 didn't produce 2 migrations",
        env._downgrade_revs, "+2", b.revision
    )

def test_invalid_move_rev_to_none():
    assert_raises_message(
        util.CommandError,
        "Revision %s is not an ancestor of base" % b.revision,
        env._downgrade_revs, b.revision[0:3], None
    )

def test_invalid_move_higher_to_lower():
    assert_raises_message(
       util.CommandError,
        "Revision %s is not an ancestor of %s" % (c.revision, b.revision),
        env._downgrade_revs, c.revision[0:4], b.revision
    )

