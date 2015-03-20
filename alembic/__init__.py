from os import path

__version__ = '0.7.5.post2'

package_dir = path.abspath(path.dirname(__file__))


from . import op  # noqa
from . import context  # noqa
