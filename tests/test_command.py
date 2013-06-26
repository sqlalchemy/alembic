import unittest
from . import clear_staging_env, staging_env, \
    _sqlite_testing_config, \
    three_rev_fixture, eq_
from alembic import command
from io import StringIO
from alembic.script import ScriptDirectory



class StdoutCommandTest(unittest.TestCase):

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

        revs = {"reva": self.a, "revb": self.b, "revc": self.c}
        eq_(
            buf.getvalue().strip(),
            "\n".join([script.get_revision(rev).log_entry for rev in expected]).strip()
        )

    def test_history_full(self):
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg)
        self._eq_cmd_output(buf, [self.c, self.b, self.a])

    def test_history_num_range(self):
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, "%s:%s" % (self.a, self.b))
        self._eq_cmd_output(buf, [self.b])

    def test_history_base_to_num(self):
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, ":%s" % (self.b))
        self._eq_cmd_output(buf, [self.b, self.a])

    def test_history_num_to_head(self):
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, "%s:" % (self.a))
        self._eq_cmd_output(buf, [self.c, self.b])

    def test_history_num_plus_relative(self):
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, "%s:+2" % (self.a))
        self._eq_cmd_output(buf, [self.c, self.b])

    def test_history_relative_to_num(self):
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, "-2:%s" % (self.c))
        self._eq_cmd_output(buf, [self.c, self.b])

    def test_history_current_to_head_as_b(self):
        command.stamp(self.cfg, self.b)
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, "current:")
        self._eq_cmd_output(buf, [self.c])

    def test_history_current_to_head_as_base(self):
        command.stamp(self.cfg, "base")
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, "current:")
        self._eq_cmd_output(buf, [self.c, self.b, self.a])
