"""${message}"""

# downgrade revision identifier, used by Alembic.
down_revision = ${repr(down_revision)}

from alembic.op import *

def upgrade(engine):
    eval("upgrade_%s" % engine.name)()

% if down_revision:
def downgrade(engine):
    eval("upgrade_%s" % engine.name)()
% else:
# this is the origin node, no downgrade !
% endif


% for engine in ["engine1", "engine2"]:
    def upgrade_${engine}():
        pass

    def downgrade_${engine}():
        pass
% endfor