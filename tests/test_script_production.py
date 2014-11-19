from alembic.testing.fixtures import TestBase
from alembic.testing import eq_, ne_, is_, assert_raises_message
from alembic.testing.env import clear_staging_env, staging_env, \
    _get_staging_directory, _no_sql_testing_config, env_file_fixture, \
    script_file_fixture, _testing_config, _sqlite_testing_config, \
    three_rev_fixture
from alembic import command
from alembic.script import ScriptDirectory
from alembic.environment import EnvironmentContext
from alembic import util
import os
import datetime

env, abc, def_ = None, None, None


class GeneralOrderedTests(TestBase):

    def setUp(self):
        global env
        env = staging_env()

    def tearDown(self):
        clear_staging_env()

    def test_steps(self):
        self._test_001_environment()
        self._test_002_rev_ids()
        self._test_003_api_methods_clean()
        self._test_004_rev()
        self._test_005_nextrev()
        self._test_006_from_clean_env()
        self._test_007_no_refresh()
        self._test_008_long_name()
        self._test_009_long_name_configurable()

    def _test_001_environment(self):
        assert_set = set(['env.py', 'script.py.mako', 'README'])
        eq_(
            assert_set.intersection(os.listdir(env.dir)),
            assert_set
        )

    def _test_002_rev_ids(self):
        global abc, def_
        abc = util.rev_id()
        def_ = util.rev_id()
        ne_(abc, def_)

    def _test_003_api_methods_clean(self):
        eq_(env.get_heads(), [])

        eq_(env.get_base(), None)

    def _test_004_rev(self):
        script = env.generate_revision(abc, "this is a message", refresh=True)
        eq_(script.doc, "this is a message")
        eq_(script.revision, abc)
        eq_(script.down_revision, None)
        assert os.access(
            os.path.join(env.dir, 'versions',
                         '%s_this_is_a_message.py' % abc), os.F_OK)
        assert callable(script.module.upgrade)
        eq_(env.get_heads(), [abc])
        eq_(env.get_base(), abc)

    def _test_005_nextrev(self):
        script = env.generate_revision(
            def_, "this is the next rev", refresh=True)
        assert os.access(
            os.path.join(
                env.dir, 'versions',
                '%s_this_is_the_next_rev.py' % def_), os.F_OK)
        eq_(script.revision, def_)
        eq_(script.down_revision, abc)
        eq_(env.get_revision(abc).nextrev, set([def_]))
        assert script.module.down_revision == abc
        assert callable(script.module.upgrade)
        assert callable(script.module.downgrade)
        eq_(env.get_heads(), [def_])
        eq_(env.get_base(), abc)

    def _test_006_from_clean_env(self):
        # test the environment so far with a
        # new ScriptDirectory instance.

        env = staging_env(create=False)
        abc_rev = env.get_revision(abc)
        def_rev = env.get_revision(def_)
        eq_(abc_rev.nextrev, set([def_]))
        eq_(abc_rev.revision, abc)
        eq_(def_rev.down_revision, abc)
        eq_(env.get_heads(), [def_])
        eq_(env.get_base(), abc)

    def _test_007_no_refresh(self):
        rid = util.rev_id()
        script = env.generate_revision(rid, "dont' refresh")
        is_(script, None)
        env2 = staging_env(create=False)
        eq_(env2.get_current_head(), rid)

    def _test_008_long_name(self):
        rid = util.rev_id()
        env.generate_revision(rid,
                              "this is a really long name with "
                              "lots of characters and also "
                              "I'd like it to\nhave\nnewlines")
        assert os.access(
            os.path.join(
                env.dir, 'versions',
                '%s_this_is_a_really_long_name_with_lots_of_.py' % rid),
            os.F_OK)

    def _test_009_long_name_configurable(self):
        env.truncate_slug_length = 60
        rid = util.rev_id()
        env.generate_revision(rid,
                              "this is a really long name with "
                              "lots of characters and also "
                              "I'd like it to\nhave\nnewlines")
        assert os.access(
            os.path.join(env.dir, 'versions',
                         '%s_this_is_a_really_long_name_with_lots_'
                         'of_characters_and_also_.py' % rid),
            os.F_OK)


class ScriptNamingTest(TestBase):

    @classmethod
    def setup_class(cls):
        _testing_config()

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def test_args(self):
        script = ScriptDirectory(
            _get_staging_directory(),
            file_template="%(rev)s_%(slug)s_"
            "%(year)s_%(month)s_"
            "%(day)s_%(hour)s_"
            "%(minute)s_%(second)s"
        )
        create_date = datetime.datetime(2012, 7, 25, 15, 8, 5)
        eq_(
            script._rev_path("12345", "this is a message", create_date),
            "%s/versions/12345_this_is_a_"
            "message_2012_7_25_15_8_5.py" % _get_staging_directory()
        )


class RevisionCommandTest(TestBase):
    def setUp(self):
        self.env = staging_env()
        self.cfg = _sqlite_testing_config()
        self.a, self.b, self.c = three_rev_fixture(self.cfg)

    def tearDown(self):
        clear_staging_env()

    def test_create_script_basic(self):
        rev = command.revision(self.cfg, message="some message")
        script = ScriptDirectory.from_config(self.cfg)
        rev = script.get_revision(rev.revision)
        eq_(rev.down_revision, self.c)
        assert "some message" in rev.doc

    def test_create_script_splice(self):
        rev = command.revision(
            self.cfg, message="some message", head=self.b, splice=True)
        script = ScriptDirectory.from_config(self.cfg)
        rev = script.get_revision(rev.revision)
        eq_(rev.down_revision, self.b)
        assert "some message" in rev.doc
        eq_(set(script.get_heads()), set([rev.revision, self.c]))

    def test_create_script_missing_splice(self):
        assert_raises_message(
            util.CommandError,
            "Revision %s is not a head revision; please specify --splice "
            "to create a new branch from this revision" % self.b,
            command.revision,
            self.cfg, message="some message", head=self.b
        )

    def test_create_script_branches(self):
        rev = command.revision(
            self.cfg, message="some message", branch_label="foobar")
        script = ScriptDirectory.from_config(self.cfg)
        rev = script.get_revision(rev.revision)
        eq_(script.get_revision("foobar"), rev)

    def test_create_script_branches_old_template(self):
        script = ScriptDirectory.from_config(self.cfg)
        with open(os.path.join(script.dir, "script.py.mako"), "w") as file_:
            file_.write(
                "<%text>#</%text> ${message}\n"
                "revision = ${repr(up_revision)}\n"
                "down_revision = ${repr(down_revision)}\n"
                "def upgrade():\n"
                "    ${upgrades if upgrades else 'pass'}\n\n"
                "def downgrade():\n"
                "    ${downgrade if downgrades else 'pass'}\n\n"
            )

        # works OK if no branch names
        command.revision(self.cfg, message="some message")

        assert_raises_message(
            util.CommandError,
            r"Version \w+ specified branch_labels foobar, "
            r"however the migration file .+?\b does not have them; have you "
            "upgraded your script.py.mako to include the 'branch_labels' "
            r"section\?",
            command.revision,
            self.cfg, message="some message", branch_label="foobar"
        )


class TemplateArgsTest(TestBase):

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
        with open(rev.path) as f:
            text = f.read()
        assert "somearg: somevalue" in text
