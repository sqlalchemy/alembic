from tests import clear_staging_env, staging_env, eq_, ne_
from alembic import util
import os

def test_001_environment():
    assert_set = set(['env.py', 'script.py.mako', 'README'])
    eq_(
        assert_set.intersection(os.listdir(env.dir)),
        assert_set
    )

def test_002_rev_ids():
    global abc, def_
    abc = util.rev_id()
    def_ = util.rev_id()
    ne_(abc, def_)

def test_003_heads():
    eq_(env._get_heads(), [])

def test_004_rev():
    script = env.generate_rev(abc, "this is a message", refresh=True)
    eq_(script.doc, "this is a message")
    eq_(script.revision, abc)
    eq_(script.down_revision, None)
    assert os.access(
        os.path.join(env.dir, 'versions', '%s_this_is_a_message.py' % abc), os.F_OK)
    assert callable(script.module.upgrade)
    eq_(env._get_heads(), [abc])

def test_005_nextrev():
    script = env.generate_rev(def_, "this is the next rev", refresh=True)
    assert os.access(
        os.path.join(env.dir, 'versions', '%s_this_is_the_next_rev.py' % def_), os.F_OK)
    eq_(script.revision, def_)
    eq_(script.down_revision, abc)
    eq_(env._revision_map[abc].nextrev, set([def_]))
    assert script.module.down_revision == abc
    assert callable(script.module.upgrade)
    assert callable(script.module.downgrade)
    eq_(env._get_heads(), [def_])

def test_006_from_clean_env():
    # test the environment so far with a 
    # new ScriptDirectory instance.

    env = staging_env(create=False)
    abc_rev = env._revision_map[abc]
    def_rev = env._revision_map[def_]
    eq_(abc_rev.nextrev, set([def_]))
    eq_(abc_rev.revision, abc)
    eq_(def_rev.down_revision, abc)
    eq_(env._get_heads(), [def_])

def test_007_no_refresh():
    script = env.generate_rev(util.rev_id(), "dont' refresh")
    ne_(script, env._as_rev_number("head"))
    env2 = staging_env(create=False)
    eq_(script, env2._as_rev_number("head"))

def test_008_long_name():
    rid = util.rev_id()
    script = env.generate_rev(rid, 
            "this is a really long name with "
            "lots of characters and also "
            "I'd like it to\nhave\nnewlines")
    assert os.access(
        os.path.join(env.dir, 'versions', '%s_this_is_a_really_lon.py' % rid), os.F_OK)


def setup():
    global env
    env = staging_env()

def teardown():
    clear_staging_env()