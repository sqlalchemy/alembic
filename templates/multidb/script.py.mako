"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""

# downgrade revision identifier, used by Alembic.
down_revision = ${repr(down_revision)}

from alembic.op import *

def upgrade(engine):
    eval("upgrade_%s" % engine.name)()

def downgrade(engine):
    eval("upgrade_%s" % engine.name)()


% for engine in ["engine1", "engine2"]:
    def upgrade_${engine}():
        pass

    def downgrade_${engine}():
        pass
% endfor