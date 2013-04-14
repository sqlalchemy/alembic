import unittest
from . import clear_staging_env, staging_env, \
    _sqlite_testing_config, \
    three_rev_fixture, eq_
from alembic import command
from io import StringIO

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
        revs = {"reva": self.a, "revb": self.b, "revc": self.c}
        eq_(
            [s for s in buf.getvalue().split("\n") if s],
            [exp % revs for exp in expected]
        )

    def test_history_full(self):
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg)
        self._eq_cmd_output(buf, [
                '%(revb)s -> %(revc)s (head), Rev C',
                '%(reva)s -> %(revb)s, Rev B',
                'None -> %(reva)s, Rev A'
            ])

    def test_history_num_range(self):
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, "%s:%s" % (self.a, self.b))
        self._eq_cmd_output(buf, [
                '%(reva)s -> %(revb)s, Rev B',
            ])

    def test_history_base_to_num(self):
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, ":%s" % (self.b))
        self._eq_cmd_output(buf, [
                '%(reva)s -> %(revb)s, Rev B',
                'None -> %(reva)s, Rev A'
            ])

    def test_history_num_to_head(self):
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, "%s:" % (self.a))
        self._eq_cmd_output(buf, [
                '%(revb)s -> %(revc)s (head), Rev C',
                '%(reva)s -> %(revb)s, Rev B',
            ])

    def test_history_num_plus_relative(self):
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, "%s:+2" % (self.a))
        self._eq_cmd_output(buf, [
                '%(revb)s -> %(revc)s (head), Rev C',
                '%(reva)s -> %(revb)s, Rev B',
            ])

    def test_history_relative_to_num(self):
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, "-2:%s" % (self.c))
        self._eq_cmd_output(buf, [
                '%(revb)s -> %(revc)s (head), Rev C',
                '%(reva)s -> %(revb)s, Rev B',
            ])

    def test_history_current_to_head_as_b(self):
        command.stamp(self.cfg, self.b)
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, "current:")
        self._eq_cmd_output(buf, [
                '%(revb)s -> %(revc)s (head), Rev C',
            ])

    def test_history_current_to_head_as_base(self):
        command.stamp(self.cfg, "base")
        self.cfg.stdout = buf = StringIO()
        command.history(self.cfg, "current:")
        self._eq_cmd_output(buf, [
                '%(revb)s -> %(revc)s (head), Rev C',
                '%(reva)s -> %(revb)s, Rev B',
                'None -> %(reva)s, Rev A'
            ])
