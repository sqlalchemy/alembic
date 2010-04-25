from alembic.context import DefaultContext

class PostgresqlContext(DefaultContext):
    __dialect__ = 'postgresql'
    
    