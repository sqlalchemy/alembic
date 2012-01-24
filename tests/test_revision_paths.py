from tests import clear_staging_env, staging_env, eq_, ne_
from alembic import util


def setup():
    global env
    env = staging_env()
    global a, b, c, d, e
    a = env.generate_rev(util.rev_id(), None, refresh=True)
    b = env.generate_rev(util.rev_id(), None, refresh=True)
    c = env.generate_rev(util.rev_id(), None, refresh=True)
    d = env.generate_rev(util.rev_id(), None, refresh=True)
    e = env.generate_rev(util.rev_id(), None, refresh=True)

def teardown():
    clear_staging_env()


def test_upgrade_path():

    eq_(
        env.upgrade_from(e.revision, c.revision, None),
        [
            (d.module.upgrade, c.revision, d.revision),
            (e.module.upgrade, d.revision, e.revision),
        ]
    )

    eq_(
        env.upgrade_from(c.revision, None, None),
        [
            (a.module.upgrade, None, a.revision),
            (b.module.upgrade, a.revision, b.revision),
            (c.module.upgrade, b.revision, c.revision),
        ]
    )

def test_downgrade_path():

    eq_(
        env.downgrade_to(c.revision, e.revision, None),
        [
            (e.module.downgrade, e.revision, e.down_revision),
            (d.module.downgrade, d.revision, d.down_revision),
        ]
    )

    eq_(
        env.downgrade_to(None, c.revision, None),
        [
            (c.module.downgrade, c.revision, c.down_revision),
            (b.module.downgrade, b.revision, b.down_revision),
            (a.module.downgrade, a.revision, a.down_revision),
        ]
    )
