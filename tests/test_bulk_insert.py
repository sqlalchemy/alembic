from tests import op_fixture, eq_, assert_raises_message
from alembic import op
from sqlalchemy import Integer, String
from sqlalchemy.sql import table, column
from unittest import TestCase
from sqlalchemy import Table, Column, MetaData

def _table_fixture(dialect, as_sql):
    context = op_fixture(dialect, as_sql)
    t1 = table("ins_table",
                column('id', Integer),
                column('v1', String()),
                column('v2', String()),
    )
    return context, t1

def _big_t_table_fixture(dialect, as_sql):
    context = op_fixture(dialect, as_sql)
    t1 = Table("ins_table", MetaData(),
                Column('id', Integer, primary_key=True),
                Column('v1', String()),
                Column('v2', String()),
    )
    return context, t1

def _test_bulk_insert(dialect, as_sql):
    context, t1 = _table_fixture(dialect, as_sql)

    op.bulk_insert(t1, [
        {'id':1, 'v1':'row v1', 'v2':'row v5'},
        {'id':2, 'v1':'row v2', 'v2':'row v6'},
        {'id':3, 'v1':'row v3', 'v2':'row v7'},
        {'id':4, 'v1':'row v4', 'v2':'row v8'},
    ])
    return context

def _test_bulk_insert_single(dialect, as_sql):
    context, t1 = _table_fixture(dialect, as_sql)

    op.bulk_insert(t1, [
        {'id':1, 'v1':'row v1', 'v2':'row v5'},
    ])
    return context

def _test_bulk_insert_single_bigt(dialect, as_sql):
    context, t1 = _big_t_table_fixture(dialect, as_sql)

    op.bulk_insert(t1, [
        {'id':1, 'v1':'row v1', 'v2':'row v5'},
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
    context.assert_(
        'INSERT INTO ins_table (id, v1, v2) VALUES (%(id)s, %(v1)s, %(v2)s)'
    )

def test_bulk_insert_pg():
    context = _test_bulk_insert('postgresql', False)
    context.assert_(
        'INSERT INTO ins_table (id, v1, v2) VALUES (%(id)s, %(v1)s, %(v2)s)'
    )

def test_bulk_insert_pg_single():
    context = _test_bulk_insert_single('postgresql', False)
    context.assert_(
        'INSERT INTO ins_table (id, v1, v2) VALUES (%(id)s, %(v1)s, %(v2)s)'
    )

def test_bulk_insert_pg_single_as_sql():
    context = _test_bulk_insert_single('postgresql', True)
    context.assert_(
        "INSERT INTO ins_table (id, v1, v2) VALUES (1, 'row v1', 'row v5')"
    )

def test_bulk_insert_pg_single_big_t_as_sql():
    context = _test_bulk_insert_single_bigt('postgresql', True)
    context.assert_(
        "INSERT INTO ins_table (id, v1, v2) VALUES (1, 'row v1', 'row v5')"
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

def test_invalid_format():
    context, t1 = _table_fixture("sqlite", False)
    assert_raises_message(
        TypeError,
        "List expected",
        op.bulk_insert, t1, {"id":5}
    )

    assert_raises_message(
        TypeError,
        "List of dictionaries expected",
        op.bulk_insert, t1, [(5, )]
    )

class RoundTripTest(TestCase):
    def setUp(self):
        from sqlalchemy import create_engine
        from alembic.migration import MigrationContext
        self.conn = create_engine("sqlite://").connect()
        self.conn.execute("""
            create table foo(
                id integer primary key,
                data varchar(50),
                x integer
            )
        """)
        context = MigrationContext.configure(self.conn)
        self.op = op.Operations(context)
        self.t1 = table('foo',
                column('id'),
                column('data'),
                column('x')
        )
    def tearDown(self):
        self.conn.close()

    def test_single_insert_round_trip(self):
        self.op.bulk_insert(self.t1,
            [{'data':"d1", "x":"x1"}]
        )

        eq_(
            self.conn.execute("select id, data, x from foo").fetchall(),
            [
                (1, "d1", "x1"),
            ]
        )

    def test_bulk_insert_round_trip(self):
        self.op.bulk_insert(self.t1, [
            {'data':"d1", "x":"x1"},
            {'data':"d2", "x":"x2"},
            {'data':"d3", "x":"x3"},
        ])

        eq_(
            self.conn.execute("select id, data, x from foo").fetchall(),
            [
                (1, "d1", "x1"),
                (2, "d2", "x2"),
                (3, "d3", "x3")
            ]
        )

