"""
Bootstrapper for test framework plugins.

This is vendored from SQLAlchemy so that we can use local overrides
for plugin_base.py and pytestplugin.py.

"""


import os
import sys


bootstrap_file = locals()["bootstrap_file"]
to_bootstrap = locals()["to_bootstrap"]


def load_file_as_module(name):
    path = os.path.join(os.path.dirname(bootstrap_file), "%s.py" % name)
    if sys.version_info >= (3, 3):
        from importlib import machinery

        mod = machinery.SourceFileLoader(name, path).load_module()
    else:
        import imp

        mod = imp.load_source(name, path)
    return mod


if to_bootstrap == "pytest":
    sys.modules["sqla_plugin_base"] = load_file_as_module("plugin_base")
    sys.modules["sqla_pytestplugin"] = load_file_as_module("pytestplugin")
else:
    raise Exception("unknown bootstrap: %s" % to_bootstrap)  # noqa
