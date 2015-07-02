========
Overview
========

A visualization of the primary features of Alembic's internals is presented
in the following figure.   The module and class boxes do not list out
all the operations provided by each unit; only a small set of representative
elements intended to convey the primary purpose of each system.

.. image:: api_overview.png

The script runner for Alembic is present in the :mod:`alembic.config` module.
This module produces a :class:`.Config` object and passes it to the
appropriate function in :mod:`alembic.command`.   Functions within
:mod:`alembic.command` will typically instantiate an
:class:`.ScriptDirectory` instance, which represents the collection of
version files, and an :class:`.EnvironmentContext`, which represents a
configurational object passed to the environment's ``env.py`` script.

Within the execution of ``env.py``, a :class:`.MigrationContext`
object is produced when the :meth:`.EnvironmentContext.configure`
method is called.  :class:`.MigrationContext` is the gateway to the database
for other parts of the application, and produces a :class:`.DefaultImpl`
object which does the actual database communication, and knows how to
create the specific SQL text of the various DDL directives such as
ALTER TABLE; :class:`.DefaultImpl` has subclasses that are per-database-backend.
In "offline" mode (e.g. ``--sql``), the :class:`.MigrationContext` will
produce SQL to a file output stream instead of a database.

During an upgrade or downgrade operation, a specific series of migration
scripts are invoked starting with the :class:`.MigrationContext` in conjunction
with the :class:`.ScriptDirectory`; the actual scripts themselves make use
of the :class:`.Operations` object, which provide the end-user interface to
specific database operations.   The :class:`.Operations` object is generated
based on a series of "operation directive" objects that are user-extensible,
and start out in the :mod:`alembic.operations.ops` module.

Another prominent feature of Alembic is the "autogenerate" feature, which
produces new migration scripts that contain Python code.  The autogenerate
feature starts in :mod:`alembic.autogenerate`, and is used exclusively
by the :func:`.alembic.command.revision` command when the ``--autogenerate``
flag is passed.  Autogenerate refers to the :class:`.MigrationContext`
and :class:`.DefaultImpl` in order to access database connectivity and
access per-backend rules for autogenerate comparisons.  It also makes use
of :mod:`alembic.operations.ops` in order to represent the operations that
it will render into scripts.

