"""${message}"""

# downgrade revision identifier, used by Alembic.
down_revision = ${repr(down_revision)}

from alembic.op import *

def upgrade():
    pass

% if down_revision:
def downgrade():
    pass
% else:
# this is the origin node, no downgrade !
% endif
