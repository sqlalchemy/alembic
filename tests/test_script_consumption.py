# coding: utf-8

import os
import re

from alembic import command, util, compat
from alembic.script import ScriptDirectory, Script
from alembic.testing.env import clear_staging_env, staging_env, \
    _sqlite_testing_config, write_script, _sqlite_file_db, \
    three_rev_fixture, _no_sql_testing_config
from alembic.testing import eq_, assert_raises_message
from alembic.testing.fixtures import TestBase, capture_context_buffer


class ApplyVersionsFunctionalTest(TestBase):
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
        self.a = a = util.rev_id()
        self.b = b = util.rev_id()
        self.c = c = util.rev_id()

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
        command.upgrade(self.cfg, self.c)
        db = self.bind
        assert db.dialect.has_table(db.connect(), 'foo')
        assert db.dialect.has_table(db.connect(), 'bar')
        assert db.dialect.has_table(db.connect(), 'bat')

    def _test_003_downgrade(self):
        command.downgrade(self.cfg, self.a)
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
        command.upgrade(self.cfg, self.b)
        db = self.bind
        assert db.dialect.has_table(db.connect(), 'foo')
        assert db.dialect.has_table(db.connect(), 'bar')
        assert not db.dialect.has_table(db.connect(), 'bat')

    def _test_006_upgrade_again(self):
        command.upgrade(self.cfg, self.b)
        db = self.bind
        assert db.dialect.has_table(db.connect(), 'foo')
        assert db.dialect.has_table(db.connect(), 'bar')
        assert not db.dialect.has_table(db.connect(), 'bat')


class SourcelessApplyVersionsTest(ApplyVersionsFunctionalTest):
    sourceless = True


class TransactionalDDLTest(TestBase):
    def setUp(self):
        self.env = staging_env()
        self.cfg = cfg = _no_sql_testing_config()
        cfg.set_main_option('dialect_name', 'sqlite')
        cfg.remove_main_option('url')

        self.a, self.b, self.c = three_rev_fixture(cfg)

    def tearDown(self):
        clear_staging_env()

    def test_begin_commit_transactional_ddl(self):
        with capture_context_buffer(transactional_ddl=True) as buf:
            command.upgrade(self.cfg, self.c, sql=True)
        assert re.match(
            (r"^BEGIN;\s+CREATE TABLE.*?%s.*" % self.a) +
            (r".*%s" % self.b) +
            (r".*%s.*?COMMIT;.*$" % self.c),

            buf.getvalue(), re.S)

    def test_begin_commit_nontransactional_ddl(self):
        with capture_context_buffer(transactional_ddl=False) as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert re.match(r"^CREATE TABLE.*?\n+$", buf.getvalue(), re.S)
        assert "COMMIT;" not in buf.getvalue()

    def test_begin_commit_per_rev_ddl(self):
        with capture_context_buffer(transaction_per_migration=True) as buf:
            command.upgrade(self.cfg, self.c, sql=True)
        assert re.match(
            (r"^BEGIN;\s+CREATE TABLE.*%s.*?COMMIT;.*" % self.a) +
            (r"BEGIN;.*?%s.*?COMMIT;.*" % self.b) +
            (r"BEGIN;.*?%s.*?COMMIT;.*$" % self.c),

            buf.getvalue(), re.S)


class EncodingTest(TestBase):

    def setUp(self):
        self.env = staging_env()
        self.cfg = cfg = _no_sql_testing_config()
        cfg.set_main_option('dialect_name', 'sqlite')
        cfg.remove_main_option('url')
        self.a = util.rev_id()
        script = ScriptDirectory.from_config(cfg)
        script.generate_revision(self.a, "revision a", refresh=True)
        write_script(script, self.a, (compat.u("""# coding: utf-8
from __future__ import unicode_literals
revision = '%s'
down_revision = None

from alembic import op

def upgrade():
    op.execute("« S’il vous plaît…")

def downgrade():
    op.execute("drôle de petite voix m’a réveillé")

""") % self.a), encoding='utf-8')

    def tearDown(self):
        clear_staging_env()

    def test_encode(self):
        with capture_context_buffer(
            bytes_io=True,
            output_encoding='utf-8'
        ) as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert compat.u("« S’il vous plaît…").encode("utf-8") in buf.getvalue()


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

        path = script._revision_map[a].path
        with open(path, 'w') as fp:
            fp.write("""
down_revision = None

from alembic import op

def upgrade():
    op.execute("CREATE TABLE foo(id integer)")

def downgrade():
    op.execute("DROP TABLE foo")
""")
        pyc_path = util.pyc_file_from_path(path)
        if os.access(pyc_path, os.F_OK):
            os.unlink(pyc_path)

        assert_raises_message(
            util.CommandError,
            "Could not determine revision id from filename foobar_%s.py. "
            "Be sure the 'revision' variable is declared "
            "inside the script." % a,
            Script._from_path, script, path)


class IgnoreInitTest(TestBase):
    sourceless = False

    def setUp(self):
        self.bind = _sqlite_file_db()
        self.env = staging_env(sourceless=self.sourceless)
        self.cfg = _sqlite_testing_config(sourceless=self.sourceless)

    def tearDown(self):
        clear_staging_env()

    def _test_ignore_init_py(self, ext):
        """test that __init__.py is ignored."""

        command.revision(self.cfg, message="some rev")
        script = ScriptDirectory.from_config(self.cfg)
        path = os.path.join(script.versions, "__init__.%s" % ext)
        with open(path, 'w') as f:
            f.write(
                "crap, crap -> crap"
            )
        command.revision(self.cfg, message="another rev")

        script.get_revision('head')

    def test_ignore_py(self):
        self._test_ignore_init_py("py")

    def test_ignore_pyc(self):
        self._test_ignore_init_py("pyc")

    def test_ignore_pyx(self):
        self._test_ignore_init_py("pyx")

    def test_ignore_pyo(self):
        self._test_ignore_init_py("pyo")


class SourcelessIgnoreInitTest(IgnoreInitTest):
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
