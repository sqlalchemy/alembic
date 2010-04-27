from alembic.op import *

def upgrade_${up_revision}(engine):
    eval("upgrade_%s_${up_revision}" % engine.name)()

% if down_revision:
def downgrade_${down_revision}(engine):
    eval("upgrade_%s_${down_revision}" % engine.name)()
% else:
# this is the origin node, no downgrade !
% endif


% for engine in ["engine1", "engine2"]:
    def upgrade_${engine}_${up_revision}():
        pass

    def downgrade_${engine}_${down_revision}():
        pass
% endfor