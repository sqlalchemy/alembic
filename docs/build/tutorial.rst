========
Tutorial
========

Alembic provides for the creation, management, and invocation of *change management* 
scripts for a relational database, using `SQLAlchemy <http://www.sqlalchemy.org>`_ as the underlying engine.
This tutorial will provide a full introduction to the theory and usage of this tool.

Installation
============

Install Alembic with `pip <http://pypi.python.org/pypi/pip>`_ or a similar tool::

    pip install alembic

The install will add the ``alembic`` command to the environment.  All operations with Alembic
then proceed through the usage of this command.

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
                3512b954651e.py
                2b1ae634e5cd.py
                3adcc9a56557.py

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
    script_location = alembic
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

This file contains the following features:

* ``[alembic]`` - this is the section read by Alembic to determine configuration.  Alembic
  itself does not directly read any other areas of the file.
* ``script_location`` - this is the location of the Alembic environment, relative to 
  the location of the .ini file [TODO: verify this].   It can also be an absolute
  file path.  This is the only key required by Alembic in all cases.   The generation 
  of the .ini file by the command ``alembic init alembic`` automatically placed the 
  directory name ``alembic`` here.
* ``sqlalchemy.url`` - A URL to connect to the database via SQLAlchemy.  This key is in fact
  only referenced within the ``env.py`` file that is specific to the "generic" configuration;
  a file that can be customized by the developer. A multiple
  database configuration may respond to multiple keys here, or may reference other sections
  of the file.
* ``[loggers]``, ``[handlers]``, ``[formatters]``, ``[logger_*]``, ``[handler_*]``, 
  ``[formatter_*]`` - these sections are all part of Python's standard logging configuration,
  the mechanics of which are documented at `Configuration File Format <http://docs.python.org/library/logging.config.html#configuration-file-format>`_.
  As is the case with the database connection, these directives are used directly as the
  result of the ``logging.config.fileConfig()`` call present in the fully customizable
  ``env.py`` script.

For starting up with just a single database and the generic configuration, setting up
the SQLAlchemy URL is all that's needed::

    sqlalchemy.url = postgresql://scott:tiger@localhost/test

Create a Migration Script
=========================

With the environment in place we can create a new revision, using ``alembic revision``::

    $ alembic revision -m "add a column"
    Generating /path/to/yourproject/alembic/versions/1975ea83b712.py...done

A new file 1975ea83b712.py is generated.  Looking inside the file::

    """add a column

    Revision ID: 1975ea83b712
    Revises: None
    Create Date: 2011-11-08 11:40:27.089406

    """

    # downgrade revision identifier, used by Alembic.
    down_revision = None

    from alembic.op import *

    def upgrade():
        pass

    def downgrade():
        pass

The file contains some header information, a "downgrade revision identifier", an import
of basic Alembic directives, and empty ``upgrade()`` and ``downgrade()`` functions.  Our 
job here is to populate the ``upgrade()`` and ``downgrade()`` functions with directives that
will apply a set of changes to our database.    Typically, ``upgrade()`` is required
while ``downgrade()`` is only needed if down-revision capability is desired, though it's
probably a good idea.

Another thing to notice is the ``down_revision`` variable.  This is how Alembic 
knows the correct order in which to apply migrations.   When we create the next revision,
the new file's ``down_revision`` identifier would point to this one::

    # downgrade revision identifier, used by Alembic.
    down_revision = '1975ea83b712'

Every time Alembic runs an operation against the ``versions/`` directory, it reads all
the files in, and composes a list based on how the ``down_revision`` identifiers link together,
with the ``down_revision`` of ``None`` representing the first file.   In theory, if a
migration environment had thousands of migrations, this could begin to add some latency to 
startup, but in practice a project should probably prune old migrations anyway
(see the section :ref:`building_uptodate` for a description on how to do this, while maintaining
the ability to build the current database fully).

We can then add some directives to our script, suppose adding a new table ``account``::

    from sqlalchemy import Integer, String, Unicode, Column

    def upgrade():
        create_table(
            'account',
            Column('id', Integer, primary_key=True),
            Column('name', String(50), nullable=False),
            Column('description', Unicode(200)),
        )

    def downgrade():
        drop_table('account')

foo::

    def upgrade():
        add_column('accounts', 
            Column('account_id', INTEGER, ForeignKey('accounts.id'))
        )

    def downgrade():
        drop_column('organization', 'account_id')
        drop_table("accounts")




.. _building_uptodate:

Building an Up to Date Database from Scratch
=============================================

There's a theory of database migrations that says that the revisions in existence for a database should be
able to go from an entirely blank schema to the finished product, and back again.   Alembic can roll
this way.   Though we think it's kind of overkill, considering that SQLAlchemy itself can emit 
the full CREATE statements for any given model using :meth:`.MetaData.create_all`.   If you check out
a copy of an application, running this will give you the entire database in one shot, without the need
to run through all those migration files, which are instead tailored towards applying incremental
changes to an existing database.

Alembic can integrate with a :meth:`.MetaData.create_all` script quite easily.  After running the
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
