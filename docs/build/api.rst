===========
API Details
===========

This section describes some key functions used within the migration process, particularly those referenced within
a migration environment's ``env.py`` file.

env.py Directives
=================

.. autofunction:: sqlalchemy.engine.engine_from_config
.. autofunction:: alembic.context.configure_connection
.. autofunction:: alembic.context.run_migrations

Internals
=========

.. automodule:: alembic.config
    :members:
    :undoc-members:

.. automodule:: alembic.command
    :members:
    :undoc-members:

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

MySQL
^^^^^

.. automodule:: alembic.ddl.mysql
    :members:
    :undoc-members:

MS-SQL
^^^^^^

.. automodule:: alembic.ddl.mssql
    :members:
    :undoc-members:

Postgresql
^^^^^^^^^^

.. automodule:: alembic.ddl.postgresql
    :members:
    :undoc-members:

SQLite
^^^^^^

.. automodule:: alembic.ddl.sqlite
    :members:
    :undoc-members:
