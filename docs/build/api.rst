===========
API Details
===========

This section describes some key functions used within the migration process, particularly those referenced within
a migration environment's ``env.py`` file.

env.py Directives
=================

The :mod:`alembic.context` module contains API features that are generally used within
``env.py`` files.

The central object in use is the :class:`.Context` object.   This object is 
made present when the ``env.py`` script calls upon the :func:`.configure`
method for the first time.  Before this function is called, there's not
yet any database connection or dialect-specific state set up, and those
functions which require this state will raise an exception when used,
until :func:`.configure` is called successfully.


.. autofunction:: sqlalchemy.engine.engine_from_config

.. currentmodule:: alembic.context

.. automodule:: alembic.context
    :members:

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

.. currentmodule:: alembic.command

.. automodule:: alembic.command
    :members:
    :undoc-members:

Configuration
==============

.. currentmodule:: alembic.config

.. automodule:: alembic.config
    :members:
    :undoc-members:


Internals
=========

.. automodule:: alembic.script
    :members:
    :undoc-members:

DDL Internals
-------------

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
^^^^^

.. automodule:: alembic.ddl.mysql
    :members:
    :undoc-members:
    :show-inheritance:

MS-SQL
^^^^^^

.. automodule:: alembic.ddl.mssql
    :members:
    :undoc-members:
    :show-inheritance:

Postgresql
^^^^^^^^^^

.. automodule:: alembic.ddl.postgresql
    :members:
    :undoc-members:
    :show-inheritance:

SQLite
^^^^^^

.. automodule:: alembic.ddl.sqlite
    :members:
    :undoc-members:
    :show-inheritance:
