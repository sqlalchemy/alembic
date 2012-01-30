.. _ops:

===================
Operation Reference
===================

This file provides documentation on Alembic migration directives.

The directives here are used within user-defined migration files,
within the ``upgrade()`` and ``downgrade()`` functions, as well as 
any functions further invoked by those.  

All directives exist as methods on a class called :class:`.Operations`.
When migration scripts are run, this object is made available
to the script via the ``alembic.op`` datamember, which is
a *proxy* to an actual instance of :class:`.Operations`.
Currently, ``alembic.op`` is a real Python module, populated
with individual proxies for each method on :class:`.Operations`,
so symbols can be imported safely from the ``alembic.op`` namespace.

A key design philosophy to the :mod:`alembic.operations` methods is that
to the greatest degree possible, they internally generate the 
appropriate SQLAlchemy metadata, typically involving
:class:`~sqlalchemy.schema.Table` and :class:`~sqlalchemy.schema.Constraint`
objects.  This so that migration instructions can be 
given in terms of just the string names and/or flags involved.   
The exceptions to this
rule include the :meth:`~.Operations.add_column` and :meth:`~.Operations.create_table`
directives, which require full :class:`~sqlalchemy.schema.Column`
objects, though the table metadata is still generated here.

The functions here all require that a :class:`.MigrationContext` has been
configured within the ``env.py`` script first, which is typically
via :meth:`.EnvironmentContext.configure`.   Under normal
circumstances they are called from an actual migration script, which
itself would be invoked by the :meth:`.EnvironmentContext.run_migrations`
method.


.. automodule:: alembic.operations
    :members:
