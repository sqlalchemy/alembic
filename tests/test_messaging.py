from io import StringIO

from alembic.testing import eq_
from alembic.testing import mock
from alembic.testing.fixtures import TestBase
from alembic.util.messaging import msg
from alembic.util.messaging import obfuscate_url_pw


class MessagingTest(TestBase):
    def test_msg_wraps(self):
        buf = StringIO()
        with (
            mock.patch("sys.stdout", buf),
            mock.patch("alembic.util.messaging.TERMWIDTH", 10),
        ):
            msg("AAAAAAAAAAAAAAAAA")
        eq_(
            str(buf.getvalue()).splitlines(),
            [
                "  AAAAAAAA",  # initial indent 10 chars before wrapping
                "  AAAAAAAA",  # subsequent indent 10 chars before wrapping
                "  A",  # subsequent indent with remainining chars
            ],
        )

    def test_current_obfuscate_password(self):
        eq_(
            obfuscate_url_pw("postgresql://scott:tiger@localhost/test"),
            "postgresql://scott:***@localhost/test",
        )
