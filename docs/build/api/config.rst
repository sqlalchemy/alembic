.. _alembic.config.toplevel:

==============
Configuration
==============

.. note:: this section discusses the **internal API of Alembic** as
   regards internal configuration constructs.
   This section is only useful for developers who wish to extend the
   capabilities of Alembic.  For documentation on configuration of
   an Alembic environment, please see :doc:`/tutorial`.

The :class:`.Config` object represents the configuration
passed to the Alembic environment.  From an API usage perspective,
it is needed for the following use cases:

* to create a :class:`.ScriptDirectory`, which allows you to work
  with the actual script files in a migration environment
* to create an :class:`.EnvironmentContext`, which allows you to
  actually run the ``env.py`` module within the migration environment
* to programatically run any of the commands in the :ref:`alembic.command.toplevel`
  module.

The :class:`.Config` is *not* needed for these cases:

* to instantiate a :class:`.MigrationContext` directly - this object
  only needs a SQLAlchemy connection or dialect name.
* to instantiate a :class:`.Operations` object - this object only
  needs a :class:`.MigrationContext`.

.. automodule:: alembic.config
    :members:
