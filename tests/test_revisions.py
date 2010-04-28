from tests import _clear_testing_directory, _testing_env, eq_
import os

def test_environment():
    env = _testing_env()
    assert_set = set(['env.py', 'script.py.mako', 'README'])
    eq_(
        assert_set.intersection(
                os.listdir(env.dir)
            ),
        assert_set
    )
    
def teardown():
    _clear_testing_directory()