from alembic import command
from io import TextIOWrapper, BytesIO
from alembic.script import ScriptDirectory
from alembic.testing.fixtures import TestBase, capture_context_buffer
from alembic.testing.env import staging_env, _sqlite_testing_config, \
    three_rev_fixture, clear_staging_env, _no_sql_testing_config
from alembic.testing import eq_


class HistoryTest(TestBase):

    @classmethod
    def setup_class(cls):
        cls.env = staging_env()
        cls.cfg = _sqlite_testing_config()
        cls.a, cls.b, cls.c = three_rev_fixture(cls.cfg)

    @classmethod
    def teardown_class(cls):
        clear_staging_env()

    def _eq_cmd_output(self, buf, expected):
        script = ScriptDirectory.from_config(self.cfg)

        # test default encode/decode behavior as well,
        # rev B has a non-ascii char in it + a coding header.
        eq_(
            buf.getvalue().decode("ascii", 'replace').strip(),
            "\n".join([
                script.get_revision(rev).log_entry
                for rev in expected
            ]).encode("ascii", "replace").decode("ascii").strip()
        )

    def _buf_fixture(self):
        # try to simulate how sys.stdout looks - we send it u''
        # but then it's trying to encode to something.
        buf = BytesIO()
        wrapper = TextIOWrapper(buf, encoding='ascii', line_buffering=True)
        wrapper.getvalue = buf.getvalue
        return wrapper

    def test_history_full(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg)
        self._eq_cmd_output(buf, [self.c, self.b, self.a])

    def test_history_num_range(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "%s:%s" % (self.a, self.b))
        self._eq_cmd_output(buf, [self.b])

    def test_history_base_to_num(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, ":%s" % (self.b))
        self._eq_cmd_output(buf, [self.b, self.a])

    def test_history_num_to_head(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "%s:" % (self.a))
        self._eq_cmd_output(buf, [self.c, self.b])

    def test_history_num_plus_relative(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "%s:+2" % (self.a))
        self._eq_cmd_output(buf, [self.c, self.b])

    def test_history_relative_to_num(self):
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "-2:%s" % (self.c))
        self._eq_cmd_output(buf, [self.c, self.b])

    def test_history_current_to_head_as_b(self):
        command.stamp(self.cfg, self.b)
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "current:")
        self._eq_cmd_output(buf, [self.c])

    def test_history_current_to_head_as_base(self):
        command.stamp(self.cfg, "base")
        self.cfg.stdout = buf = self._buf_fixture()
        command.history(self.cfg, "current:")
        self._eq_cmd_output(buf, [self.c, self.b, self.a])


class UpgradeDowngradeStampTest(TestBase):

    def setUp(self):
        self.env = staging_env()
        self.cfg = cfg = _no_sql_testing_config()
        cfg.set_main_option('dialect_name', 'sqlite')
        cfg.remove_main_option('url')

        self.a, self.b, self.c = three_rev_fixture(cfg)

    def tearDown(self):
        clear_staging_env()

    def test_version_from_none_insert(self):
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, self.a, sql=True)
        assert "CREATE TABLE alembic_version" in buf.getvalue()
        assert "INSERT INTO alembic_version" in buf.getvalue()
        assert "CREATE STEP 1" in buf.getvalue()
        assert "CREATE STEP 2" not in buf.getvalue()
        assert "CREATE STEP 3" not in buf.getvalue()

    def test_version_from_middle_update(self):
        with capture_context_buffer() as buf:
            command.upgrade(self.cfg, "%s:%s" % (self.b, self.c), sql=True)
        assert "CREATE TABLE alembic_version" not in buf.getvalue()
        assert "UPDATE alembic_version" in buf.getvalue()
        assert "CREATE STEP 1" not in buf.getvalue()
        assert "CREATE STEP 2" not in buf.getvalue()
        assert "CREATE STEP 3" in buf.getvalue()

    def test_version_to_none(self):
        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, "%s:base" % self.c, sql=True)
        assert "CREATE TABLE alembic_version" not in buf.getvalue()
        assert "INSERT INTO alembic_version" not in buf.getvalue()
        assert "DROP TABLE alembic_version" in buf.getvalue()
        assert "DROP STEP 3" in buf.getvalue()
        assert "DROP STEP 2" in buf.getvalue()
        assert "DROP STEP 1" in buf.getvalue()

    def test_version_to_middle(self):
        with capture_context_buffer() as buf:
            command.downgrade(self.cfg, "%s:%s" % (self.c, self.a), sql=True)
        assert "CREATE TABLE alembic_version" not in buf.getvalue()
        assert "INSERT INTO alembic_version" not in buf.getvalue()
        assert "DROP TABLE alembic_version" not in buf.getvalue()
        assert "DROP STEP 3" in buf.getvalue()
        assert "DROP STEP 2" in buf.getvalue()
        assert "DROP STEP 1" not in buf.getvalue()

    def test_stamp(self):
        with capture_context_buffer() as buf:
            command.stamp(self.cfg, "head", sql=True)
        assert "UPDATE alembic_version "\
            "SET version_num='%s';" % self.c in buf.getvalue()

