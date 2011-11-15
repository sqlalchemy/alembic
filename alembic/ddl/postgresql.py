from alembic.ddl.impl import DefaultImpl

class PostgresqlImpl(DefaultImpl):
    __dialect__ = 'postgresql'
    transactional_ddl = True
