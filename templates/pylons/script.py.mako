"""${message}"""

from alembic.op import *

def upgrade_${up_revision}():
    pass

% if down_revision:
def downgrade_${down_revision}():
    pass
% else:
# this is the origin node, no downgrade !
% endif
