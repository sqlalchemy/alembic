from __future__ import with_statement
from tests import clear_staging_env, staging_env, \
    _sqlite_testing_config, sqlite_db, eq_, ne_, write_script, \
    assert_raises_message
from alembic import command, util
from alembic.script import ScriptDirectory
import time
import unittest
import os

class VersioningTest(unittest.TestCase):
    def test_001_revisions(self):
        global a, b, c
        a = util.rev_id()
        b = util.rev_id()
        c = util.rev_id()

        script = ScriptDirectory.from_config(self.cfg)
        script.generate_rev(a, None, refresh=True)
        write_script(script, a, """
    revision = '%s'
    down_revision = None

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")

    def downgrade():
        op.execute("DROP TABLE foo")

    """ % a)

        script.generate_rev(b, None, refresh=True)
        write_script(script, b, """
    revision = '%s'
    down_revision = '%s'

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE bar(id integer)")

    def downgrade():
        op.execute("DROP TABLE bar")

    """ % (b, a))

        script.generate_rev(c, None, refresh=True)
        write_script(script, c, """
    revision = '%s'
    down_revision = '%s'

    from alembic import op

    def upgrade():
        op.execute("CREATE TABLE bat(id integer)")

    def downgrade():
        op.execute("DROP TABLE bat")

    """ % (c, b))


    def test_002_upgrade(self):
        command.upgrade(self.cfg, c)
        db = sqlite_db()
        assert db.dialect.has_table(db.connect(), 'foo')
        assert db.dialect.has_table(db.connect(), 'bar')
        assert db.dialect.has_table(db.connect(), 'bat')

    def test_003_downgrade(self):
        command.downgrade(self.cfg, a)
        db = sqlite_db()
        assert db.dialect.has_table(db.connect(), 'foo')
        assert not db.dialect.has_table(db.connect(), 'bar')
        assert not db.dialect.has_table(db.connect(), 'bat')

    def test_004_downgrade(self):
        command.downgrade(self.cfg, 'base')
        db = sqlite_db()
        assert not db.dialect.has_table(db.connect(), 'foo')
        assert not db.dialect.has_table(db.connect(), 'bar')
        assert not db.dialect.has_table(db.connect(), 'bat')

    def test_005_upgrade(self):
        command.upgrade(self.cfg, b)
        db = sqlite_db()
        assert db.dialect.has_table(db.connect(), 'foo')
        assert db.dialect.has_table(db.connect(), 'bar')
        assert not db.dialect.has_table(db.connect(), 'bat')

    def test_006_upgrade_again(self):
        command.upgrade(self.cfg, b)


    # TODO: test some invalid movements

    @classmethod
    def setup_class(cls):
        cls.env = staging_env()
        cls.cfg = _sqlite_testing_config()

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

class VersionNameTemplateTest(unittest.TestCase):
    def setUp(self):
        self.env = staging_env()
        self.cfg = _sqlite_testing_config()

    def tearDown(self):
        clear_staging_env()

    def test_option(self):
        self.cfg.set_main_option("file_template", "myfile_%%(slug)s")
        script = ScriptDirectory.from_config(self.cfg)
        a = util.rev_id()
        script.generate_rev(a, "some message", refresh=True)
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
        script.generate_rev(a, None, refresh=True)
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
        script.generate_rev(a, "foobar", refresh=True)
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

