import os
# use bootstrapping so that test plugins are loaded
# without touching the main library before coverage starts
bootstrap_file = os.path.join(
    os.path.dirname(__file__), "alembic",
    "testing", "plugin", "bootstrap.py"
)

with open(bootstrap_file) as f:
    code = compile(f.read(), "bootstrap.py", 'exec')
    to_bootstrap = "nose"
    exec(code, globals(), locals())


from noseplugin import NoseSQLAlchemy
import nose
nose.main(addplugins=[NoseSQLAlchemy()])
