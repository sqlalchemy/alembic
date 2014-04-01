from os import path

__version__ = '0.6.5'

package_dir = path.abspath(path.dirname(__file__))


from . import op
from . import context


