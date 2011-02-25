from alembic.context import DefaultContext

class MySQLContext(DefaultContext):
    __dialect__ = 'mysql'

