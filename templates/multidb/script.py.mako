from alembic.op import *

% for engine in engines:
def upgrade_${engine}_${up_revision}():
    pass

def downgrade_${engine}_${down_revision}():
    pass
% endfor