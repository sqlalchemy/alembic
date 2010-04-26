from alembic.script import ScriptDirectory
from alembic import options, util
import os
import sys
import shutil

def list_templates(opts):
    """List available templates"""
    
    print "Available templates:\n"
    for tempname in os.listdir(opts.get_template_directory()):
        readme = os.path.join(
                        opts.get_template_directory(), 
                        tempname, 
                        'README')
        synopsis = open(readme).next()
        print util.format_opt(tempname, synopsis)
    
    print "\nTemplates are used via the 'init' command, e.g.:"
    print "\n  alembic init --template pylons ./scripts"
    
def init(opts):
    """Initialize a new scripts directory."""
    
    dir_, = opts.get_command_args(1, 'alembic init <directory>')
    if os.access(dir_, os.F_OK):
        opts.err("Directory %s already exists" % dir_)

    util.status("Creating directory %s" % os.path.abspath(dir_),
                os.makedirs, dir_)
    template_dir = os.path.join(opts.get_template_directory(),
                                    opts.cmd_line_options.template)
    if not os.access(template_dir, os.F_OK):
        opts.err("No such template %r" % opts.cmd_line_options.template)
    for file_ in os.listdir(template_dir):
        if file_ == 'alembic.ini.mako':
            config_file = os.path.abspath(opts.cmd_line_options.config)
            util.status("Generating %s" % config_file,
                util.template_to_file,
                os.path.join(template_dir, file_),
                config_file,
                script_location=dir_
            )
        else:
            output_file = os.path.join(dir_, file_)
            util.status("Generating %s" % os.path.abspath(output_file), 
                        shutil.copy, 
                        os.path.join(template_dir, file_), output_file)

    util.msg("\nPlease edit configuration/connection/logging "\
            "settings in %r before proceeding." % config_file)
    
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