from alembic import util
from sqlalchemy import MetaData, Table, Column, String, literal_column, \
    text
from sqlalchemy import schema, create_engine
from sqlalchemy.util import importlater

import logging
base = importlater("alembic.ddl", "base")
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
    as_sql = False

    def __init__(self, connection, fn, as_sql=False):
        self.connection = connection
        self._migrations_fn = fn
        self.as_sql = as_sql

    def _current_rev(self):
        if self.as_sql:
            if not self.connection.dialect.has_table(self.connection,
                    'alembic_version'):
                self._exec(CreateTable(_version))
                return None
        else:
            _version.create(self.connection, checkfirst=True)
        return self.connection.scalar(_version.select())

    def _update_current_rev(self, old, new):
        if old == new:
            return

        if new is None:
            self._exec(_version.delete())
        elif old is None:
            self._exec(_version.insert().
                        values(version_num=literal_column("'%s'" % new))
                    )
        else:
            self._exec(_version.update().
                        values(version_num=literal_column("'%s'" % new))
                    )

    def run_migrations(self, **kw):
        log.info("Context class %s.", self.__class__.__name__)
        log.info("Will assume %s DDL.", 
                        "transactional" if self.transactional_ddl 
                        else "non-transactional")

        if self.as_sql and self.transactional_ddl:
            print "BEGIN;\n"

        current_rev = prev_rev = rev = self._current_rev()
        for change, rev in self._migrations_fn(current_rev):
            log.info("Running %s %s -> %s", change.__name__, prev_rev, rev)
            change(**kw)
            if not self.transactional_ddl:
                self._update_current_rev(prev_rev, rev)
            prev_rev = rev

        if self.transactional_ddl:
            self._update_current_rev(current_rev, rev)

        if self.as_sql and self.transactional_ddl:
            print "COMMIT;\n"

    def _exec(self, construct):
        if isinstance(construct, basestring):
            construct = text(construct)
        if self.as_sql:
            print unicode(
                    construct.compile(dialect=self.connection.dialect)
                    ).replace("\t", "    ") + ";"
        else:
            self.connection.execute(construct)

    def execute(self, sql):
        self._exec(sql)

    @util.memoized_property
    def _stdout_connection(self):
        def dump(construct, *multiparams, **params):
            self._exec(construct)

        return create_engine(self.connection.engine.url, 
                        strategy="mock", executor=dump)

    @property
    def bind(self):
        """Return a bind suitable for passing to the create() 
        or create_all() methods of MetaData, Table.
        
        Note that when "standard output" mode is enabled, 
        this bind will be a "mock" connection handler that cannot
        return results and is only appropriate for DDL.
        
        """
        if self.as_sql:
            return self._stdout_connection
        else:
            return self.connection

    def alter_column(self, table_name, column_name, 
                        nullable=util.NO_VALUE,
                        server_default=util.NO_VALUE,
                        name=util.NO_VALUE,
                        type=util.NO_VALUE,
                        schema=None,
    ):

        if nullable is not util.NO_VALUE:
            self._exec(base.ColumnNullable(table_name, column_name, nullable, schema=schema))
        if server_default is not util.NO_VALUE:
            self._exec(base.ColumnDefault(
                                table_name, column_name, server_default,
                                schema=schema
                            ))

        # ... etc

    def add_column(self, table_name, column):
        self._exec(base.AddColumn(table_name, column))

    def drop_column(self, table_name, column):
        self._exec(base.DropColumn(table_name, column))

    def add_constraint(self, const):
        self._exec(schema.AddConstraint(const))

    def create_table(self, table):
        self._exec(schema.CreateTable(table))
        for index in table.indexes:
            self._exec(schema.CreateIndex(index))

    def drop_table(self, table):
        self._exec(schema.DropTable(table))

def opts(cfg, **kw):
    global _context_opts, config
    _context_opts = kw
    config = cfg

def configure_connection(connection):
    global _context
    from alembic.ddl import base
    _context = _context_impls.get(
                    connection.dialect.name, 
                    DefaultContext)(connection, **_context_opts)

def run_migrations(**kw):
    _context.run_migrations(**kw)

def get_context():
    return _context