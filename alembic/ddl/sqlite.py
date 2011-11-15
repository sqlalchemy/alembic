from alembic.ddl.impl import DefaultImpl

class SQLiteImpl(DefaultImpl):
    __dialect__ = 'sqlite'
    transactional_ddl = True
