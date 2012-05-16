from tests import clear_staging_env, staging_env, eq_, ne_, \
    assert_raises_message
from alembic import util


def setup():
    global env
    env = staging_env()
    global a, b, c, d, e
    a = env.generate_revision(util.rev_id(), None, refresh=True)
    b = env.generate_revision(util.rev_id(), None, refresh=True)
    c = env.generate_revision(util.rev_id(), None, refresh=True)
    d = env.generate_revision(util.rev_id(), None, refresh=True)
    e = env.generate_revision(util.rev_id(), None, refresh=True)

def teardown():
    clear_staging_env()


def test_upgrade_path():

    eq_(
        env._upgrade_revs(e.revision, c.revision),
        [
            (d.module.upgrade, c.revision, d.revision),
            (e.module.upgrade, d.revision, e.revision),
        ]
    )

    eq_(
        env._upgrade_revs(c.revision, None),
        [
            (a.module.upgrade, None, a.revision),
            (b.module.upgrade, a.revision, b.revision),
            (c.module.upgrade, b.revision, c.revision),
        ]
    )

def test_relative_upgrade_path():
    eq_(
        env._upgrade_revs("+2", a.revision),
        [
            (b.module.upgrade, a.revision, b.revision),
            (c.module.upgrade, b.revision, c.revision),
        ]
    )

    eq_(
        env._upgrade_revs("+1", a.revision),
        [
            (b.module.upgrade, a.revision, b.revision),
        ]
    )

    eq_(
        env._upgrade_revs("+3", b.revision),
        [
            (c.module.upgrade, b.revision, c.revision),
            (d.module.upgrade, c.revision, d.revision),
            (e.module.upgrade, d.revision, e.revision),
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
            (e.module.downgrade, e.revision, e.down_revision),
            (d.module.downgrade, d.revision, d.down_revision),
        ]
    )

    eq_(
        env._downgrade_revs(None, c.revision),
        [
            (c.module.downgrade, c.revision, c.down_revision),
            (b.module.downgrade, b.revision, b.down_revision),
            (a.module.downgrade, a.revision, a.down_revision),
        ]
    )

def test_relative_downgrade_path():
    eq_(
        env._downgrade_revs("-1", c.revision),
        [
            (c.module.downgrade, c.revision, c.down_revision),
        ]
    )

    eq_(
        env._downgrade_revs("-3", e.revision),
        [
            (e.module.downgrade, e.revision, e.down_revision),
            (d.module.downgrade, d.revision, d.down_revision),
            (c.module.downgrade, c.revision, c.down_revision),
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
