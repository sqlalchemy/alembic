from alembic.ddl import base
from alembic import util

class ContextMeta(type):
    def __init__(cls, classname, bases, dict_):
        newtype = type.__init__(cls, classname, bases, dict_)
        if '__dialect__' in dict_:
            _context_impls[dict_['__dialect__']] = newtype
        return newtype

_context_impls = {}
    
class DefaultContext(object):
    __metaclass__ = ContextMeta
    
    def __init__(self, options, connection):
        self.options = options
        self.connection = connection
    
    def _exec(self, construct):
        pass
        
    def alter_column(self, table_name, column_name, 
                        nullable=util.NO_VALUE,
                        server_default=util.NO_VALUE,
                        name=util.NO_VALUE,
                        type=util.NO_VALUE
    ):
    
        if nullable is not util.NO_VALUE:
            self._exec(base.ColumnNullable(table_name, column_name, nullable))
        if server_default is not util.NO_VALUE:
            self._exec(base.ColumnDefault(table_name, column_name, server_default))
    
        # ... etc
        
    def add_constraint(self, const):
        self._exec(schema.AddConstraint(const))

        