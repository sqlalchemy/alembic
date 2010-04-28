from alembic.script import ScriptDirectory
from alembic import util, ddl, context
import os
import functools

def list_templates(config):
    """List available templates"""
    
    print "Available templates:\n"
    for tempname in os.listdir(config.get_template_directory()):
        readme = os.path.join(
                        config.get_template_directory(), 
                        tempname, 
                        'README')
        synopsis = open(readme).next()
        print util.format_opt(tempname, synopsis)
    
    print "\nTemplates are used via the 'init' command, e.g.:"
    print "\n  alembic init --template pylons ./scripts"
    
def init(config, directory, template='generic'):
    """Initialize a new scripts directory."""
    
    if os.access(directory, os.F_OK):
        util.err("Directory %s already exists" % directory)

    template_dir = os.path.join(config.get_template_directory(),
                                    template)
    if not os.access(template_dir, os.F_OK):
        util.err("No such template %r" % template)

    util.status("Creating directory %s" % os.path.abspath(directory),
                os.makedirs, directory)
    
    versions = os.path.join(directory, 'versions')
    util.status("Creating directory %s" % os.path.abspath(versions),
                os.makedirs, versions)

    script = ScriptDirectory(directory)

    for file_ in os.listdir(template_dir):
        if file_ == 'alembic.ini.mako':
            config_file = os.path.abspath(config.config_file_name)
            if os.access(config_file, os.F_OK):
                util.msg("File %s already exists, skipping" % config_file)
            else:
                script.generate_template(
                    os.path.join(template_dir, file_),
                    config_file,
                    script_location=directory
                )
        else:
            output_file = os.path.join(directory, file_)
            script.copy_file(
                os.path.join(template_dir, file_), 
                output_file
            )

    util.msg("Please edit configuration/connection/logging "\
            "settings in %r before proceeding." % config_file)

def revision(config, message=None):
    """Create a new revision file."""

    script = ScriptDirectory.from_config(config)
    script.generate_rev(util.rev_id(), message)
    
def upgrade(config):
    """Upgrade to the latest version."""

    script = ScriptDirectory.from_config(config)
    context._migration_fn = script.upgrade_from
    context.config = config
    script.run_env()
    
def revert(config, revision):
    """Revert to a specific previous version."""
    
    script = ScriptDirectory.from_config(config)
    context._migration_fn = functools.partial(script.downgrade_to, revision)
    script.run_env()

def history(config):
    """List changeset scripts in chronological order."""

    script = ScriptDirectory.from_config(config)
    
def splice(config, parent, child):
    """'splice' two branches, creating a new revision file."""
    
    
def branches(config):
    """Show current un-spliced branch points"""