.. _alembic.runtime.environment.toplevel:

=======================
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

.. automodule:: alembic.runtime.environment
    :members: EnvironmentContext
