========
Tutorial
========

`Alembic <http://bitbucket.org/zzzeek/alembic>`_ provides for the creation, management, and invocation of *change management*
scripts for a relational database, using `SQLAlchemy <http://www.sqlalchemy.org>`_ as the underlying engine.
This tutorial will provide a full introduction to the theory and usage of this tool.

To begin, make sure Alembic is installed as described at :ref:`installation`.

The Migration Environment
==========================

Usage of Alembic starts with creation of the *Migration Environment*.  This is a directory of scripts
that is specific to a particular application.   The migration environment is created just once,
and is then maintained along with the application's source code itself.   The environment is
created using the ``init`` command of Alembic, and is then customizable to suit the specific
needs of the application.

The structure of this environment, including some generated migration scripts, looks like::

    yourproject/
        alembic/
            env.py
            README
            script.py.mako
            versions/
                3512b954651e_add_account.py
                2b1ae634e5cd_add_order_id.py
                3adcc9a56557_rename_username_field.py

The directory includes these directories/files:

* ``yourproject`` - this is the root of your application's source code, or some directory within it.
* ``alembic`` - this directory lives within your application's source tree and is the home of the
  migration environment.   It can be named anything, and a project that uses multiple databases
  may even have more than one.
* ``env.py`` - This is a Python script that is run whenever the alembic migration tool is invoked.
  At the very least, it contains instructions to configure and generate a SQLAlchemy engine,
  procure a connection from that engine along with a transaction, and to then invoke the migration
  engine, using the connection as a source of database connectivity.

  The ``env.py`` script is part of the generated environment so that the way migrations run
  is entirely customizable.   The exact specifics of how to connect are here, as well as
  the specifics of how the migration enviroment are invoked.  The script can be modified
  so that multiple engines can be operated upon, custom arguments can be passed into the
  migration environment, application-specific libraries and models can be loaded in and
  made available.

  Alembic includes a set of initialization templates which feature different varieties
  of ``env.py`` for different use cases.
* ``README`` - included with the various enviromnent templates, should have something
  informative.
* ``script.py.mako`` - This is a `Mako <http://www.makotemplates.org>`_ template file which
  is used to generate new migration scripts.   Whatever is here is used to generate new
  files within ``versions/``.   This is scriptable so that the structure of each migration
  file can be controlled, including standard imports to be within each, as well as
  changes to the structure of the ``upgrade()`` and ``downgrade()`` functions.  For example,
  the ``multidb`` environment allows for multiple functions to be generated using a
  naming scheme ``upgrade_engine1()``, ``upgrade_engine2()``.
* ``versions/`` - This directory holds the individual version scripts.  Users of other migration
  tools may notice that the files here don't use ascending integers, and instead use a
  partial GUID approach.   In Alembic, the ordering of version scripts is relative
  to directives within the scripts themselves, and it is theoretically possible to "splice" version files
  in between others, allowing migration sequences from different branches to be merged,
  albeit carefully by hand.


Creating an Environment
=======================

With a basic understanding of what the environment is, we can create one using ``alembic init``.
This will create an environment using the "generic" template::

    $ cd yourproject
    $ alembic init alembic

Where above, the ``init`` command was called to generate a migrations directory called ``alembic``::

    Creating directory /path/to/yourproject/alembic...done
    Creating directory /path/to/yourproject/alembic/versions...done
    Generating /path/to/yourproject/alembic.ini...done
    Generating /path/to/yourproject/alembic/env.py...done
    Generating /path/to/yourproject/alembic/README...done
    Generating /path/to/yourproject/alembic/script.py.mako...done
    Please edit configuration/connection/logging settings in
    '/path/to/yourproject/alembic.ini' before proceeding.

Alembic also includes other environment templates.  These can be listed out using the ``list_templates``
command::

    $ alembic list_templates
    Available templates:

    generic - Generic single-database configuration.
    multidb - Rudimentary multi-database configuration.
    pylons - Configuration that reads from a Pylons project environment.

    Templates are used via the 'init' command, e.g.:

      alembic init --template pylons ./scripts

Editing the .ini File
=====================

Alembic placed a file ``alembic.ini`` into the current directory.  This is a file that the ``alembic``
script looks for when invoked.  This file can be anywhere, either in the same directory
from which the ``alembic`` script will normally be invoked, or if in a different directory, can
be specified by using the ``--config`` option to the ``alembic`` runner.

The file generated with the "generic" configuration looks like::

    # A generic, single database configuration.

    [alembic]
    # path to migration scripts
    script_location = alembic

    # template used to generate migration files
    # file_template = %%(rev)s_%%(slug)s

    # set to 'true' to run the environment during
    # the 'revision' command, regardless of autogenerate
    # revision_environment = false

    sqlalchemy.url = driver://user:pass@localhost/dbname

    # Logging configuration
    [loggers]
    keys = root,sqlalchemy,alembic

    [handlers]
    keys = console

    [formatters]
    keys = generic

    [logger_root]
    level = WARN
    handlers = console
    qualname =

    [logger_sqlalchemy]
    level = WARN
    handlers =
    qualname = sqlalchemy.engine

    [logger_alembic]
    level = INFO
    handlers =
    qualname = alembic

    [handler_console]
    class = StreamHandler
    args = (sys.stderr,)
    level = NOTSET
    formatter = generic

    [formatter_generic]
    format = %(levelname)-5.5s [%(name)s] %(message)s
    datefmt = %H:%M:%S

The file is read using Python's :class:`ConfigParser.SafeConfigParser` object.  The
``%(here)s`` variable is provided as a substitution variable, which
can be used to produce absolute pathnames to directories and files, as we do above
with the path to the Alembic script location.

This file contains the following features:

* ``[alembic]`` - this is the section read by Alembic to determine configuration.  Alembic
  itself does not directly read any other areas of the file.
* ``script_location`` - this is the location of the Alembic environment.   It is normally
  specified as a filesystem location, either relative or absolute.  If the location is
  a relative path, it's interpreted as relative to the current directory.

  This is the only key required by Alembic in all cases.   The generation
  of the .ini file by the command ``alembic init alembic`` automatically placed the
  directory name ``alembic`` here.   The special variable ``%(here)s`` can also be used,
  as in ``%(here)s/alembic``.

  For support of applications that package themselves into .egg files, the value can
  also be specified
  as a `package resource <http://packages.python.org/distribute/pkg_resources.html>`_, in which
  case ``resource_filename()`` is used to find the file (new in 0.2.2).  Any non-absolute
  URI which contains colons is interpreted here as a resource name, rather than
  a straight filename.

* ``file_template`` - this is the naming scheme used to generate new migration files.
  The value present is the default, so is commented out.   Tokens available include:

    * ``%%(rev)s`` - revision id
    * ``%%(slug)s`` - a truncated string derived from the revision message
    * ``%%(year)d``, ``%%(month).2d``, ``%%(day).2d``, ``%%(hour).2d``,
      ``%%(minute).2d``, ``%%(second).2d`` - components of the create date
      as returned by ``datetime.datetime.now()``

    .. versionadded:: 0.3.6 - added date parameters to ``file_template``.

* ``sqlalchemy.url`` - A URL to connect to the database via SQLAlchemy.  This key is in fact
  only referenced within the ``env.py`` file that is specific to the "generic" configuration;
  a file that can be customized by the developer. A multiple
  database configuration may respond to multiple keys here, or may reference other sections
  of the file.
* ``revision_environment`` - this is a flag which when set to the value 'true', will indicate
  that the migration environment script ``env.py`` should be run unconditionally when
  generating new revision files (new in 0.3.3).
* ``[loggers]``, ``[handlers]``, ``[formatters]``, ``[logger_*]``, ``[handler_*]``,
  ``[formatter_*]`` - these sections are all part of Python's standard logging configuration,
  the mechanics of which are documented at `Configuration File Format <http://docs.python.org/library/logging.config.html#configuration-file-format>`_.
  As is the case with the database connection, these directives are used directly as the
  result of the ``logging.config.fileConfig()`` call present in the
  ``env.py`` script, which you're free to modify.

For starting up with just a single database and the generic configuration, setting up
the SQLAlchemy URL is all that's needed::

    sqlalchemy.url = postgresql://scott:tiger@localhost/test

Create a Migration Script
=========================

With the environment in place we can create a new revision, using ``alembic revision``::

    $ alembic revision -m "create account table"
    Generating /path/to/yourproject/alembic/versions/1975ea83b712_create_accoun
    t_table.py...done

A new file ``1975ea83b712_create_account_table.py`` is generated.  Looking inside the file::

    """create account table

    Revision ID: 1975ea83b712
    Revises: None
    Create Date: 2011-11-08 11:40:27.089406

    """

    # revision identifiers, used by Alembic.
    revision = '1975ea83b712'
    down_revision = None

    from alembic import op
    import sqlalchemy as sa

    def upgrade():
        pass

    def downgrade():
        pass

The file contains some header information, identifiers for the current revision
and a "downgrade" revision, an import of basic Alembic directives,
and empty ``upgrade()`` and ``downgrade()`` functions.  Our
job here is to populate the ``upgrade()`` and ``downgrade()`` functions with directives that
will apply a set of changes to our database.    Typically, ``upgrade()`` is required
while ``downgrade()`` is only needed if down-revision capability is desired, though it's
probably a good idea.

Another thing to notice is the ``down_revision`` variable.  This is how Alembic
knows the correct order in which to apply migrations.   When we create the next revision,
the new file's ``down_revision`` identifier would point to this one::

    # revision identifiers, used by Alembic.
    revision = 'ae1027a6acf'
    down_revision = '1975ea83b712'

Every time Alembic runs an operation against the ``versions/`` directory, it reads all
the files in, and composes a list based on how the ``down_revision`` identifiers link together,
with the ``down_revision`` of ``None`` representing the first file.   In theory, if a
migration environment had thousands of migrations, this could begin to add some latency to
startup, but in practice a project should probably prune old migrations anyway
(see the section :ref:`building_uptodate` for a description on how to do this, while maintaining
the ability to build the current database fully).

We can then add some directives to our script, suppose adding a new table ``account``::

    def upgrade():
        op.create_table(
            'account',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('name', sa.String(50), nullable=False),
            sa.Column('description', sa.Unicode(200)),
        )

    def downgrade():
        op.drop_table('account')

:meth:`~.Operations.create_table` and :meth:`~.Operations.drop_table` are Alembic directives.   Alembic provides
all the basic database migration operations via these directives, which are designed to be as simple and
minimalistic as possible;
there's no reliance upon existing table metadata for most of these directives.  They draw upon
a global "context" that indicates how to get at a database connection (if any; migrations can
dump SQL/DDL directives to files as well) in order to invoke the command.   This global
context is set up, like everything else, in the ``env.py`` script.

An overview of all Alembic directives is at :ref:`ops`.

Running our First Migration
===========================

We now want to run our migration.   Assuming our database is totally clean, it's as
yet unversioned.   The ``alembic upgrade`` command will run upgrade operations, proceeding
from the current database revision, in this example ``None``, to the given target revision.
We can specify ``1975ea83b712`` as the revision we'd like to upgrade to, but it's easier
in most cases just to tell it "the most recent", in this case ``head``::

    $ alembic upgrade head
    INFO  [alembic.context] Context class PostgresqlContext.
    INFO  [alembic.context] Will assume transactional DDL.
    INFO  [alembic.context] Running upgrade None -> 1975ea83b712

Wow that rocked !   Note that the information we see on the screen is the result of the
logging configuration set up in ``alembic.ini`` - logging the ``alembic`` stream to the
console (standard error, specifically).

The process which occurred here included that Alembic first checked if the database had
a table called ``alembic_version``, and if not, created it.   It looks in this table
for the current version, if any, and then calculates the path from this version to
the version requested, in this case ``head``, which is known to be ``1975ea83b712``.
It then invokes the ``upgrade()`` method in each file to get to the target revision.

Running our Second Migration
=============================

Let's do another one so we have some things to play with.    We again create a revision
file::

    $ alembic revision -m "Add a column"
    Generating /path/to/yourapp/alembic/versions/ae1027a6acf.py_add_a_column.py...
    done

Let's edit this file and add a new column to the ``account`` table::

    """Add a column

    Revision ID: ae1027a6acf
    Revises: 1975ea83b712
    Create Date: 2011-11-08 12:37:36.714947

    """

    # revision identifiers, used by Alembic.
    revision = 'ae1027a6acf'
    down_revision = '1975ea83b712'

    from alembic import op
    import sqlalchemy as sa

    def upgrade():
        op.add_column('account', sa.Column('last_transaction_date', sa.DateTime))

    def downgrade():
        op.drop_column('account', 'last_transaction_date')

Running again to ``head``::

    $ alembic upgrade head
    INFO  [alembic.context] Context class PostgresqlContext.
    INFO  [alembic.context] Will assume transactional DDL.
    INFO  [alembic.context] Running upgrade 1975ea83b712 -> ae1027a6acf

We've now added the ``last_transaction_date`` column to the database.

Relative Migration Identifiers
==============================

As of 0.3.3, relative upgrades/downgrades are also supported.  To move two versions from the current, a decimal value "+N" can be supplied::

    $ alembic upgrade +2

Negative values are accepted for downgrades::

    $ alembic downgrade -1

Getting Information
===================

With a few revisions present we can get some information about the state of things.

First we can view the current revision::

    $ alembic current
    INFO  [alembic.context] Context class PostgresqlContext.
    INFO  [alembic.context] Will assume transactional DDL.
    Current revision for postgresql://scott:XXXXX@localhost/test: 1975ea83b712 -> ae1027a6acf (head), Add a column

``head`` is displayed only if the revision identifier for this database matches the head revision.

We can also view history::

    $ alembic history

    1975ea83b712 -> ae1027a6acf (head), Add a column
    None -> 1975ea83b712, empty message

We can also identify specific migrations using just enough characters to uniquely identify them.
If we wanted to upgrade directly to ``ae1027a6acf`` we could say::

    $ alembic upgrade ae1

Alembic will stop and let you know if more than one version starts with that prefix.


Downgrading
===========

We can illustrate a downgrade back to nothing, by calling ``alembic downgrade`` back
to the beginning, which in Alembic is called ``base``::

    $ alembic downgrade base
    INFO  [alembic.context] Context class PostgresqlContext.
    INFO  [alembic.context] Will assume transactional DDL.
    INFO  [alembic.context] Running downgrade ae1027a6acf -> 1975ea83b712
    INFO  [alembic.context] Running downgrade 1975ea83b712 -> None

Back to nothing - and up again::

    $ alembic upgrade head
    INFO  [alembic.context] Context class PostgresqlContext.
    INFO  [alembic.context] Will assume transactional DDL.
    INFO  [alembic.context] Running upgrade None -> 1975ea83b712
    INFO  [alembic.context] Running upgrade 1975ea83b712 -> ae1027a6acf


Auto Generating Migrations
===========================

Alembic can view the status of the database and compare against the table metadata
in the application, generating the "obvious" migrations based on a comparison.  This
is achieved using the ``--autogenerate`` option to the ``alembic revision`` command,
which places so-called *candidate* migrations into our new migrations file.  We
review and modify these by hand as needed, then proceed normally.

To use autogenerate, we first need to modify our ``env.py`` so that it gets access
to a table metadata object that contains the target.  Suppose our application
has a `declarative base <http://www.sqlalchemy.org/docs/orm/extensions/declarative.html#synopsis>`_
in ``myapp.mymodel``.  This base contains a :class:`~sqlalchemy.schema.MetaData` object which
contains :class:`~sqlalchemy.schema.Table` objects defining our database.  We make sure this
is loaded in ``env.py`` and then passed to :meth:`.EnvironmentContext.configure` via the
``target_metadata`` argument.   The ``env.py`` sample script already has a
variable declaration near the top for our convenience, where we replace ``None``
with our :class:`~sqlalchemy.schema.MetaData`.  Starting with::

    # add your model's MetaData object here
    # for 'autogenerate' support
    # from myapp import mymodel
    # target_metadata = mymodel.Base.metadata
    target_metadata = None

we change to::

    from myapp.mymodel import Base
    target_metadata = Base.metadata

If we look later in the script, down in ``run_migrations_online()``,
we can see the directive passed to :meth:`.EnvironmentContext.configure`::

    def run_migrations_online():
        engine = engine_from_config(
                    config.get_section(config.config_ini_section), prefix='sqlalchemy.')

        connection = engine.connect()
        context.configure(
                    connection=connection,
                    target_metadata=target_metadata
                    )

        trans = connection.begin()
        try:
            context.run_migrations()
            trans.commit()
        except:
            trans.rollback()
            raise

We can then use the ``alembic revision`` command in conjunction with the
``--autogenerate`` option.  Suppose
our :class:`~sqlalchemy.schema.MetaData` contained a definition for the ``account`` table,
and the database did not.  We'd get output like::

    $ alembic revision --autogenerate -m "Added account table"
    INFO [alembic.context] Detected added table 'account'
    Generating /Users/classic/Desktop/tmp/alembic/versions/27c6a30d7c24.py...done

We can then view our file ``27c6a30d7c24.py`` and see that a rudimentary migration
is already present::

    """empty message

    Revision ID: 27c6a30d7c24
    Revises: None
    Create Date: 2011-11-08 11:40:27.089406

    """

    # revision identifiers, used by Alembic.
    revision = '27c6a30d7c24'
    down_revision = None

    from alembic import op
    import sqlalchemy as sa

    def upgrade():
        ### commands auto generated by Alembic - please adjust! ###
        op.create_table(
        'account',
        sa.Column('id', sa.Integer()),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.VARCHAR(200)),
        sa.Column('last_transaction_date', sa.DateTime()),
        sa.PrimaryKeyConstraint('id')
        )
        ### end Alembic commands ###

    def downgrade():
        ### commands auto generated by Alembic - please adjust! ###
        op.drop_table("account")
        ### end Alembic commands ###

The migration hasn't actually run yet, of course.  We do that via the usual ``upgrade``
command.   We should also go into our migration file and alter it as needed, including
adjustments to the directives as well as the addition of other directives which these may
be dependent on - specifically data changes in between creates/alters/drops.

Autogenerate will by default detect:

* Table additions, removals.
* Column additions, removals.
* Change of nullable status on columns.

Autogenerate can *optionally* detect:

* Change of column type.  This will occur if you set ``compare_type=True``
  on :meth:`.EnvironmentContext.configure`.  The feature works well in most cases,
  but is off by default so that it can be tested on the target schema
  first.  It can also be customized by passing a callable here; see the
  function's documentation for details.
* Change of server default.  This will occur if you set
  ``compare_server_default=True`` on :meth:`.EnvironmentContext.configure`.
  This feature works well for simple cases but cannot always produce
  accurate results.  The Postgresql backend will actually invoke
  the "detected" and "metadata" values against the database to
  determine equivalence.  The feature is off by default so that
  it can be tested on the target schema first.  Like type comparison,
  it can also be customized by passing a callable; see the
  function's documentation for details.

Autogenerate can *not* detect:

* Changes of table name.   These will come out as an add/drop of two different
  tables, and should be hand-edited into a name change instead.
* Changes of column name.  Like table name changes, these are detected as
  a column add/drop pair, which is not at all the same as a name change.
* Special SQLAlchemy types such as :class:`~sqlalchemy.types.Enum` when generated
  on a backend which doesn't support ENUM directly - this because the
  representation of such a type
  in the non-supporting database, i.e. a CHAR+ CHECK constraint, could be
  any kind of CHAR+CHECK.  For SQLAlchemy to determine that this is actually
  an ENUM would only be a guess, something that's generally a bad idea.
  To implement your own "guessing" function here, use the
  :meth:`sqlalchemy.events.DDLEvents.column_reflect` event
  to alter the SQLAlchemy type passed for certain columns and possibly
  :meth:`sqlalchemy.events.DDLEvents.after_parent_attach` to intercept
  unwanted CHECK constraints.

Autogenerate can't currently, but will *eventually* detect:

* Free-standing constraint additions, removals,
  like CHECK, UNIQUE, FOREIGN KEY - these aren't yet implemented.
  Right now you'll get constraints within new tables, PK and FK
  constraints for the "downgrade" to a previously existing table,
  and the CHECK constraints generated with a SQLAlchemy "schema" types
  :class:`~sqlalchemy.types.Boolean`, :class:`~sqlalchemy.types.Enum`.
* Index additions, removals - not yet implemented.
* Sequence additions, removals - not yet implemented.

Rendering Custom Types in Autogenerate
--------------------------------------

Note that the methodology Alembic uses to generate SQLAlchemy type constructs
as Python code is plain old ``__repr__()``.   SQLAlchemy's built-in types
for the most part have a ``__repr__()`` that faithfully renders a
Python-compatible constructor call, but there are some exceptions, particularly
in those cases when a constructor accepts arguments that aren't compatible
with ``__repr__()``, such as a pickling function.

When building a custom type that will be rendered into a migration script,
it is often necessary to explicitly give the type a ``__repr__()`` that will
faithfully reproduce the constructor for that type::

  from sqlalchemy.types import UserDefinedType

  class MySpecialType(UserDefinedType):
      def __init__(self, precision = 8):
          self.precision = precision

      def get_col_spec(self):
          return "MYTYPE(%s)" % self.precision

      def __repr__(self):
          return "MySpecialType(%d)" % self.precision

The above custom type includes a ``__repr__()`` that will render ``MySpecialType``
with the appropriate construction.   Sometimes ``__repr__()`` is needed
with semi-custom types such as those which derive from
:class:`~sqlalchemy.types.TypeDecorator` as well.


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
        context.configure(dialect_name=engine.name, starting_version=current_version)
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

Working with Branches
=====================

A *branch* describes when a source tree is broken up into two versions representing
two independent sets of changes.   The challenge of a branch is to *merge* the
branches into a single series of changes.  Alembic's GUID-based version number scheme
allows branches to be reconciled.

Consider if we merged into our source repository another branch which contained
a revision for another table called ``shopping_cart``.   This revision was made
against our first Alembic revision, the one that generated ``account``.   After
loading the second source tree in, a new file ``27c6a30d7c24.py`` exists within
our ``versions`` directory.   Both it, as well as ``ae1027a6acf.py``, reference
``1975ea83b712`` as the "downgrade" revision.  To illustrate::

    # main source tree:
    1975ea83b712 (add account table) -> ae1027a6acf (add a column)

    # branched source tree
    1975ea83b712 (add account table) -> 27c6a30d7c24 (add shopping cart table)

So above we can see 1975ea83b712 is our *branch point*.  The Alembic command ``branches``
illustrates this fact::

    $ alembic branches
    None -> 1975ea83b712 (branchpoint), add account table
         -> 1975ea83b712 -> 27c6a30d7c24 (head), add shopping cart table
         -> 1975ea83b712 -> ae1027a6acf (head), add a column

History shows it too, illustrating two ``head`` entries as well
as a ``branchpoint``::

    $ alembic history

    1975ea83b712 -> 27c6a30d7c24 (head), add shopping cart table

    1975ea83b712 -> ae1027a6acf (head), add a column
    None -> 1975ea83b712 (branchpoint), add account table

Alembic will also refuse to run any migrations until this is resolved::

    $ alembic upgrade head
    INFO  [alembic.context] Context class PostgresqlContext.
    INFO  [alembic.context] Will assume transactional DDL.
    Exception: Only a single head supported so far...

We resolve this branch by editing the files to be in a straight line.   In this case we edit
``27c6a30d7c24.py`` to point to ``ae1027a6acf.py``::

    """add shopping cart table

    Revision ID: 27c6a30d7c24
    Revises: ae1027a6acf  # changed from 1975ea83b712
    Create Date: 2011-11-08 13:02:14.212810

    """

    # revision identifiers, used by Alembic.
    revision = '27c6a30d7c24'
    # changed from 1975ea83b712
    down_revision = 'ae1027a6acf'


The ``branches`` command then shows no branches::

    $ alembic branches
    $

And the history is similarly linear::

    $ alembic history

    ae1027a6acf -> 27c6a30d7c24 (head), add shopping cart table
    1975ea83b712 -> ae1027a6acf, add a column
    None -> 1975ea83b712, add account table

.. note:: A future command called ``splice`` will automate this process.


.. _building_uptodate:

Building an Up to Date Database from Scratch
=============================================

There's a theory of database migrations that says that the revisions in existence for a database should be
able to go from an entirely blank schema to the finished product, and back again.   Alembic can roll
this way.   Though we think it's kind of overkill, considering that SQLAlchemy itself can emit
the full CREATE statements for any given model using :meth:`~sqlalchemy.schema.MetaData.create_all`.   If you check out
a copy of an application, running this will give you the entire database in one shot, without the need
to run through all those migration files, which are instead tailored towards applying incremental
changes to an existing database.

Alembic can integrate with a :meth:`~sqlalchemy.schema.MetaData.create_all` script quite easily.  After running the
create operation, tell Alembic to create a new version table, and to stamp it with the most recent
revision (i.e. ``head``)::

    # inside of a "create the database" script, first create
    # tables:
    my_metadata.create_all(engine)

    # then, load the Alembic configuration and generate the
    # version table, "stamping" it with the most recent rev:
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("/path/to/yourapp/alembic.ini")
    command.stamp(alembic_cfg, "head")

When this approach is used, the application can generate the database using normal SQLAlchemy
techniques instead of iterating through hundreds of migration scripts.   Now, the purpose of the
migration scripts is relegated just to movement between versions on out-of-date databases, not
*new* databases.    You can now remove old migration files that are no longer represented
on any existing environments.

To prune old migration files, simply delete the files.   Then, in the earliest, still-remaining
migration file, set ``down_revision`` to ``None``::

    # replace this:
    #down_revision = '290696571ad2'

    # with this:
    down_revision = None

That file now becomes the "base" of the migration series.
