from tests import op_fixture
from alembic import op
from sqlalchemy import Integer, \
            UniqueConstraint, String
from sqlalchemy.sql import table, column

def _test_bulk_insert(dialect, as_sql):
    context = op_fixture(dialect, as_sql)
    t1 = table("ins_table",
                column('id', Integer),
                column('v1', String()),
                column('v2', String()),
    )
    op.bulk_insert(t1, [
        {'id':1, 'v1':'row v1', 'v2':'row v5'},
        {'id':2, 'v1':'row v2', 'v2':'row v6'},
        {'id':3, 'v1':'row v3', 'v2':'row v7'},
        {'id':4, 'v1':'row v4', 'v2':'row v8'},
    ])
    return context

def test_bulk_insert():
    context = _test_bulk_insert('default', False)
    context.assert_(
        'INSERT INTO ins_table (id, v1, v2) VALUES (:id, :v1, :v2)'
    )

def test_bulk_insert_wrong_cols():
    context = op_fixture('postgresql')
    t1 = table("ins_table", 
                column('id', Integer),
                column('v1', String()),
                column('v2', String()),
    )
    op.bulk_insert(t1, [
        {'v1':'row v1', },
    ])
    # TODO: this is wrong because the test fixture isn't actually 
    # doing what the real context would do.   Sending this to 
    # PG is going to produce a RETURNING clause.  fixture would
    # need to be beefed up
    context.assert_(
        'INSERT INTO ins_table (id, v1, v2) VALUES (%(id)s, %(v1)s, %(v2)s)'
    )

def test_bulk_insert_pg():
    context = _test_bulk_insert('postgresql', False)
    context.assert_(
        'INSERT INTO ins_table (id, v1, v2) VALUES (%(id)s, %(v1)s, %(v2)s)'
    )

def test_bulk_insert_mssql():
    context = _test_bulk_insert('mssql', False)
    context.assert_(
        'INSERT INTO ins_table (id, v1, v2) VALUES (:id, :v1, :v2)'
    )

def test_bulk_insert_as_sql():
    context = _test_bulk_insert('default', True)
    context.assert_(
        "INSERT INTO ins_table (id, v1, v2) VALUES (1, 'row v1', 'row v5')", 
        "INSERT INTO ins_table (id, v1, v2) VALUES (2, 'row v2', 'row v6')", 
        "INSERT INTO ins_table (id, v1, v2) VALUES (3, 'row v3', 'row v7')",
        "INSERT INTO ins_table (id, v1, v2) VALUES (4, 'row v4', 'row v8')"
    )

def test_bulk_insert_as_sql_pg():
    context = _test_bulk_insert('postgresql', True)
    context.assert_(
        "INSERT INTO ins_table (id, v1, v2) VALUES (1, 'row v1', 'row v5')", 
        "INSERT INTO ins_table (id, v1, v2) VALUES (2, 'row v2', 'row v6')", 
        "INSERT INTO ins_table (id, v1, v2) VALUES (3, 'row v3', 'row v7')",
        "INSERT INTO ins_table (id, v1, v2) VALUES (4, 'row v4', 'row v8')"
    )

def test_bulk_insert_as_sql_mssql():
    context = _test_bulk_insert('mssql', True)
    # SQL server requires IDENTITY_INSERT
    # TODO: figure out if this is safe to enable for a table that 
    # doesn't have an IDENTITY column
    context.assert_(
        'SET IDENTITY_INSERT ins_table ON', 
        "INSERT INTO ins_table (id, v1, v2) VALUES (1, 'row v1', 'row v5')", 
        "INSERT INTO ins_table (id, v1, v2) VALUES (2, 'row v2', 'row v6')", 
        "INSERT INTO ins_table (id, v1, v2) VALUES (3, 'row v3', 'row v7')", 
        "INSERT INTO ins_table (id, v1, v2) VALUES (4, 'row v4', 'row v8')", 
        'SET IDENTITY_INSERT ins_table OFF'
    )
