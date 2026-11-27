.. _alembic.ddl.toplevel:

=============
DDL Internals
=============

These are some of the constructs used to generate migration
instructions.  The APIs here build off of the :class:`sqlalchemy.schema.DDLElement`
and :ref:`sqlalchemy.ext.compiler_toplevel` systems.

For programmatic usage of Alembic's migration directives, the easiest
route is to use the higher level functions given by :ref:`alembic.operations.toplevel`.

.. _alembic.ddl.third_party:

Implementations for Third Party Dialects
========================================

Alembic selects a :class:`.DefaultImpl` based on the name of the SQLAlchemy
dialect being used. If an implementation does not exist for a dialect,
Alembic will raise :class:`.NoSuchDialectError`. Third-party SQLAlchemy
libraries are therefore encouraged to implement their own
:class:`.DefaultImpl`.

Declaring an implementation
---------------------------

Subclass :class:`.BaseImpl` and set ``__dialect__``::

    from alembic.ddl.impl import BaseImpl

    class NewDbImpl(BaseImpl):
        __dialect__ = "newdb"

The implementation is registered for the ``__dialect__`` when the class is
defined.

Registering via entry point
---------------------------

.. versionadded:: 1.21.0

Third-party implementations can be registered via entry-points.
The name of the entry-point should match the name of the SQLAlchemy dialect:

.. code-block:: toml

    [project.entry-points."alembic.dialects"]
    newdb = "newdb_sqlalchemy.alembic:NewDbImpl"

When the ``context.configure()`` in ``env.py`` builds a
:class:`.MigrationContext`, Alembic will scan for entry-points matching to
the dialect required for the migration.  Entry-points are not consulted for
dialects Alembic implements itself.

If ``env.py`` declares an implementation for a dialect defined in an entry
point, the one in ``env.py`` is used; see
:meth:`.BaseImpl.resolve_registration_conflict`.

Built-In Implementation Reference
=================================

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
=============

.. automodule:: alembic.ddl.mysql
    :members:
    :undoc-members:
    :show-inheritance:

MS-SQL
=============

.. automodule:: alembic.ddl.mssql
    :members:
    :undoc-members:
    :show-inheritance:

Postgresql
=============

.. automodule:: alembic.ddl.postgresql
    :members:
    :undoc-members:
    :show-inheritance:

SQLite
=============

.. automodule:: alembic.ddl.sqlite
    :members:
    :undoc-members:
    :show-inheritance:
