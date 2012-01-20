from alembic import config
from tests import eq_

def test_config_no_file_main_option():
    cfg = config.Config()
    cfg.set_main_option("url", "postgresql://foo/bar")

    eq_(cfg.get_main_option("url"), "postgresql://foo/bar")


def test_config_no_file_section_option():
    cfg = config.Config()
    cfg.set_section_option("foo", "url", "postgresql://foo/bar")

    eq_(cfg.get_section_option("foo", "url"), "postgresql://foo/bar")

    cfg.set_section_option("foo", "echo", "True")
    eq_(cfg.get_section_option("foo", "echo"), "True")