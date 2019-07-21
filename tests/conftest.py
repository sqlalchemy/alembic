#!/usr/bin/env python
"""
pytest plugin script.

This script is an extension to py.test which
installs SQLAlchemy's testing plugin into the local environment.

"""
import os

import sqlalchemy

# ideally, SQLAlchemy would allow us to just import bootstrap,
# but for now we have to use its "load from a file" approach

bootstrap_file = os.path.join(
    os.path.dirname(sqlalchemy.__file__), "testing", "plugin", "bootstrap.py"
)

with open(bootstrap_file) as f:
    code = compile(f.read(), "bootstrap.py", "exec")
    to_bootstrap = "pytest"
    exec(code, globals(), locals())
    from pytestplugin import *  # noqa
