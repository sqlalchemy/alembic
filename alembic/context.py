from alembic.ddl import base
from alembic import util
from sqlalchemy import MetaData, Table, Column, String
import logging

log = logging.getLogger(__name__)

class ContextMeta(type):
    def __init__(cls, classname, bases, dict_):
        newtype = type.__init__(cls, classname, bases, dict_)
        if '__dialect__' in dict_:
            _context_impls[dict_['__dialect__']] = cls
        return newtype

_context_impls = {}

_meta = MetaData()
_version = Table('alembic_version', _meta, 
                Column('version_num', String(32), nullable=False)
            )

class DefaultContext(object):
    __metaclass__ = ContextMeta
    __dialect__ = 'default'
    
    transactional_ddl = False
    
    def __init__(self, connection, fn):
        self.connection = connection
        self._migrations_fn = fn
        
    def _current_rev(self):
        _version.create(self.connection, checkfirst=True)
        return self.connection.scalar(_version.select())
    
    def _update_current_rev(self, old, new):
        if old == new:
            return
            
        if new is None:
            self.connection.execute(_version.delete())
        elif old is None:
            self.connection.execute(_version.insert(), {'version_num':new})
        else:
            self.connection.execute(_version.update(), {'version_num':new})
            
    def run_migrations(self, **kw):
        log.info("Context class %s.", self.__class__.__name__)
        log.info("Will assume %s DDL.", 
                        "transactional" if self.transactional_ddl 
                        else "non-transactional")
        current_rev = prev_rev = rev = self._current_rev()
        for change, rev in self._migrations_fn(current_rev):
            log.info("Running %s %s -> %s", change.__name__, prev_rev, rev)
            change(**kw)
            if not self.transactional_ddl:
                self._update_current_rev(prev_rev, rev)
            prev_rev = rev
            
        if self.transactional_ddl:
            self._update_current_rev(current_rev, rev)
        
    def _exec(self, construct):
        self.connection.execute(construct)
    
    def execute(self, sql):
        self._exec(sql)
        
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


def configure_connection(connection):
    global _context
    _context = _context_impls.get(connection.dialect.name, DefaultContext)(connection, _migration_fn)
    
def run_migrations(**kw):
    _context.run_migrations(**kw)

def get_context():
    return _context