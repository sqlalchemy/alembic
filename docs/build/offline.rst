Generating SQL Scripts (a.k.a. "Offline Mode")
==============================================

A major capability of Alembic is to generate migrations as SQL scripts, instead of running
them against the database - this is also referred to as *offline mode*.
This is a critical feature when working in large organizations
where access to DDL is restricted, and SQL scripts must be handed off to DBAs.   Alembic makes
this easy via the ``--sql`` option passed to any ``upgrade`` or ``downgrade`` command.   We
can, for example, generate a script that revises up to rev ``ae1027a6acf``::

    $ alembic upgrade ae1027a6acf --sql
    INFO  [alembic.context] Context class PostgresqlContext.
    INFO  [alembic.context] Will assume transactional DDL.
    BEGIN;

    CREATE TABLE alembic_version (
        version_num VARCHAR(32) NOT NULL
    );

    INFO  [alembic.context] Running upgrade None -> 1975ea83b712
    CREATE TABLE account (
        id SERIAL NOT NULL,
        name VARCHAR(50) NOT NULL,
        description VARCHAR(200),
        PRIMARY KEY (id)
    );

    INFO  [alembic.context] Running upgrade 1975ea83b712 -> ae1027a6acf
    ALTER TABLE account ADD COLUMN last_transaction_date TIMESTAMP WITHOUT TIME ZONE;

    INSERT INTO alembic_version (version_num) VALUES ('ae1027a6acf');

    COMMIT;


While the logging configuration dumped to standard error, the actual script was dumped to standard output -
so in the absence of further configuration (described later in this section), we'd at first be using output
redirection to generate a script::

    $ alembic upgrade ae1027a6acf --sql > migration.sql

Getting the Start Version
--------------------------

Notice that our migration script started at the base - this is the default when using offline
mode, as no database connection is present and there's no ``alembic_version`` table to read from.

One way to provide a starting version in offline mode is to provide a range to the command line.
This is accomplished by providing the "version" in ``start:end`` syntax::

    $ alembic upgrade 1975ea83b712:ae1027a6acf --sql > migration.sql

The ``start:end`` syntax is only allowed in offline mode; in "online" mode, the ``alembic_version``
table is always used to get at the current version.

It's also possible to have the ``env.py`` script retrieve the "last" version from
the local environment, such as from a local file.   A scheme like this would basically
treat a local file in the same way ``alembic_version`` works::

    if context.is_offline_mode():
        version_file = os.path.join(os.path.dirname(config.config_file_name), "version.txt")
        if os.path.exists(version_file):
            current_version = open(version_file).read()
        else:
            current_version = None
        context.configure(dialect_name=engine.name, starting_rev=current_version)
        context.run_migrations()
        end_version = context.get_revision_argument()
        if end_version and end_version != current_version:
            open(version_file, 'w').write(end_version)

Writing Migration Scripts to Support Script Generation
------------------------------------------------------

The challenge of SQL script generation is that the scripts we generate can't rely upon
any client/server database access.  This means a migration script that pulls some rows
into memory via a ``SELECT`` statement will not work in ``--sql`` mode.   It's also
important that the Alembic directives, all of which are designed specifically to work
in both "live execution" as well as "offline SQL generation" mode, are used.

Customizing the Environment
---------------------------

Users of the ``--sql`` option are encouraged to hack their ``env.py`` files to suit their
needs.  The ``env.py`` script as provided is broken into two sections: ``run_migrations_online()``
and ``run_migrations_offline()``.  Which function is run is determined at the bottom of the
script by reading :meth:`.EnvironmentContext.is_offline_mode`, which basically determines if the
``--sql`` flag was enabled.

For example, a multiple database configuration may want to run through each
database and set the output of the migrations to different named files - the :meth:`.EnvironmentContext.configure`
function accepts a parameter ``output_buffer`` for this purpose.  Below we illustrate
this within the ``run_migrations_offline()`` function::

    from alembic import context
    import myapp
    import sys

    db_1 = myapp.db_1
    db_2 = myapp.db_2

    def run_migrations_offline():
        """Run migrations *without* a SQL connection."""

        for name, engine, file_ in [
            ("db1", db_1, "db1.sql"),
            ("db2", db_2, "db2.sql"),
        ]:
            context.configure(
                        url=engine.url,
                        transactional_ddl=False,
                        output_buffer=open(file_, 'w'))
            context.execute("-- running migrations for '%s'" % name)
            context.run_migrations(name=name)
            sys.stderr.write("Wrote file '%s'" % file_)

    def run_migrations_online():
        """Run migrations *with* a SQL connection."""

        for name, engine in [
            ("db1", db_1),
            ("db2", db_2),
        ]:
            connection = engine.connect()
            context.configure(connection=connection)
            try:
                context.run_migrations(name=name)
                session.commit()
            except:
                session.rollback()
                raise

    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()

