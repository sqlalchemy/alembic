.. _api:

===========
API Details
===========

This section describes some key functions used within the migration process, particularly those referenced within
a migration environment's ``env.py`` file.

Overview
========

The three main objects in use are the :class:`.EnvironmentContext`, :class:`.MigrationContext`,
and :class:`.Operations` classes, pictured below.

.. image:: api_overview.png

An Alembic command begins by instantiating an :class:`.EnvironmentContext` object, then
making it available via the ``alembic.context`` proxy module.  The ``env.py``
script, representing a user-configurable migration environment, is then 
invoked.   The ``env.py`` script is then responsible for calling upon the
:meth:`.EnvironmentContext.configure`, whose job it is to create 
a :class:`.MigrationContext` object. 

Before this method is called, there's not
yet any database connection or dialect-specific state set up.  While 
many methods on :class:`.EnvironmentContext` are usable at this stage,
those which require database access, or at least access to the kind 
of database dialect in use, are not.   Once the 
:meth:`.EnvironmentContext.configure` method is called, the :class:`.EnvironmentContext`
is said to be *configured* with database connectivity, available via
a new :class:`.MigrationContext` object.   The :class:`.MigrationContext`
is associated with the :class:`.EnvironmentContext` object
via the :meth:`.EnvironmentContext.get_context` method.

Finally, ``env.py`` calls upon the :meth:`.EnvironmentContext.run_migrations`
method.   Within this method, a new :class:`.Operations` object, which
provides an API for individual database migration operations, is established
within the ``alembic.op`` proxy module.   The :class:`.Operations` object
uses the :class:`.MigrationContext` object ultimately as a source of 
database connectivity, though in such a way that it does not care if the
:class:`.MigrationContext` is talking to a real database or just writing
out SQL to a file.

The Environment Context
=======================

The :class:`.EnvironmentContext` class provides most of the
API used within an ``env.py`` script.  Within ``env.py``, 
the instantated :class:`.EnvironmentContext` is made available
via a special *proxy module* called ``alembic.context``.   That is,
you can import ``alembic.context`` like a regular Python module,
and each name you call upon it is ultimately routed towards the
current :class:`.EnvironmentContext` in use.

In particular, the key method used within ``env.py`` is :meth:`.EnvironmentContext.configure`,
which establishes all the details about how the database will be accessed.

.. automodule:: alembic.environment
    :members:

The Migration Context
=====================

.. automodule:: alembic.migration
    :members:

The Operations Object
=====================

Within migration scripts, actual database migration operations are handled
via an instance of :class:`.Operations`.    See :ref:`ops` for an overview
of this object.

Commands
=========

Alembic commands are all represented by functions in the :mod:`alembic.command`
package.  They all accept the same style of usage, being sent
the :class:`~.alembic.config.Config` object as the first argument.

Commands can be run programmatically, by first constructing a :class:`.Config` 
object, as in::

    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("/path/to/yourapp/alembic.ini")
    command.upgrade(alembic_cfg, "head")

To write small API functions that make direct use of database and script directory
information, rather than just running one of the built-in commands,
use the :class:`.ScriptDirectory` and :class:`.MigrationContext`
classes directly.

.. currentmodule:: alembic.command

.. automodule:: alembic.command
    :members:

Configuration
==============

The :class:`.Config` object represents the configuration 
passed to the Alembic environment.  From an API usage perspective,
it is needed for the following use cases:

* to create a :class:`.ScriptDirectory`, which allows you to work
  with the actual script files in a migration environment
* to create an :class:`.EnvironmentContext`, which allows you to 
  actually run the ``env.py`` module within the migration environment
* to programatically run any of the commands in the :mod:`alembic.command`
  module.

The :class:`.Config` is *not* needed for these cases:

* to instantiate a :class:`.MigrationContext` directly - this object
  only needs a SQLAlchemy connection or dialect name.
* to instantiate a :class:`.Operations` object - this object only
  needs a :class:`.MigrationContext`.

.. currentmodule:: alembic.config

.. automodule:: alembic.config
    :members:

Script Directory
================

The :class:`.ScriptDirectory` object provides programmatic access
to the Alembic version files present in the filesystem.

.. automodule:: alembic.script
    :members:

Autogeneration
==============

Alembic 0.3 introduces a small portion of the autogeneration system
as a public API.

.. autofunction:: alembic.autogenerate.compare_metadata

DDL Internals
=============

These are some of the constructs used to generate migration
instructions.  The APIs here build off of the :class:`sqlalchemy.schema.DDLElement`
and :mod:`sqlalchemy.ext.compiler` systems.

For programmatic usage of Alembic's migration directives, the easiest
route is to use the higher level functions given by :mod:`alembic.operations`.

.. automodule:: alembic.ddl
    :members:
    :undoc-members:

.. automodule:: alembic.ddl.base
    :members:
    :undoc-members:

.. automodule:: alembic.ddl.impl
    :members:
    :undoc-members:

MySQL
-----

.. automodule:: alembic.ddl.mysql
    :members:
    :undoc-members:
    :show-inheritance:

MS-SQL
------

.. automodule:: alembic.ddl.mssql
    :members:
    :undoc-members:
    :show-inheritance:

Postgresql
----------

.. automodule:: alembic.ddl.postgresql
    :members:
    :undoc-members:
    :show-inheritance:

SQLite
------

.. automodule:: alembic.ddl.sqlite
    :members:
    :undoc-members:
    :show-inheritance:
