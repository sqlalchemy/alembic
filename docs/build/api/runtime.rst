.. _alembic.runtime.environment.toplevel:

=======================
Runtime Objects
=======================

The "runtime" of Alembic involves the :class:`.EnvironmentContext`
and :class:`.MigrationContext` objects.   These are the objects that are
in play once the ``env.py`` script is loaded up by a command and
a migration operation proceeds.

The Environment Context
=======================

The :class:`.EnvironmentContext` class provides most of the
API used within an ``env.py`` script.  Within ``env.py``,
the instantiated :class:`.EnvironmentContext` is made available
via a special *proxy module* called ``alembic.context``.   That is,
you can import ``alembic.context`` like a regular Python module,
and each name you call upon it is ultimately routed towards the
current :class:`.EnvironmentContext` in use.

In particular, the key method used within ``env.py`` is :meth:`.EnvironmentContext.configure`,
which establishes all the details about how the database will be accessed.

.. automodule:: alembic.runtime.environment
    :members: EnvironmentContext

.. _alembic.runtime.migration.toplevel:

The Migration Context
=====================

The :class:`.MigrationContext` handles the actual work to be performed
against a database backend as migration operations proceed.  It is generally
not exposed to the end-user, except when the
:paramref:`~.EnvironmentContext.configure.on_version_apply` callback hook is used.

.. automodule:: alembic.runtime.migration
    :members: MigrationContext
