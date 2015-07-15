from alembic import util
from alembic.testing import assert_raises_message
from alembic.testing.fixtures import TestBase

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch  # noqa


class TestHelpers(TestBase):

    def test_edit_with_user_editor(self):
        test_environ = {
            'EDITOR': 'myvim',
            'PATH': '/usr/bin'
        }

        with patch('alembic.util.os_helpers.check_call') as check_call, \
                patch('alembic.util.os_helpers.exists') as exists:
            exists.side_effect = lambda fname: fname == '/usr/bin/myvim'
            util.open_in_editor('myfile', test_environ)
            check_call.assert_called_with(['/usr/bin/myvim', 'myfile'])

    def test_edit_with_default_editor(self):
        test_environ = {}

        with patch('alembic.util.os_helpers.check_call') as check_call, \
                patch('alembic.util.os_helpers.exists') as exists:
            exists.side_effect = lambda fname: fname == '/usr/bin/vim'
            util.open_in_editor('myfile', test_environ)
            check_call.assert_called_with(['/usr/bin/vim', 'myfile'])

    def test_edit_with_missing_editor(self):
        test_environ = {}
        with patch('alembic.util.os_helpers.check_call'), \
                patch('alembic.util.os_helpers.exists') as exists:
            exists.return_value = False
            assert_raises_message(
                OSError,
                'EDITOR',
                util.open_in_editor,
                'myfile',
                test_environ)
