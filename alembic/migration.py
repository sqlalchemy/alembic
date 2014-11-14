import logging
import sys
from contextlib import contextmanager
from collections import namedtuple

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

    def __init__(self, dialect, connection, opts, environment_context=None):
        self.environment_context = environment_context
        self.opts = opts
        self.dialect = dialect
        self.script = opts.get('script')

        as_sql = opts.get('as_sql', False)
        transactional_ddl = opts.get("transactional_ddl")

        self._transaction_per_migration = opts.get(
            "transaction_per_migration", False)

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
        self.version_table = version_table = opts.get(
            'version_table', 'alembic_version')
        self.version_table_schema = version_table_schema = \
            opts.get('version_table_schema', None)
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
                  environment_context=None,
                  opts=None,
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
        if opts is None:
            opts = {}

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

        return MigrationContext(dialect, connection, opts, environment_context)

    def begin_transaction(self, _per_migration=False):
        transaction_now = _per_migration == self._transaction_per_migration

        if not transaction_now:
            @contextmanager
            def do_nothing():
                yield
            return do_nothing()

        elif not self.impl.transactional_ddl:
            @contextmanager
            def do_nothing():
                yield
            return do_nothing()
        elif self.as_sql:
            @contextmanager
            def begin_commit():
                self.impl.emit_begin()
                yield
                self.impl.emit_commit()
            return begin_commit()
        else:
            return self.bind.begin()

    def get_current_revision(self):
        """Return the current revision, usually that which is present
        in the ``alembic_version`` table in the database.

        This method intends to be used only for a migration stream that
        does not contain unmerged branches in the target database;
        if there are multiple branches present, an exception is raised.
        The :meth:`.MigrationContext.get_current_heads` should be preferred
        over this method going forward in order to be compatible with
        branch migration support.

        If this :class:`.MigrationContext` was configured in "offline"
        mode, that is with ``as_sql=True``, the ``starting_rev``
        parameter is returned instead, if any.

        """
        heads = self.get_current_heads()
        if len(heads) == 0:
            return None
        elif len(heads) > 1:
            raise util.CommandError(
                "Version table '%s' has more than one head present; "
                "please use get_current_heads()" % self.version_table)
        else:
            return heads[0]

    def get_current_heads(self):
        """Return a tuple of the current 'head versions' that are represented
        in the target database.

        For a migration stream without branches, this will be a single
        value, synonymous with that of
        :meth:`.MigrationContext.get_current_revision`.   However when multiple
        unmerged branches exist within the target database, the returned tuple
        will contain a value for each head.

        If this :class:`.MigrationContext` was configured in "offline"
        mode, that is with ``as_sql=True``, the ``starting_rev``
        parameter is returned in a one-length tuple.

        If no version table is present, or if there are no revisions
        present, an empty tuple is returned.

        .. versionadded:: 0.7.0

        """
        if self.as_sql:
            return (self._start_from_rev, )
        else:
            if self._start_from_rev:
                raise util.CommandError(
                    "Can't specify current_rev to context "
                    "when using a database connection")
            if not self._has_version_table():
                return ()
        return tuple(
            row[0] for row in self.connection.execute(self._version.select())
        )

    def _ensure_version_table(self):
        self._version.create(self.connection, checkfirst=True)

    def _has_version_table(self):
        return self.connection.dialect.has_table(
            self.connection, self.version_table, self.version_table_schema)

    def _update_current_rev(self, old, new):
        if old == new:
            return
        if new is None or new == ():
            ret = self.impl._exec(
                self._version.delete().where(
                    self._version.c.version_num == old))
            if not self.as_sql and ret.rowcount != 1:
                raise util.CommandError(
                    "Online migration expected to match one "
                    "row when deleting '%s' in '%s'; "
                    "%d found"
                    % (old, self.version_table, ret.rowcount))
        elif old is None or old == ():
            self.impl._exec(
                self._version.insert().
                values(version_num=literal_column("'%s'" % new))
            )
        elif old is False:
            # this is the "offline stamp" use case
            assert self.as_sql
            self.impl._exec(
                self._version.update().
                values(version_num=literal_column("'%s'" % new))
            )
        else:
            ret = self.impl._exec(
                self._version.update().
                values(version_num=literal_column("'%s'" % new)).where(
                    self._version.c.version_num == old)
            )
            if not self.as_sql and ret.rowcount != 1:
                raise util.CommandError(
                    "Online migration expected to match one "
                    "row when updating '%s' to '%s' in '%s'; "
                    "%d found"
                    % (old, new, self.version_table, ret.rowcount))

    def run_migrations(self, **kw):
        """Run the migration scripts established for this
        :class:`.MigrationContext`, if any.

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
        stamp_per_migration = not self.impl.transactional_ddl or \
            self._transaction_per_migration

        self.impl.start_migrations()

        heads = self.get_current_heads()
        if not self.as_sql and not heads:
            self._ensure_version_table()

        for change, prev_rev, rev, doc in self._migrations_fn(
                self.get_current_revision(),
                self):
            with self.begin_transaction(_per_migration=True):
                if current_rev is False:
                    current_rev = prev_rev
                    # for offline mode, include a CREATE TABLE from
                    # the base
                    if self.as_sql and not current_rev:
                        self._version.create(self.connection)
                if doc:
                    log.info(
                        "Running %s %s -> %s, %s", change.__name__, prev_rev,
                        rev, doc)
                else:
                    log.info(
                        "Running %s %s -> %s", change.__name__, prev_rev, rev)
                if self.as_sql:
                    self.impl.static_output(
                        "-- Running %s %s -> %s" %
                        (change.__name__, prev_rev, rev)
                    )
                change(**kw)
                if stamp_per_migration:
                    self._update_current_rev(prev_rev, rev)
                prev_rev = rev

        if rev is not False:
            if not stamp_per_migration:
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
        of :class:`~sqlalchemy.schema.Table`,
        :class:`~sqlalchemy.schema.MetaData`.

        Note that when "standard output" mode is enabled,
        this bind will be a "mock" connection handler that cannot
        return results and is only appropriate for a very limited
        subset of commands.

        """
        return self.connection

    @property
    def config(self):
        """Return the :class:`.Config` used by the current environment, if any.

        .. versionadded:: 0.6.6

        """
        if self.environment_context:
            return self.environment_context.config
        else:
            return None

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

MigrationStep = namedtuple(
    "MigrationStep",
    ["migrate_fn", "from_revisions", "to_revisions",
     "doc", "is_upgrade", "branch_presence_changed"]
)


class MigrationStep(MigrationStep):
    @property
    def should_create_branch(self):
        return self.is_upgrade and self.branch_presence_changed

    @property
    def should_delete_branch(self):
        return self.is_downgrade and self.branch_presence_changed

    @property
    def should_merge_branches(self):
        return self.is_upgrade and len(self.from_revisions) > 1

    @property
    def should_unmerge_branches(self):
        return self.is_downgrade and len(self.from_revisions) > 1

    @property
    def is_downgrade(self):
        return not self.is_upgrade

    @classmethod
    def upgrade_from_script(cls, script, down_revision_seen=False):
        return MigrationStep(
            script.module.upgrade, script.down_revision, script.revision,
            script.doc, True, down_revision_seen
        )

    @classmethod
    def downgrade_from_script(cls, script, down_revision_seen=False):
        return MigrationStep(
            script.module.downgrade, script.revision, script.down_revision,
            script.doc, False, down_revision_seen
        )
