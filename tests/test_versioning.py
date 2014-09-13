import os

from alembic import command, util
from alembic.script import ScriptDirectory
from alembic.testing.env import clear_staging_env, staging_env, \
    _sqlite_testing_config, write_script, _sqlite_file_db
from alembic.testing import eq_, assert_raises_message
from alembic.testing.fixtures import TestBase

a = b = c = None


class VersioningTest(TestBase):
    __only_on__ = 'sqlite'

    sourceless = False

    def setUp(self):
        self.bind = _sqlite_file_db()
        self.env = staging_env(sourceless=self.sourceless)
        self.cfg = _sqlite_testing_config(sourceless=self.sourceless)

    def tearDown(self):
        clear_staging_env()

    def test_steps(self):
        self._test_001_revisions()
        self._test_002_upgrade()
        self._test_003_downgrade()
        self._test_004_downgrade()
        self._test_005_upgrade()
        self._test_006_upgrade_again()

    def _test_001_revisions(self):
        global a, b, c
        a = util.rev_id()
        b = util.rev_id()
        c = util.rev_id()

        script = ScriptDirectory.from_config(self.cfg)
        script.generate_revision(a, None, refresh=True)
        write_script(script, a, """
    revision = '%s'
    down_revision = None

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")

    def downgrade():
        op.execute("DROP TABLE foo")

    """ % a, sourceless=self.sourceless)

        script.generate_revision(b, None, refresh=True)
        write_script(script, b, """
    revision = '%s'
    down_revision = '%s'

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE bar(id integer)")

    def downgrade():
        op.execute("DROP TABLE bar")

    """ % (b, a), sourceless=self.sourceless)

        script.generate_revision(c, None, refresh=True)
        write_script(script, c, """
    revision = '%s'
    down_revision = '%s'

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE bat(id integer)")

    def downgrade():
        op.execute("DROP TABLE bat")

    """ % (c, b), sourceless=self.sourceless)

    def _test_002_upgrade(self):
        command.upgrade(self.cfg, c)
        db = self.bind
        assert db.dialect.has_table(db.connect(), 'foo')
        assert db.dialect.has_table(db.connect(), 'bar')
        assert db.dialect.has_table(db.connect(), 'bat')

    def _test_003_downgrade(self):
        command.downgrade(self.cfg, a)
        db = self.bind
        assert db.dialect.has_table(db.connect(), 'foo')
        assert not db.dialect.has_table(db.connect(), 'bar')
        assert not db.dialect.has_table(db.connect(), 'bat')

    def _test_004_downgrade(self):
        command.downgrade(self.cfg, 'base')
        db = self.bind
        assert not db.dialect.has_table(db.connect(), 'foo')
        assert not db.dialect.has_table(db.connect(), 'bar')
        assert not db.dialect.has_table(db.connect(), 'bat')

    def _test_005_upgrade(self):
        command.upgrade(self.cfg, b)
        db = self.bind
        assert db.dialect.has_table(db.connect(), 'foo')
        assert db.dialect.has_table(db.connect(), 'bar')
        assert not db.dialect.has_table(db.connect(), 'bat')

    def _test_006_upgrade_again(self):
        command.upgrade(self.cfg, b)


class VersionNameTemplateTest(TestBase):

    def setUp(self):
        self.env = staging_env()
        self.cfg = _sqlite_testing_config()

    def tearDown(self):
        clear_staging_env()

    def test_option(self):
        self.cfg.set_main_option("file_template", "myfile_%%(slug)s")
        script = ScriptDirectory.from_config(self.cfg)
        a = util.rev_id()
        script.generate_revision(a, "some message", refresh=True)
        write_script(script, a, """
    revision = '%s'
    down_revision = None

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")

    def downgrade():
        op.execute("DROP TABLE foo")

    """ % a)

        script = ScriptDirectory.from_config(self.cfg)
        rev = script._get_rev(a)
        eq_(rev.revision, a)
        eq_(os.path.basename(rev.path), "myfile_some_message.py")

    def test_lookup_legacy(self):
        self.cfg.set_main_option("file_template", "%%(rev)s")
        script = ScriptDirectory.from_config(self.cfg)
        a = util.rev_id()
        script.generate_revision(a, None, refresh=True)
        write_script(script, a, """
    down_revision = None

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")

    def downgrade():
        op.execute("DROP TABLE foo")

    """)

        script = ScriptDirectory.from_config(self.cfg)
        rev = script._get_rev(a)
        eq_(rev.revision, a)
        eq_(os.path.basename(rev.path), "%s.py" % a)

    def test_error_on_new_with_missing_revision(self):
        self.cfg.set_main_option("file_template", "%%(slug)s_%%(rev)s")
        script = ScriptDirectory.from_config(self.cfg)
        a = util.rev_id()
        script.generate_revision(a, "foobar", refresh=True)
        assert_raises_message(
            util.CommandError,
            "Could not determine revision id from filename foobar_%s.py. "
            "Be sure the 'revision' variable is declared "
            "inside the script." % a,
            write_script, script, a, """
        down_revision = None

        from alembic import op

        def upgrade():
            op.execute("CREATE TABLE foo(id integer)")

        def downgrade():
            op.execute("DROP TABLE foo")

        """)


class SourcelessVersioningTest(VersioningTest):
    sourceless = True


class SourcelessNeedsFlagTest(TestBase):

    def setUp(self):
        self.env = staging_env(sourceless=False)
        self.cfg = _sqlite_testing_config()

    def tearDown(self):
        clear_staging_env()

    def test_needs_flag(self):
        a = util.rev_id()

        script = ScriptDirectory.from_config(self.cfg)
        script.generate_revision(a, None, refresh=True)
        write_script(script, a, """
    revision = '%s'
    down_revision = None

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")

    def downgrade():
        op.execute("DROP TABLE foo")

    """ % a, sourceless=True)

        script = ScriptDirectory.from_config(self.cfg)
        eq_(script.get_heads(), [])

        self.cfg.set_main_option("sourceless", "true")
        script = ScriptDirectory.from_config(self.cfg)
        eq_(script.get_heads(), [a])
