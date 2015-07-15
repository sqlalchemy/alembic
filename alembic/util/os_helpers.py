from os.path import join, exists
from subprocess import check_call
import os


def open_in_editor(filename, environ=None):
    '''
    Opens the given file in a text editor. If the environment vaiable ``EDITOR``
    is set, this is taken as preference.

    Otherwise, a list of commonly installed editors is tried.

    If no editor matches, an :py:exc:`OSError` is raised.

    :param filename: The filename to open. Will be passed  verbatim to the
        editor command.
    :param environ: An optional drop-in replacement for ``os.environ``. Used
        mainly for testing.
    '''

    environ = environ or os.environ

    # Look for an editor. Prefer the user's choice by env-var, fall back to most
    # commonly installed editor (nano/vim)
    candidates = [
        '/usr/bin/sensible-editor',
        '/usr/bin/nano',
        '/usr/bin/vim',
    ]

    if 'EDITOR' in environ:
        user_choice = environ['EDITOR']
        if '/' not in user_choice:
            # Assuming this is on the PATH, we need to determine it's absolute
            # location. Otherwise, ``check_call`` will fail
            for path in environ.get('PATH', '').split(os.pathsep):
                if exists(join(path, user_choice)):
                    user_choice = join(path, user_choice)
                    break
        candidates.insert(0, user_choice)

    for path in candidates:
        if exists(path):
            editor = path
            break
    else:
        raise OSError('No suitable editor found. Please set the '
                      '"EDITOR" environment variable')
    check_call([editor, filename])
