from tests import clear_staging_env, staging_env, _sqlite_testing_config, sqlite_db, eq_, ne_
from alembic import command, util
from alembic.script import ScriptDirectory
import time

def test_001_revisions():
    global a, b, c
    a = util.rev_id()
    b = util.rev_id()
    c = util.rev_id()
    
    script = ScriptDirectory.from_config(cfg)
    script.generate_rev(a, None)
    script.write(a, """
down_revision = None

from alembic.op import *

def upgrade():
    execute("CREATE TABLE foo(id integer)")

def downgrade():
    execute("DROP TABLE foo")

""")

    script.generate_rev(b, None)
    script.write(b, """
down_revision = '%s'

from alembic.op import *

def upgrade():
    execute("CREATE TABLE bar(id integer)")

def downgrade():
    execute("DROP TABLE bar")

""" % a)

    script.generate_rev(c, None)
    script.write(c, """
down_revision = '%s'

from alembic.op import *

def upgrade():
    execute("CREATE TABLE bat(id integer)")

def downgrade():
    execute("DROP TABLE bat")

""" % b)
    
    
def test_002_upgrade():
    command.upgrade(cfg, c)
    db = sqlite_db()
    assert db.dialect.has_table(db.connect(), 'foo')
    assert db.dialect.has_table(db.connect(), 'bar')
    assert db.dialect.has_table(db.connect(), 'bat')

def test_003_downgrade():
    command.downgrade(cfg, a)
    db = sqlite_db()
    assert db.dialect.has_table(db.connect(), 'foo')
    assert not db.dialect.has_table(db.connect(), 'bar')
    assert not db.dialect.has_table(db.connect(), 'bat')

def test_004_downgrade():
    command.downgrade(cfg, 'base')
    db = sqlite_db()
    assert not db.dialect.has_table(db.connect(), 'foo')
    assert not db.dialect.has_table(db.connect(), 'bar')
    assert not db.dialect.has_table(db.connect(), 'bat')

def test_005_upgrade():
    command.upgrade(cfg, b)
    db = sqlite_db()
    assert db.dialect.has_table(db.connect(), 'foo')
    assert db.dialect.has_table(db.connect(), 'bar')
    assert not db.dialect.has_table(db.connect(), 'bat')

# TODO: test some invalid movements


def setup():
    global cfg, env
    env = staging_env()
    cfg = _sqlite_testing_config()
    
    
def teardown():
    clear_staging_env()