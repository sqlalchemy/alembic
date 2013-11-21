import io
import logging
import sys

from sqlalchemy import MetaData, Table, Column, String, literal_column
from sqlalchemy import create_engine
from sqlalchemy.engine import url as sqla_url

from .compat import callable, EncodedIO
from . import ddl, util

log = logging.getLogger(__name__)

class MigrationContext(object):
    """Represent the database state made available to a migration
    script.

    :class:`.MigrationContext` is the front end to an actual
    database connection, or alternatively a string output
    stream given a particular database dialect,
    from an Alembic perspective.

    When inside the ``env.py`` script, the :class:`.MigrationContext`
    is available via the
    :meth:`.EnvironmentContext.get_context` method,
    which is available at ``alembic.context``::

        # from within env.py script
        from alembic import context
        migration_context = context.get_context()

    For usage outside of an ``env.py`` script, such as for
    utility routines that want to check the current version
    in the database, the :meth:`.MigrationContext.configure`
    method to create new :class:`.MigrationContext` objects.
    For example, to get at the current revision in the
    database using :meth:`.MigrationContext.get_current_revision`::

        # in any application, outside of an env.py script
        from alembic.migration import MigrationContext
        from sqlalchemy import create_engine

        engine = create_engine("postgresql://mydatabase")
        conn = engine.connect()

        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()

    The above context can also be used to produce
    Alembic migration operations with an :class:`.Operations`
    instance::

        # in any application, outside of the normal Alembic environment
        from alembic.operations import Operations
        op = Operations(context)
        op.alter_column("mytable", "somecolumn", nullable=True)

    """
    def __init__(self, dialect, connection, opts):
        self.opts = opts
        self.dialect = dialect
        self.script = opts.get('script')

        as_sql = opts.get('as_sql', False)
        transactional_ddl = opts.get("transactional_ddl")

        if as_sql:
            self.connection = self._stdout_connection(connection)
            assert self.connection is not None
        else:
            self.connection = connection
        self._migrations_fn = opts.get('fn')
        self.as_sql = as_sql

        if "output_encoding" in opts:
            self.output_buffer = EncodedIO(
                opts.get("output_buffer") or sys.stdout,
                opts['output_encoding']
            )
        else:
            self.output_buffer = opts.get("output_buffer", sys.stdout)

        self._user_compare_type = opts.get('compare_type', False)
        self._user_compare_server_default = opts.get(
                                            'compare_server_default',
                                            False)
        version_table = opts.get('version_table', 'alembic_version')
        version_table_schema = opts.get('version_table_schema', None)
        self._version = Table(
            version_table, MetaData(),
            Column('version_num', String(32), nullable=False),
            schema=version_table_schema)

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

        :param connection: a :class:`~sqlalchemy.engine.Connection`
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


    def get_current_revision(self):
        """Return the current revision, usually that which is present
        in the ``alembic_version`` table in the database.

        If this :class:`.MigrationContext` was configured in "offline"
        mode, that is with ``as_sql=True``, the ``starting_rev``
        parameter is returned instead, if any.

        """
        if self.as_sql:
            return self._start_from_rev
        else:
            if self._start_from_rev:
                raise util.CommandError(
                    "Can't specify current_rev to context "
                    "when using a database connection")
            self._version.create(self.connection, checkfirst=True)
        return self.connection.scalar(self._version.select())

    _current_rev = get_current_revision
    """The 0.2 method name, for backwards compat."""

    def _update_current_rev(self, old, new):
        if old == new:
            return
        if new is None:
            self.impl._exec(self._version.delete())
        elif old is None:
            self.impl._exec(self._version.insert().
                        values(version_num=literal_column("'%s'" % new))
                    )
        else:
            self.impl._exec(self._version.update().
                        values(version_num=literal_column("'%s'" % new))
                    )

    def run_migrations(self, **kw):
        """Run the migration scripts established for this :class:`.MigrationContext`,
        if any.

        The commands in :mod:`alembic.command` will set up a function
        that is ultimately passed to the :class:`.MigrationContext`
        as the ``fn`` argument.  This function represents the "work"
        that will be done when :meth:`.MigrationContext.run_migrations`
        is called, typically from within the ``env.py`` script of the
        migration environment.  The "work function" then provides an iterable
        of version callables and other version information which
        in the case of the ``upgrade`` or ``downgrade`` commands are the
        list of version scripts to invoke.  Other commands yield nothing,
        in the case that a command wants to run some other operation
        against the database such as the ``current`` or ``stamp`` commands.

        :param \**kw: keyword arguments here will be passed to each
         migration callable, that is the ``upgrade()`` or ``downgrade()``
         method within revision scripts.

        """
        current_rev = rev = False
        self.impl.start_migrations()
        for change, prev_rev, rev, doc in self._migrations_fn(
                                            self.get_current_revision(),
                                            self):
            if current_rev is False:
                current_rev = prev_rev
                if self.as_sql and not current_rev:
                    self._version.create(self.connection)
            if doc:
                log.info("Running %s %s -> %s, %s", change.__name__, prev_rev,
                    rev, doc)
            else:
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
                self._version.drop(self.connection)

    def execute(self, sql, execution_options=None):
        """Execute a SQL construct or string statement.

        The underlying execution mechanics are used, that is
        if this is "offline mode" the SQL is written to the
        output buffer, otherwise the SQL is emitted on
        the current SQLAlchemy connection.

        """
        self.impl._exec(sql, execution_options)

    def _stdout_connection(self, connection):
        def dump(construct, *multiparams, **params):
            self.impl._exec(construct)

        return create_engine("%s://" % self.dialect.name,
                        strategy="mock", executor=dump)

    @property
    def bind(self):
        """Return the current "bind".

        In online mode, this is an instance of
        :class:`sqlalchemy.engine.Connection`, and is suitable
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

    def _compare_type(self, inspector_column, metadata_column):
        if self._user_compare_type is False:
            return False

        if callable(self._user_compare_type):
            user_value = self._user_compare_type(
                self,
                inspector_column,
                metadata_column,
                inspector_column.type,
                metadata_column.type
            )
            if user_value is not None:
                return user_value

        return self.impl.compare_type(
                                    inspector_column,
                                    metadata_column)

    def _compare_server_default(self, inspector_column,
                            metadata_column,
                            rendered_metadata_default,
                            rendered_column_default):

        if self._user_compare_server_default is False:
            return False

        if callable(self._user_compare_server_default):
            user_value = self._user_compare_server_default(
                    self,
                    inspector_column,
                    metadata_column,
                    rendered_column_default,
                    metadata_column.server_default,
                    rendered_metadata_default
            )
            if user_value is not None:
                return user_value

        return self.impl.compare_server_default(
                                inspector_column,
                                metadata_column,
                                rendered_metadata_default,
                                rendered_column_default)

