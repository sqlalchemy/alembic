from alembic import util
from sqlalchemy import MetaData, Table, Column, String, literal_column, \
    text
from sqlalchemy import create_engine
from alembic import ddl
import sys
from contextlib import contextmanager

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

    The :class:`.Context` is available directly via the :func:`.get_context` function,
    though usually it is referenced behind the scenes by the various module level functions
    within the :mod:`alembic.context` module.

    """
    def __init__(self, dialect, script, connection, 
                        opts,
                        as_sql=False, 
                        output_buffer=None,
                        transactional_ddl=None,
                        starting_rev=None,
                        compare_type=False,
                        compare_server_default=False):
        self.dialect = dialect
        # TODO: need this ?
        self.script = script
        if as_sql:
            self.connection = self._stdout_connection(connection)
            assert self.connection is not None
        else:
            self.connection = connection
        self._migrations_fn = opts.get('fn')
        self.as_sql = as_sql
        self.output_buffer = output_buffer if output_buffer else sys.stdout

        self._user_compare_type = compare_type
        self._user_compare_server_default = compare_server_default

        self._start_from_rev = starting_rev
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
                                        self._current_rev()):
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
        of :class:`.Table`, :class:`.MetaData`.

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

