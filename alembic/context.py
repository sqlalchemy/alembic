from alembic import util
from sqlalchemy import MetaData, Table, Column, String, literal_column, \
    text
from sqlalchemy import schema, create_engine
from sqlalchemy.engine import url as sqla_url
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import _BindParamClause
import sys

import logging
base = util.importlater("alembic.ddl", "base")
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

    def __init__(self, dialect, connection, fn, as_sql=False, 
                        output_buffer=None,
                        transactional_ddl=None):
        self.dialect = dialect
        if as_sql:
            self.connection = self._stdout_connection(connection)
            assert self.connection is not None
        else:
            self.connection = connection
        self._migrations_fn = fn
        self.as_sql = as_sql
        if output_buffer is None:
            self.output_buffer = sys.stdout
        else:
            self.output_buffer = output_buffer
        if transactional_ddl is not None:
            self.transactional_ddl = transactional_ddl

    def _current_rev(self):
        if self.as_sql:
            # TODO: no coverage here !
            # TODO: what if migrations table is needed on remote DB ?? 
            # need an option
            raise Exception("revisions must be specified with --sql")
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
        if self.as_sql:
            log.info("Generating static SQL")
        log.info("Will assume %s DDL.", 
                        "transactional" if self.transactional_ddl 
                        else "non-transactional")

        if self.as_sql and self.transactional_ddl:
            self.static_output("BEGIN;")

        current_rev = rev = False
        for change, prev_rev, rev in self._migrations_fn(
                                        self._current_rev() 
                                        if not self.as_sql else None):
            if current_rev is False:
                current_rev = prev_rev
                if self.as_sql and not current_rev:
                    _version.create(self.connection)
            log.info("Running %s %s -> %s", change.__name__, prev_rev, rev)
            change(**kw)
            if not self.transactional_ddl:
                self._update_current_rev(prev_rev, rev)
            prev_rev = rev

        if rev is not False:
            if self.transactional_ddl:
                self._update_current_rev(current_rev, rev)

            if self.as_sql and not rev:
                _version.drop(self.connection)

        if self.as_sql and self.transactional_ddl:
            self.static_output("COMMIT;")

    def _exec(self, construct, *args, **kw):
        if isinstance(construct, basestring):
            construct = text(construct)
        if self.as_sql:
            if args or kw:
                # TODO: coverage
                raise Exception("Execution arguments not allowed with as_sql")
            self.static_output(unicode(
                    construct.compile(dialect=self.dialect)
                    ).replace("\t", "    ").strip() + ";")
        else:
            self.connection.execute(construct, *args, **kw)

    def static_output(self, text):
        self.output_buffer.write(text + "\n\n")

    def execute(self, sql):
        self._exec(sql)

    def _stdout_connection(self, connection):
        def dump(construct, *multiparams, **params):
            self._exec(construct)

        return create_engine("%s://" % self.dialect.name, 
                        strategy="mock", executor=dump)

    @property
    def bind(self):
        """Return a bind suitable for passing to the create() 
        or create_all() methods of MetaData, Table.
        
        Note that when "standard output" mode is enabled, 
        this bind will be a "mock" connection handler that cannot
        return results and is only appropriate for DDL.
        
        """
        return self.connection

    def alter_column(self, table_name, column_name, 
                        nullable=None,
                        server_default=False,
                        name=None,
                        type_=None,
                        schema=None,
    ):

        if nullable is not None:
            self._exec(base.ColumnNullable(table_name, column_name, 
                                nullable, schema=schema))
        if server_default is not False:
            self._exec(base.ColumnDefault(
                                table_name, column_name, server_default,
                                schema=schema
                            ))
        if type_ is not None:
            self._exec(base.ColumnType(
                                table_name, column_name, type_, schema=schema
                            ))

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

    def bulk_insert(self, table, rows):
        if self.as_sql:
            for row in rows:
                self._exec(table.insert().values(**dict(
                    (k, _literal_bindparam(k, v, type_=table.c[k].type))
                    for k, v in row.items()
                )))
        else:
            self._exec(table.insert(), *rows)

class _literal_bindparam(_BindParamClause):
    pass

@compiles(_literal_bindparam)
def _render_literal_bindparam(element, compiler, **kw):
    return compiler.render_literal_bindparam(element, **kw)

_context_opts = {}
_context = None

def opts(cfg, **kw):
    """Set up options that will be used by the :func:`.configure_connection`
    function.
    
    This basically sets some global variables.
    
    """
    global config
    _context_opts.update(kw)
    config = cfg

def requires_connection():
    """Return True if the current migrations environment should have
    an active database connection.
    
    """
    return not _context_opts.get('as_sql', False)

def configure(
        connection=None,
        url=None,
        dialect_name=None,
        transactional_ddl=None,
        output_buffer=None
    ):
    """Configure the migration environment.
    
    The important thing needed here is first a way to figure out
    what kind of "dialect" is in use.   The second is to pass
    an actual database connection, if one is required.
    
    If the :func:`requires_connection` function returns False,
    then no connection is needed here.  Otherwise, the
    object should be an instance of :class:`sqlalchemy.engine.Connection`.
    
    This function is typically called from the ``env.py``
    script within a migration environment.  It can be called
    multiple times for an invocation.  The most recent :class:`~sqlalchemy.engine.Connection`
    for which it was called is the one that will be operated upon
    by the next call to :func:`.run_migrations`.
    
    :param connection: a :class:`sqlalchemy.engine.Connection`.  The type of dialect
     to be used will be derived from this.
    :param url: a string database url, or a :class:`sqlalchemy.engine.url.URL` object.
     The type of dialect to be used will be derived from this if ``connection`` is
     not passed.
    :param dialect_name: string name of a dialect, such as "postgresql", "mssql", etc.
     The type of dialect to be used will be derived from this if ``connection``
     and ``url`` are not passed.
    :param transactional_ddl: Force the usage of "transactional" DDL on or off;
     this otherwise defaults to whether or not the dialect in use supports it.
    :param output_buffer: a file-like object that will be used for textual output
     when the ``--sql`` option is used to generate SQL scripts.  Defaults to
     ``sys.stdout`` it not passed here.
    """

    if connection:
        dialect = connection.dialect
    elif url:
        url = sqla_url.make_url(url)
        dialect = url.get_dialect()()
    elif dialect_name:
        url = sqla_url.make_url("%s://" % dialect_name)
        dialect = url.get_dialect()()
    else:
        raise Exception("Connection, url, or dialect_name is required.")

    global _context
    from alembic.ddl import base
    opts = _context_opts.copy()
    opts.setdefault("transactional_ddl", transactional_ddl)
    opts.setdefault("output_buffer", output_buffer)
    _context = _context_impls.get(
                    dialect.name, 
                    DefaultContext)(dialect, connection, **opts)

def configure_connection(connection):
    """Deprecated; use :func:`alembic.context.configure`."""
    configure(connection=connection)

def run_migrations(**kw):
    """Run migrations as determined by the current command line configuration
    as well as versioning information present (or not) in the current 
    database connection (if one is present).
    """
    _context.run_migrations(**kw)

def execute(sql):
    """Execute the given SQL using the current change context.
    
    In a SQL script context, the statement is emitted directly to the 
    output stream.
    
    """
    get_context().execute(sql)

def get_context():
    if _context is None:
        raise Exception("No context has been configured yet.")
    return _context