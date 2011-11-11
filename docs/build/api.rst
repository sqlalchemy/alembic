===========
API Details
===========

This section describes some key functions used within the migration process, particularly those referenced within
a migration environment's ``env.py`` file.

env.py Directives
=================

.. autofunction:: sqlalchemy.engine.engine_from_config
.. autofunction:: alembic.context.configure
.. autofunction:: alembic.context.get_context
.. autofunction:: alembic.context.execute
.. autofunction:: alembic.context.requires_connection
.. autofunction:: alembic.context.run_migrations

Internals
=========

.. currentmodule:: alembic.command

Commands
--------

Alembic commands are all represented by functions in the :mod:`alembic.command`
package.  They all accept the same style of usage, being sent
the :class:`~.alembic.config.Config` object as the first argument.


.. automodule:: alembic.command
    :members:
    :undoc-members:

Misc
----
.. automodule:: alembic.config
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
