from alembic.script import ScriptDirectory
from alembic import options
import os
import sys

def _status(msg, fn, *arg, **kw):
    sys.stdout.write("  " + msg + "...")
    try:
        ret = fn(*arg, **kw)
        sys.stdout.write("done\n")
        return ret
    except:
        sys.stdout.write("FAILED\n")
        raise
    
def list_templates(opts):
    """List available templates"""
    
    print "Available templates:\n"
    for tempname in os.listdir(opts.get_template_directory()):
        readme = os.path.join(
                        opts.get_template_directory(), 
                        tempname, 
                        'README')
        synopsis = open(readme).next()
        print options.format_opt(tempname, synopsis)
    
    print "\nTemplates are used via the 'init' command, e.g.:"
    print "\n  alembic init --template pylons ./scripts"
    
def init(opts):
    """Initialize a new scripts directory."""
    
    dir_, = opts.get_command_args(1, 'alembic init <directory>')
    if not _status("Checking for directory %s" % dir_, 
                        os.access, dir_, os.F_OK):
        _status("Creating directory %s" % dir_,
                    os.makedirs, dir_)
    else:
        opts.err("Directory %s already exists" % dir_)
    # copy files...
    
def upgrade(opts):
    """Upgrade to the latest version."""

    script = ScriptDirectory.from_options(opts)
    
    # ...
    
def revert(opts):
    """Revert to a specific previous version."""
    
    script = ScriptDirectory.from_options(opts)

    # ...

def history(opts):
    """List changeset scripts in chronological order."""

    script = ScriptDirectory.from_options(opts)
    
def splice(opts):
    """'splice' two branches, creating a new revision file."""
    
def revision(opts):
    """Create a new revision file."""
    
def branches(opts):
    """Show current un-spliced branch points"""