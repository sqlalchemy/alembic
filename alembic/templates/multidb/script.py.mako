"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

def upgrade(engine):
    eval("upgrade_%s" % engine.name)()

def downgrade(engine):
    eval("upgrade_%s" % engine.name)()


% for engine in ["engine1", "engine2"]:

def upgrade_${engine}():
    ${context.get("%s_upgrades" % engine, "pass")}

def downgrade_${engine}():
    ${context.get("%s_downgrades" % engine, "pass")}

% endfor