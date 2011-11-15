from alembic.ddl.impl import DefaultImpl

class MySQLImpl(DefaultImpl):
    __dialect__ = 'mysql'

