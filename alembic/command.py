from alembic.script import Script

def main(options, command):
    raise NotImplementedError("yeah yeah nothing here yet")


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

