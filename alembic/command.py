from alembic.script import ScriptDirectory
from alembic import options

def main(argv=None):

    parser = options.get_option_parser()

    opts, args = parser.parse_args(argv[1:])
    if len(args) < 1:
        parser.error("no command specified") # Will exit

    print opts.config

def list_templates(options):
    """List available templates"""
    
def init(options):
    """Initialize a new scripts directory."""
    
    script = ScriptDirectory(options)
    script.init()
    
def upgrade(options):
    """Upgrade to the latest version."""

    script = ScriptDirectory(options)
    
    # ...
    
def revert(options, file_config):
    """Revert to a specific previous version."""
    
    script = ScriptDirectory(options)

    # ...

