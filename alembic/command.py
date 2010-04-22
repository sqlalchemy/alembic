from alembic.script import Script

def main(options, file_config, command):
    raise NotImplementedError("yeah yeah nothing here yet")


def init(options, file_config):
    """Initialize a new scripts directory."""
    
    script = Script(options, file_config)
    script.init()
    
def upgrade(options, file_config):
    """Upgrade to the latest version."""

    script = Script(options, file_config)
    
def revert(options, file_config):
    """Revert to a specific previous version."""
    
    script = Script(options, file_config)


