from alembic.ddl import base

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
        
    def alter_column(self, table_name, column_name, 
                        nullable=NO_VALUE,
                        server_default=NO_VALUE,
                        name=NO_VALUE,
                        type=NO_VALUE
    ):
    
        if nullable is not NO_VALUE:
            base.ColumnNullable(table_name, column_name, nullable)
        if server_default is not NO_VALUE:
            base.ColumnDefault(table_name, column_name, server_default)
    
        # ... etc