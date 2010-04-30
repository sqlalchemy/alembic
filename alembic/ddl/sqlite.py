from alembic.context import DefaultContext

class SQLiteContext(DefaultContext):
    __dialect__ = 'sqlite'
    transactional_ddl = True
