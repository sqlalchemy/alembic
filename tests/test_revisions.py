from tests import clear_staging_env, staging_env, eq_
import os

def test_001_environment():
    assert_set = set(['env.py', 'script.py.mako', 'README'])
    eq_(
        assert_set.intersection(os.listdir(env.dir)),
        assert_set
    )

def test_002_heads():
    eq_(env._get_heads(), [])
    
def test_003_rev():
    script = env.generate_rev("abc", "this is a message")
    eq_(script.module.__doc__,"this is a message")
    eq_(script.upgrade, "abc")
    eq_(script.downgrade, None)
    assert os.access(os.path.join(env.dir, 'versions', 'abc.py'), os.F_OK)
    assert callable(script.module.upgrade_abc)
    eq_(env._get_heads(), ["abc"])
    
def test_004_nextrev():
    script = env.generate_rev("def", "this is the next rev")
    eq_(script.upgrade, "def")
    eq_(script.downgrade, "abc")
    eq_(env._revision_map["abc"].nextrev, "def")
    assert callable(script.module.upgrade_def)
    assert callable(script.module.downgrade_abc)
    eq_(env._get_heads(), ["def"])

def test_005_from_clean_env():
    # test the environment so far with a 
    # new ScriptDirectory instance.
    
    env = staging_env(create=False)
    abc = env._revision_map["abc"]
    def_ = env._revision_map["def"]
    eq_(abc.nextrev, "def")
    eq_(abc.upgrade, "abc")
    eq_(def_.downgrade, "abc")
    eq_(env._get_heads(), ["def"])
    
def setup():
    global env
    env = staging_env()
    
def teardown():
    clear_staging_env()