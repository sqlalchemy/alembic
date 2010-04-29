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
        list(env.upgrade_from(c.upgrade)),
        [
            (d.module.upgrade, d.upgrade),
            (e.module.upgrade, e.upgrade),
        ]
    )
    