from tests import op_fixture, assert_raises_message
from alembic import op, util
from sqlalchemy import Integer, func

def test_rename_column():
    context = op_fixture('mysql')
    op.alter_column('t1', 'c1', new_column_name="c2", existing_type=Integer)
    context.assert_(
        'ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL'
    )

def test_rename_column_serv_default():
    context = op_fixture('mysql')
    op.alter_column('t1', 'c1', new_column_name="c2", existing_type=Integer,
                        existing_server_default="q")
    context.assert_(
        "ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL DEFAULT 'q'"
    )

def test_rename_column_serv_compiled_default():
    context = op_fixture('mysql')
    op.alter_column('t1', 'c1', new_column_name="c2", existing_type=Integer,
            existing_server_default=func.utc_thing(func.current_timestamp()))
    # this is not a valid MySQL default but the point is to just
    # test SQL expression rendering
    context.assert_(
        "ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL DEFAULT utc_thing(CURRENT_TIMESTAMP)"
    )

def test_rename_column_autoincrement():
    context = op_fixture('mysql')
    op.alter_column('t1', 'c1', new_column_name="c2", existing_type=Integer,
                                existing_autoincrement=True)
    context.assert_(
        'ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL AUTO_INCREMENT'
    )

def test_col_add_autoincrement():
    context = op_fixture('mysql')
    op.alter_column('t1', 'c1', new_column_name="c2", existing_type=Integer,
                                autoincrement=True)
    context.assert_(
        'ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL AUTO_INCREMENT'
    )

def test_col_remove_autoincrement():
    context = op_fixture('mysql')
    op.alter_column('t1', 'c1', new_column_name="c2", existing_type=Integer,
                                existing_autoincrement=True,
                                autoincrement=False)
    context.assert_(
        'ALTER TABLE t1 CHANGE c1 c2 INTEGER NULL'
    )

def test_col_nullable():
    context = op_fixture('mysql')
    op.alter_column('t1', 'c1', nullable=False, existing_type=Integer)
    context.assert_(
        'ALTER TABLE t1 CHANGE c1 c1 INTEGER NOT NULL'
    )

def test_col_multi_alter():
    context = op_fixture('mysql')
    op.alter_column('t1', 'c1', nullable=False, server_default="q", type_=Integer)
    context.assert_(
        "ALTER TABLE t1 CHANGE c1 c1 INTEGER NOT NULL DEFAULT 'q'"
    )


def test_col_alter_type_required():
    context = op_fixture('mysql')
    assert_raises_message(
        util.CommandError,
        "All MySQL ALTER COLUMN operations require the existing type.",
        op.alter_column, 't1', 'c1', nullable=False, server_default="q"
    )

def test_drop_fk():
    context = op_fixture('mysql')
    op.drop_constraint("f1", "t1", "foreignkey")
    context.assert_(
        "ALTER TABLE t1 DROP FOREIGN KEY f1"
    )

def test_drop_constraint_primary():
    context = op_fixture('mysql')
    op.drop_constraint('primary', 't1', type_='primary')
    context.assert_(
        "ALTER TABLE t1 DROP PRIMARY KEY "
    )

def test_drop_unique():
    context = op_fixture('mysql')
    op.drop_constraint("f1", "t1", "unique")
    context.assert_(
        "ALTER TABLE t1 DROP INDEX f1"
    )

def test_drop_check():
    context = op_fixture('mysql')
    assert_raises_message(
        NotImplementedError,
        "MySQL does not support CHECK constraints.",
        op.drop_constraint, "f1", "t1", "check"
    )

def test_drop_unknown():
    context = op_fixture('mysql')
    assert_raises_message(
        TypeError,
        "'type' can be one of 'check', 'foreignkey', "
        "'primary', 'unique', None",
        op.drop_constraint, "f1", "t1", "typo"
    )

def test_drop_generic_constraint():
    context = op_fixture('mysql')
    assert_raises_message(
        NotImplementedError,
        "No generic 'DROP CONSTRAINT' in MySQL - please "
        "specify constraint type",
        op.drop_constraint, "f1", "t1"
    )
