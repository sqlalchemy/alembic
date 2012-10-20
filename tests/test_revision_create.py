from tests import clear_staging_env, staging_env, eq_, ne_, is_, staging_directory
from tests import _no_sql_testing_config, env_file_fixture, script_file_fixture, _testing_config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.environment import EnvironmentContext
from alembic import util
import os
import unittest
import datetime

env, abc, def_ = None, None, None

class GeneralOrderedTests(unittest.TestCase):
    def test_001_environment(self):
        assert_set = set(['env.py', 'script.py.mako', 'README'])
        eq_(
            assert_set.intersection(os.listdir(env.dir)),
            assert_set
        )

    def test_002_rev_ids(self):
        global abc, def_
        abc = util.rev_id()
        def_ = util.rev_id()
        ne_(abc, def_)

    def test_003_heads(self):
        eq_(env.get_heads(), [])

    def test_004_rev(self):
        script = env.generate_revision(abc, "this is a message", refresh=True)
        eq_(script.doc, "this is a message")
        eq_(script.revision, abc)
        eq_(script.down_revision, None)
        assert os.access(
            os.path.join(env.dir, 'versions', '%s_this_is_a_message.py' % abc), os.F_OK)
        assert callable(script.module.upgrade)
        eq_(env.get_heads(), [abc])

    def test_005_nextrev(self):
        script = env.generate_revision(def_, "this is the next rev", refresh=True)
        assert os.access(
            os.path.join(env.dir, 'versions', '%s_this_is_the_next_rev.py' % def_), os.F_OK)
        eq_(script.revision, def_)
        eq_(script.down_revision, abc)
        eq_(env._revision_map[abc].nextrev, set([def_]))
        assert script.module.down_revision == abc
        assert callable(script.module.upgrade)
        assert callable(script.module.downgrade)
        eq_(env.get_heads(), [def_])

    def test_006_from_clean_env(self):
        # test the environment so far with a
        # new ScriptDirectory instance.

        env = staging_env(create=False)
        abc_rev = env._revision_map[abc]
        def_rev = env._revision_map[def_]
        eq_(abc_rev.nextrev, set([def_]))
        eq_(abc_rev.revision, abc)
        eq_(def_rev.down_revision, abc)
        eq_(env.get_heads(), [def_])

    def test_007_no_refresh(self):
        rid = util.rev_id()
        script = env.generate_revision(rid, "dont' refresh")
        is_(script, None)
        env2 = staging_env(create=False)
        eq_(env2._as_rev_number("head"), rid)

    def test_008_long_name(self):
        rid = util.rev_id()
        env.generate_revision(rid,
                "this is a really long name with "
                "lots of characters and also "
                "I'd like it to\nhave\nnewlines")
        assert os.access(
            os.path.join(env.dir, 'versions',
                        '%s_this_is_a_really_lon.py' % rid), os.F_OK)


    @classmethod
    def setup_class(cls):
        global env
        env = staging_env()

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

class ScriptNamingTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        _testing_config()

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_args(self):
        script = ScriptDirectory(
                        staging_directory,
                        file_template="%(rev)s_%(slug)s_"
                            "%(year)s_%(month)s_"
                            "%(day)s_%(hour)s_"
                            "%(minute)s_%(second)s"
                    )
        create_date = datetime.datetime(2012, 7, 25, 15, 8, 5)
        eq_(
            script._rev_path("12345", "this is a message", create_date),
            "%s/versions/12345_this_is_a_"
            "message_2012_7_25_15_8_5.py" % staging_directory
        )


class TemplateArgsTest(unittest.TestCase):
    def setUp(self):
        staging_env()
        self.cfg = _no_sql_testing_config(
            directives="\nrevision_environment=true\n"
        )

    def tearDown(self):
        clear_staging_env()

    def test_args_propagate(self):
        config = _no_sql_testing_config()
        script = ScriptDirectory.from_config(config)
        template_args = {"x": "x1", "y": "y1", "z": "z1"}
        env = EnvironmentContext(
            config,
            script,
            template_args=template_args
        )
        env.configure(dialect_name="sqlite",
                        template_args={"y": "y2", "q": "q1"})
        eq_(
            template_args,
            {"x": "x1", "y": "y2", "z": "z1", "q": "q1"}
        )

    def test_tmpl_args_revision(self):
        env_file_fixture("""
context.configure(dialect_name='sqlite', template_args={"somearg":"somevalue"})
""")
        script_file_fixture("""
# somearg: ${somearg}
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
""")
        command.revision(self.cfg, message="some rev")
        script = ScriptDirectory.from_config(self.cfg)
        rev = script.get_revision('head')
        text = open(rev.path).read()
        assert "somearg: somevalue" in text

