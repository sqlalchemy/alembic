from tests import clear_staging_env, staging_env, eq_, ne_
from alembic import util


def setup():
    global env
    env = staging_env()
    global a, b, c, d, e
    a = env.generate_rev(util.rev_id(), None)
    b = env.generate_rev(util.rev_id(), None)
    c = env.generate_rev(util.rev_id(), None)
    d = env.generate_rev(util.rev_id(), None)
    e = env.generate_rev(util.rev_id(), None)

def teardown():
    clear_staging_env()


def test_upgrade_path():

    eq_(
        env.upgrade_from(False, e.revision, c.revision),
        [
            (d.module.upgrade, d.revision),
            (e.module.upgrade, e.revision),
        ]
    )

    eq_(
        env.upgrade_from(False, c.revision, None),
        [
            (a.module.upgrade, a.revision),
            (b.module.upgrade, b.revision),
            (c.module.upgrade, c.revision),
        ]
    )

def test_downgrade_path():

    eq_(
        env.downgrade_to(False, c.revision, e.revision),
        [
            (e.module.downgrade, e.down_revision),
            (d.module.downgrade, d.down_revision),
        ]
    )

    eq_(
        env.downgrade_to(False, None, c.revision),
        [
            (c.module.downgrade, c.down_revision),
            (b.module.downgrade, b.down_revision),
            (a.module.downgrade, a.down_revision),
        ]
    )
