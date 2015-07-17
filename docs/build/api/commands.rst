.. _alembic.command.toplevel:

=========
Commands
=========

.. note:: this section discusses the **internal API of Alembic**
   as regards its command invocation system.
   This section is only useful for developers who wish to extend the
   capabilities of Alembic.  For documentation on using Alembic commands,
   please see :doc:`/tutorial`.

Alembic commands are all represented by functions in the :ref:`alembic.command.toplevel`
package.  They all accept the same style of usage, being sent
the :class:`.Config` object as the first argument.

Commands can be run programmatically, by first constructing a :class:`.Config`
object, as in::

    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("/path/to/yourapp/alembic.ini")
    command.upgrade(alembic_cfg, "head")

In many cases, and perhaps more often than not, an application will wish
to call upon a series of Alembic commands and/or other features.  It is
usually a good idea to link multiple commands along a single connection
and transaction, if feasible.  This can be achieved using the
:attr:`.Config.attributes` dictionary in order to share a connection::

    with engine.begin() as connection:
        alembic_cfg.attributes['connection'] = connection
        command.upgrade(alembic_cfg, "head")

This recipe requires that ``env.py`` consumes this connection argument;
see the example in :ref:`connection_sharing` for details.

To write small API functions that make direct use of database and script directory
information, rather than just running one of the built-in commands,
use the :class:`.ScriptDirectory` and :class:`.MigrationContext`
classes directly.

.. automodule:: alembic.command
    :members:
