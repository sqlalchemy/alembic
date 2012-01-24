.. _ops:

===================
Operation Reference
===================

This file provides documentation on Alembic migration directives.

The directives here are used within user-defined migration files,
within the ``upgrade()`` and ``downgrade()`` functions, as well as 
any functions further invoked by those.  

A key design philosophy to the :mod:`alembic.op` functions is that
to the greatest degree possible, they internally generate the 
appropriate SQLAlchemy metadata, typically involving
:class:`~sqlalchemy.schema.Table` and :class:`~sqlalchemy.schema.Constraint`
objects.  This so that migration instructions can be 
given in terms of just the string names and/or flags involved.   
The exceptions to this
rule include the :func:`.op.add_column` and :func:`.op.create_table`
directives, which require full :class:`~sqlalchemy.schema.Column`
objects, though the table metadata is still generated here.

The functions here all require that a :class:`.Context` has been
configured within the ``env.py`` script.  Under normal circumstances
this is always the case, as the migration scripts are invoked via
the :func:`.context.run_migrations` function which ultimately
is derived from the :class:`.Context` object.


.. automodule:: alembic.operations
    :members:
