.. _ops:

===================
Operation Reference
===================

This file provides documentation on Alembic migration directives.

The directives here are used within user-defined migration files,
within the ``upgrade()`` and ``downgrade()`` functions, as well as 
any functions further invoked by those.  

The functions here all require that a :class:`.Context` has been
configured within the ``env.py`` script.  Under normal circumstances
this is always the case, as the migration scripts are invoked via
the :func:`.context.run_migrations` function which ultimately
is derived from the :class:`.Context` object.


.. automodule:: alembic.op
    :members:
