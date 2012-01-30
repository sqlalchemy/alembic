from alembic import util
from sqlalchemy import MetaData, Table, Column, String, literal_column, \
    text
from sqlalchemy import create_engine
from alembic import ddl
import sys
from sqlalchemy.engine import url as sqla_url

import logging
log = logging.getLogger(__name__)

_meta = MetaData()
_version = Table('alembic_version', _meta, 
                Column('version_num', String(32), nullable=False)
            )

class MigrationContext(object):
    """Represent the state made available to a migration script,
    or otherwise a series of migration operations.

    Mediates the relationship between an ``env.py`` environment script, 
    a :class:`.ScriptDirectory` instance, and a :class:`.DefaultImpl` instance.

    The :class:`.MigrationContext` that's established for a 
    duration of a migration command is available via the 
    :meth:`.EnvironmentContext.get_context` method,
    which is available at ``alembic.context``::
    
        from alembic import context
        migration_context = context.get_context()
    
    A :class:`.MigrationContext` can be created programmatically
    for usage outside of the usual Alembic migrations flow,
    using the :meth:`.MigrationContext.configure` method::
    
        conn = myengine.connect()
        ctx = MigrationContext.configure(conn)
    
    The above context can then be used to produce
    Alembic migration operations with an :class:`.Operations`
    instance.
    

    """
    def __init__(self, dialect, connection, opts):
        self.opts = opts
        self.dialect = dialect
        self.script = opts.get('script')

        as_sql=opts.get('as_sql', False)
        transactional_ddl=opts.get("transactional_ddl")

        if as_sql:
            self.connection = self._stdout_connection(connection)
            assert self.connection is not None
        else:
            self.connection = connection
        self._migrations_fn = opts.get('fn')
        self.as_sql = as_sql
        self.output_buffer = opts.get("output_buffer", sys.stdout)

        self._user_compare_type = opts.get('compare_type', False)
        self._user_compare_server_default = opts.get(
                                            'compare_server_default', 
                                            False)

        self._start_from_rev = opts.get("starting_rev")
        self.impl = ddl.DefaultImpl.get_by_dialect(dialect)(
                            dialect, self.connection, self.as_sql,
                            transactional_ddl,
                            self.output_buffer,
                            opts
                            )
        log.info("Context impl %s.", self.impl.__class__.__name__)
        if self.as_sql:
            log.info("Generating static SQL")
        log.info("Will assume %s DDL.", 
                        "transactional" if self.impl.transactional_ddl 
                        else "non-transactional")

    @classmethod
    def configure(cls,
                connection=None,
                url=None,
                dialect_name=None,
                opts={},
    ):
        """Create a new :class:`.MigrationContext`.
        
        This is a factory method usually called
        by :meth:`.EnvironmentContext.configure`.
        
        :param connection: a :class:`~sqlalchemy.engine.base.Connection` 
         to use for SQL execution in "online" mode.  When present, 
         is also used to determine the type of dialect in use.
        :param url: a string database url, or a 
         :class:`sqlalchemy.engine.url.URL` object.
         The type of dialect to be used will be derived from this if 
         ``connection`` is not passed.
        :param dialect_name: string name of a dialect, such as 
         "postgresql", "mssql", etc.  The type of dialect to be used will be 
         derived from this if ``connection`` and ``url`` are not passed.
        :param opts: dictionary of options.  Most other options
         accepted by :meth:`.EnvironmentContext.configure` are passed via 
         this dictionary.

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

        return MigrationContext(dialect, connection, opts)


    def _current_rev(self):
        if self.as_sql:
            return self._start_from_rev
        else:
            if self._start_from_rev:
                raise util.CommandError(
                    "Can't specify current_rev to context "
                    "when using a database connection")
            _version.create(self.connection, checkfirst=True)
        return self.connection.scalar(_version.select())

    def _update_current_rev(self, old, new):
        if old == new:
            return
        if new is None:
            self.impl._exec(_version.delete())
        elif old is None:
            self.impl._exec(_version.insert().
                        values(version_num=literal_column("'%s'" % new))
                    )
        else:
            self.impl._exec(_version.update().
                        values(version_num=literal_column("'%s'" % new))
                    )

    def run_migrations(self, **kw):

        current_rev = rev = False
        self.impl.start_migrations()
        for change, prev_rev, rev in self._migrations_fn(
                                        self._current_rev(),
                                        self):
            if current_rev is False:
                current_rev = prev_rev
                if self.as_sql and not current_rev:
                    _version.create(self.connection)
            log.info("Running %s %s -> %s", change.__name__, prev_rev, rev)
            if self.as_sql:
                self.impl.static_output(
                        "-- Running %s %s -> %s" %
                        (change.__name__, prev_rev, rev)
                    )
            change(**kw)
            if not self.impl.transactional_ddl:
                self._update_current_rev(prev_rev, rev)
            prev_rev = rev

        if rev is not False:
            if self.impl.transactional_ddl:
                self._update_current_rev(current_rev, rev)

            if self.as_sql and not rev:
                _version.drop(self.connection)

    def execute(self, sql):
        self.impl._exec(sql)

    def _stdout_connection(self, connection):
        def dump(construct, *multiparams, **params):
            self.impl._exec(construct)

        return create_engine("%s://" % self.dialect.name, 
                        strategy="mock", executor=dump)

    @property
    def bind(self):
        """Return the current "bind".

        In online mode, this is an instance of
        :class:`sqlalchemy.engine.base.Connection`, and is suitable
        for ad-hoc execution of any kind of usage described 
        in :ref:`sqlexpression_toplevel` as well as 
        for usage with the :meth:`sqlalchemy.schema.Table.create`
        and :meth:`sqlalchemy.schema.MetaData.create_all` methods
        of :class:`~sqlalchemy.schema.Table`, :class:`~sqlalchemy.schema.MetaData`.

        Note that when "standard output" mode is enabled, 
        this bind will be a "mock" connection handler that cannot
        return results and is only appropriate for a very limited
        subset of commands.

        """
        return self.connection

    def compare_type(self, inspector_column, metadata_column):
        if self._user_compare_type is False:
            return False

        if callable(self._user_compare_type):
            user_value = self._user_compare_type(
                self,
                inspector_column,
                metadata_column,
                inspector_column['type'],
                metadata_column.type
            )
            if user_value is not None:
                return user_value

        return self.impl.compare_type(
                                    inspector_column, 
                                    metadata_column)

    def compare_server_default(self, inspector_column, 
                            metadata_column, 
                            rendered_metadata_default):

        if self._user_compare_server_default is False:
            return False

        if callable(self._user_compare_server_default):
            user_value = self._user_compare_server_default(
                    self,
                    inspector_column,
                    metadata_column,
                    inspector_column['default'],
                    metadata_column.server_default,
                    rendered_metadata_default
            )
            if user_value is not None:
                return user_value

        return self.impl.compare_server_default(
                                inspector_column, 
                                metadata_column, 
                                rendered_metadata_default)

