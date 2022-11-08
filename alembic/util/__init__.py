from .editor import open_in_editor
from .exc import CommandError
from .langhelpers import _with_legacy_names
from .langhelpers import asbool
from .langhelpers import dedupe_tuple
from .langhelpers import Dispatcher
from .langhelpers import immutabledict
from .langhelpers import memoized_property
from .langhelpers import ModuleClsProxy
from .langhelpers import not_none
from .langhelpers import rev_id
from .langhelpers import to_list
from .langhelpers import to_tuple
from .langhelpers import unique_list
from .messaging import err
from .messaging import format_as_comma
from .messaging import msg
from .messaging import obfuscate_url_pw
from .messaging import status
from .messaging import warn
from .messaging import write_outstream
from .pyfiles import coerce_resource_to_filename
from .pyfiles import load_python_file
from .pyfiles import pyc_file_from_path
from .pyfiles import template_to_file
from .sqla_compat import has_computed
from .sqla_compat import sqla_13
from .sqla_compat import sqla_14
from .sqla_compat import sqla_1x


if not sqla_13:
    raise CommandError("SQLAlchemy 1.3.0 or greater is required.")
