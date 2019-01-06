# coding: utf-8

from contextlib import contextmanager
import os
import re
import textwrap

from alembic import command
from alembic import util
from alembic.environment import EnvironmentContext
from alembic.script import Script
from alembic.script import ScriptDirectory
from alembic.testing import assert_raises_message
from alembic.testing import eq_
from alembic.testing import mock
from alembic.testing.env import _no_sql_testing_config
from alembic.testing.env import _sqlite_file_db
from alembic.testing.env import _sqlite_testing_config
from alembic.testing.env import clear_staging_env
from alembic.testing.env import env_file_fixture
from alembic.testing.env import staging_env
from alembic.testing.env import three_rev_fixture
from alembic.testing.env import write_script
from alembic.testing.fixtures import capture_context_buffer
from alembic.testing.fixtures import TestBase
from alembic.util import compat


class ApplyVersionsFunctionalTest(TestBase):
    __only_on__ = "sqlite"

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
        self._test_007_stamp_upgrade()

    def _test_001_revisions(self):
        self.a = a = util.rev_id()
        self.b = b = util.rev_id()
        self.c = c = util.rev_id()

        script = ScriptDirectory.from_config(self.cfg)
        script.generate_revision(a, None, refresh=True)
        write_script(
            script,
            a,
            """
    revision = '%s'
    down_revision = None

    from alembic import op


    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")


    def downgrade():
        op.execute("DROP TABLE foo")

    """
            % a,
            sourceless=self.sourceless,
        )

        script.generate_revision(b, None, refresh=True)
        write_script(
            script,
            b,
            """
    revision = '%s'
    down_revision = '%s'

    from alembic import op


    def upgrade():
        op.execute("CREATE TABLE bar(id integer)")


    def downgrade():
        op.execute("DROP TABLE bar")

    """
            % (b, a),
            sourceless=self.sourceless,
        )

        script.generate_revision(c, None, refresh=True)
        write_script(
            script,
            c,
            """
    revision = '%s'
    down_revision = '%s'

    from alembic import op


    def upgrade():
        op.execute("CREATE TABLE bat(id integer)")


    def downgrade():
        op.execute("DROP TABLE bat")

    """
            % (c, b),
            sourceless=self.sourceless,
        )

    def _test_002_upgrade(self):
        command.upgrade(self.cfg, self.c)
        db = self.bind
        assert db.dialect.has_table(db.connect(), "foo")
        assert db.dialect.has_table(db.connect(), "bar")
        assert db.dialect.has_table(db.connect(), "bat")

    def _test_003_downgrade(self):
        command.downgrade(self.cfg, self.a)
        db = self.bind
        assert db.dialect.has_table(db.connect(), "foo")
        assert not db.dialect.has_table(db.connect(), "bar")
        assert not db.dialect.has_table(db.connect(), "bat")

    def _test_004_downgrade(self):
        command.downgrade(self.cfg, "base")
        db = self.bind
        assert not db.dialect.has_table(db.connect(), "foo")
        assert not db.dialect.has_table(db.connect(), "bar")
        assert not db.dialect.has_table(db.connect(), "bat")

    def _test_005_upgrade(self):
        command.upgrade(self.cfg, self.b)
        db = self.bind
        assert db.dialect.has_table(db.connect(), "foo")
        assert db.dialect.has_table(db.connect(), "bar")
        assert not db.dialect.has_table(db.connect(), "bat")

    def _test_006_upgrade_again(self):
        command.upgrade(self.cfg, self.b)
        db = self.bind
        assert db.dialect.has_table(db.connect(), "foo")
        assert db.dialect.has_table(db.connect(), "bar")
        assert not db.dialect.has_table(db.connect(), "bat")

    def _test_007_stamp_upgrade(self):
        command.stamp(self.cfg, self.c)
        db = self.bind
        assert db.dialect.has_table(db.connect(), "foo")
        assert db.dialect.has_table(db.connect(), "bar")
        assert not db.dialect.has_table(db.connect(), "bat")


class SimpleSourcelessApplyVersionsTest(ApplyVersionsFunctionalTest):
    sourceless = "simple"


class NewFangledSourcelessEnvOnlyApplyVersionsTest(
    ApplyVersionsFunctionalTest
):
    sourceless = "pep3147_envonly"

    __requires__ = ("pep3147",)


class NewFangledSourcelessEverythingApplyVersionsTest(
    ApplyVersionsFunctionalTest
):
    sourceless = "pep3147_everything"

    __requires__ = ("pep3147",)


class CallbackEnvironmentTest(ApplyVersionsFunctionalTest):
    exp_kwargs = frozenset(("ctx", "heads", "run_args", "step"))

    @staticmethod
    def _env_file_fixture():
        env_file_fixture(
            textwrap.dedent(
                """\
            import alembic
            from alembic import context
            from sqlalchemy import engine_from_config, pool

            config = context.config

            target_metadata = None

            def run_migrations_offline():
                url = config.get_main_option('sqlalchemy.url')
                context.configure(
                    url=url, target_metadata=target_metadata,
                    on_version_apply=alembic.mock_event_listener,
                    literal_binds=True)

                with context.begin_transaction():
                    context.run_migrations()

            def run_migrations_online():
                connectable = engine_from_config(
                    config.get_section(config.config_ini_section),
                    prefix='sqlalchemy.',
                    poolclass=pool.NullPool)
                with connectable.connect() as connection:
                    context.configure(
                        connection=connection,
                        on_version_apply=alembic.mock_event_listener,
                        target_metadata=target_metadata,
                    )
                    with context.begin_transaction():
                        context.run_migrations()

            if context.is_offline_mode():
                run_migrations_offline()
            else:
                run_migrations_online()
            """
            )
        )

    def test_steps(self):
        import alembic

        alembic.mock_event_listener = None
        self._env_file_fixture()
        with mock.patch("alembic.mock_event_listener", mock.Mock()) as mymock:
            super(CallbackEnvironmentTest, self).test_steps()
        calls = mymock.call_args_list
        assert calls
        for call in calls:
            args, kw = call
            assert not args
            assert set(kw.keys()) >= self.exp_kwargs
            assert kw["run_args"] == {}
            assert hasattr(kw["ctx"], "get_current_revision")

            step = kw["step"]
            assert isinstance(step.is_upgrade, bool)
            assert isinstance(step.is_stamp, bool)
            assert isinstance(step.is_migration, bool)
            assert isinstance(step.up_revision_id, compat.string_types)
            assert isinstance(step.up_revision, Script)

            for revtype in "up", "down", "source", "destination":
                revs = getattr(step, "%s_revisions" % revtype)
                assert isinstance(revs, tuple)
                for rev in revs:
                    assert isinstance(rev, Script)
                revids = getattr(step, "%s_revision_ids" % revtype)
                for revid in revids:
                    assert isinstance(revid, compat.string_types)

            heads = kw["heads"]
            assert hasattr(heads, "__iter__")
            for h in heads:
                assert h is None or isinstance(h, compat.string_types)


class OfflineTransactionalDDLTest(TestBase):
    def setUp(self):
        self.env = staging_env()
        self.cfg = cfg = _no_sql_testing_config()
        cfg.set_main_option("dialect_name", "sqlite")
        cfg.remove_main_option("url")

        self.a, self.b, self.c = three_rev_fixture(cfg)

    def tearDown(self):
        clear_staging_env()

    def test_begin_commit_transactional_ddl(self):
        with capture_context_buffer(transactional_ddl=True) as buf:
            command.upgrade(self.cfg, self.c, sql=True)
        assert re.match(
            (r"^BEGIN;\s+CREATE TABLE.*?%s.*" % self.a)
            + (r".*%s" % self.b)
            + (r".*%s.*?COMMIT;.*$" % self.c),
            buf.getvalue(),
            re.S,
        )

    def test_begin_commit_nontransactional_ddl(self):
        with capture_context_buffer(transactional_ddl=False) as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert re.match(r"^CREATE TABLE.*?\n+$", buf.getvalue(), re.S)
        assert "COMMIT;" not in buf.getvalue()

    def test_begin_commit_per_rev_ddl(self):
        with capture_context_buffer(transaction_per_migration=True) as buf:
            command.upgrade(self.cfg, self.c, sql=True)
        assert re.match(
            (r"^BEGIN;\s+CREATE TABLE.*%s.*?COMMIT;.*" % self.a)
            + (r"BEGIN;.*?%s.*?COMMIT;.*" % self.b)
            + (r"BEGIN;.*?%s.*?COMMIT;.*$" % self.c),
            buf.getvalue(),
            re.S,
        )


class OnlineTransactionalDDLTest(TestBase):
    def tearDown(self):
        clear_staging_env()

    def _opened_transaction_fixture(self):
        self.env = staging_env()
        self.cfg = _sqlite_testing_config()

        script = ScriptDirectory.from_config(self.cfg)
        a = util.rev_id()
        b = util.rev_id()
        c = util.rev_id()
        script.generate_revision(a, "revision a", refresh=True)
        write_script(
            script,
            a,
            """
"rev a"

revision = '%s'
down_revision = None

def upgrade():
    pass

def downgrade():
    pass

"""
            % (a,),
        )
        script.generate_revision(b, "revision b", refresh=True)
        write_script(
            script,
            b,
            """
"rev b"
revision = '%s'
down_revision = '%s'

from alembic import op


def upgrade():
    conn = op.get_bind()
    trans = conn.begin()


def downgrade():
    pass

"""
            % (b, a),
        )
        script.generate_revision(c, "revision c", refresh=True)
        write_script(
            script,
            c,
            """
"rev c"
revision = '%s'
down_revision = '%s'

from alembic import op


def upgrade():
    pass


def downgrade():
    pass

"""
            % (c, b),
        )
        return a, b, c

    @contextmanager
    def _patch_environment(self, transactional_ddl, transaction_per_migration):
        conf = EnvironmentContext.configure

        def configure(*arg, **opt):
            opt.update(
                transactional_ddl=transactional_ddl,
                transaction_per_migration=transaction_per_migration,
            )
            return conf(*arg, **opt)

        with mock.patch.object(EnvironmentContext, "configure", configure):
            yield

    def test_raise_when_rev_leaves_open_transaction(self):
        a, b, c = self._opened_transaction_fixture()

        with self._patch_environment(
            transactional_ddl=False, transaction_per_migration=False
        ):
            assert_raises_message(
                util.CommandError,
                r'Migration "upgrade .*, rev b" has left an uncommitted '
                r"transaction opened; transactional_ddl is False so Alembic "
                r"is not committing transactions",
                command.upgrade,
                self.cfg,
                c,
            )

    def test_raise_when_rev_leaves_open_transaction_tpm(self):
        a, b, c = self._opened_transaction_fixture()

        with self._patch_environment(
            transactional_ddl=False, transaction_per_migration=True
        ):
            assert_raises_message(
                util.CommandError,
                r'Migration "upgrade .*, rev b" has left an uncommitted '
                r"transaction opened; transactional_ddl is False so Alembic "
                r"is not committing transactions",
                command.upgrade,
                self.cfg,
                c,
            )

    def test_noerr_rev_leaves_open_transaction_transactional_ddl(self):
        a, b, c = self._opened_transaction_fixture()

        with self._patch_environment(
            transactional_ddl=True, transaction_per_migration=False
        ):
            command.upgrade(self.cfg, c)

    def test_noerr_transaction_opened_externally(self):
        a, b, c = self._opened_transaction_fixture()

        env_file_fixture(
            """
from sqlalchemy import engine_from_config, pool

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool)

    with connectable.connect() as connection:
        with connection.begin() as real_trans:
            context.configure(
                connection=connection,
                transactional_ddl=False,
                transaction_per_migration=False
            )

            with context.begin_transaction():
                context.run_migrations()

run_migrations_online()

"""
        )

        command.stamp(self.cfg, c)


class EncodingTest(TestBase):
    def setUp(self):
        self.env = staging_env()
        self.cfg = cfg = _no_sql_testing_config()
        cfg.set_main_option("dialect_name", "sqlite")
        cfg.remove_main_option("url")
        self.a = util.rev_id()
        script = ScriptDirectory.from_config(cfg)
        script.generate_revision(self.a, "revision a", refresh=True)
        write_script(
            script,
            self.a,
            (
                compat.u(
                    """# coding: utf-8
from __future__ import unicode_literals
revision = '%s'
down_revision = None

from alembic import op

def upgrade():
    op.execute("« S’il vous plaît…")

def downgrade():
    op.execute("drôle de petite voix m’a réveillé")

"""
                )
                % self.a
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        clear_staging_env()

    def test_encode(self):
        with capture_context_buffer(
            bytes_io=True, output_encoding="utf-8"
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
        write_script(
            script,
            a,
            """
    revision = '%s'
    down_revision = None

    from alembic import op


    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")


    def downgrade():
        op.execute("DROP TABLE foo")

    """
            % a,
        )

        script = ScriptDirectory.from_config(self.cfg)
        rev = script.get_revision(a)
        eq_(rev.revision, a)
        eq_(os.path.basename(rev.path), "myfile_some_message.py")

    def test_lookup_legacy(self):
        self.cfg.set_main_option("file_template", "%%(rev)s")
        script = ScriptDirectory.from_config(self.cfg)
        a = util.rev_id()
        script.generate_revision(a, None, refresh=True)
        write_script(
            script,
            a,
            """
    down_revision = None

    from alembic import op


    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")


    def downgrade():
        op.execute("DROP TABLE foo")

    """,
        )

        script = ScriptDirectory.from_config(self.cfg)
        rev = script.get_revision(a)
        eq_(rev.revision, a)
        eq_(os.path.basename(rev.path), "%s.py" % a)

    def test_error_on_new_with_missing_revision(self):
        self.cfg.set_main_option("file_template", "%%(slug)s_%%(rev)s")
        script = ScriptDirectory.from_config(self.cfg)
        a = util.rev_id()
        script.generate_revision(a, "foobar", refresh=True)

        path = script.get_revision(a).path
        with open(path, "w") as fp:
            fp.write(
                """
down_revision = None

from alembic import op


def upgrade():
    op.execute("CREATE TABLE foo(id integer)")


def downgrade():
    op.execute("DROP TABLE foo")

"""
            )
        pyc_path = util.pyc_file_from_path(path)
        if pyc_path is not None and os.access(pyc_path, os.F_OK):
            os.unlink(pyc_path)

        assert_raises_message(
            util.CommandError,
            "Could not determine revision id from filename foobar_%s.py. "
            "Be sure the 'revision' variable is declared "
            "inside the script." % a,
            Script._from_path,
            script,
            path,
        )


class IgnoreFilesTest(TestBase):
    sourceless = False

    def setUp(self):
        self.bind = _sqlite_file_db()
        self.env = staging_env(sourceless=self.sourceless)
        self.cfg = _sqlite_testing_config(sourceless=self.sourceless)

    def tearDown(self):
        clear_staging_env()

    def _test_ignore_file_py(self, fname):

        command.revision(self.cfg, message="some rev")
        script = ScriptDirectory.from_config(self.cfg)
        path = os.path.join(script.versions, fname)
        with open(path, "w") as f:
            f.write("crap, crap -> crap")
        command.revision(self.cfg, message="another rev")

        script.get_revision("head")

    def _test_ignore_init_py(self, ext):
        """test that __init__.py is ignored."""

        self._test_ignore_file_py("__init__.%s" % ext)

    def _test_ignore_dot_hash_py(self, ext):
        """test that .#test.py is ignored."""

        self._test_ignore_file_py(".#test.%s" % ext)

    def test_ignore_init_py(self):
        self._test_ignore_init_py("py")

    def test_ignore_init_pyc(self):
        self._test_ignore_init_py("pyc")

    def test_ignore_init_pyx(self):
        self._test_ignore_init_py("pyx")

    def test_ignore_init_pyo(self):
        self._test_ignore_init_py("pyo")

    def test_ignore_dot_hash_py(self):
        self._test_ignore_dot_hash_py("py")

    def test_ignore_dot_hash_pyc(self):
        self._test_ignore_dot_hash_py("pyc")

    def test_ignore_dot_hash_pyx(self):
        self._test_ignore_dot_hash_py("pyx")

    def test_ignore_dot_hash_pyo(self):
        self._test_ignore_dot_hash_py("pyo")


class SimpleSourcelessIgnoreFilesTest(IgnoreFilesTest):
    sourceless = "simple"


class NewFangledEnvOnlySourcelessIgnoreFilesTest(IgnoreFilesTest):
    sourceless = "pep3147_envonly"

    __requires__ = ("pep3147",)


class NewFangledEverythingSourcelessIgnoreFilesTest(IgnoreFilesTest):
    sourceless = "pep3147_everything"

    __requires__ = ("pep3147",)


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
        write_script(
            script,
            a,
            """
    revision = '%s'
    down_revision = None

    from alembic import op


    def upgrade():
        op.execute("CREATE TABLE foo(id integer)")


    def downgrade():
        op.execute("DROP TABLE foo")

    """
            % a,
            sourceless=True,
        )

        script = ScriptDirectory.from_config(self.cfg)
        eq_(script.get_heads(), [])

        self.cfg.set_main_option("sourceless", "true")
        script = ScriptDirectory.from_config(self.cfg)
        eq_(script.get_heads(), [a])
