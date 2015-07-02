.. _api:

===========
API Details
===========

This section describes some key functions used within the migration process, particularly those referenced within
a migration environment's ``env.py`` file.

Overview
========

The three main objects in use are the :class:`.EnvironmentContext`, :class:`.MigrationContext`,
and :class:`.Operations` classes, pictured below.

.. image:: api_overview.png

An Alembic command begins by instantiating an :class:`.EnvironmentContext` object, then
making it available via the ``alembic.context`` proxy module.  The ``env.py``
script, representing a user-configurable migration environment, is then
invoked.   The ``env.py`` script is then responsible for calling upon the
:meth:`.EnvironmentContext.configure`, whose job it is to create
a :class:`.MigrationContext` object.

Before this method is called, there's not
yet any database connection or dialect-specific state set up.  While
many methods on :class:`.EnvironmentContext` are usable at this stage,
those which require database access, or at least access to the kind
of database dialect in use, are not.   Once the
:meth:`.EnvironmentContext.configure` method is called, the :class:`.EnvironmentContext`
is said to be *configured* with database connectivity, available via
a new :class:`.MigrationContext` object.   The :class:`.MigrationContext`
is associated with the :class:`.EnvironmentContext` object
via the :meth:`.EnvironmentContext.get_context` method.

Finally, ``env.py`` calls upon the :meth:`.EnvironmentContext.run_migrations`
method.   Within this method, a new :class:`.Operations` object, which
provides an API for individual database migration operations, is established
within the ``alembic.op`` proxy module.   The :class:`.Operations` object
uses the :class:`.MigrationContext` object ultimately as a source of
database connectivity, though in such a way that it does not care if the
:class:`.MigrationContext` is talking to a real database or just writing
out SQL to a file.

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

The Migration Context
=====================

.. automodule:: alembic.runtime.migration
    :members: MigrationContext

The Operations Object
=====================

Within migration scripts, actual database migration operations are handled
via an instance of :class:`.Operations`.   The :class:`.Operations` class
lists out available migration operations that are linked to a
:class:`.MigrationContext`, which communicates instructions originated
by the :class:`.Operations` object into SQL that is sent to a database or SQL
output stream.

Most methods on the :class:`.Operations` class are generated dynamically
using a "plugin" system, described in the next section
:ref:`operation_plugins`.   Additionally, when Alembic migration scripts
actually run, the methods on the current :class:`.Operations` object are
proxied out to the :mod:`alembic.op` module, so that they are available
using module-style access.

For an overview of how to use an :class:`.Operations` object directly
in programs, as well as for reference to the standard operation methods
as well as "batch" methods, see :ref:`ops`.

.. _operation_plugins:

Operation Plugins
-----------------

The Operations object is extensible using a plugin system.   This system
allows one to add new ``op.<some_operation>`` methods at runtime.  The
steps to use this system are to first create a subclass of
:class:`.MigrateOperation`, register it using the :meth:`.Operations.register_operation`
class decorator, then build a default "implementation" function which is
established using the :meth:`.Operations.implementation_for` decorator.

.. versionadded:: 0.8.0 - the :class:`.Operations` class is now an
   open namespace that is extensible via the creation of new
   :class:`.MigrateOperation` subclasses.

Below we illustrate a very simple operation ``CreateSequenceOp`` which
will implement a new method ``op.create_sequence()`` for use in
migration scripts::

    from alembic.operations import Operations, MigrateOperation

    @Operations.register_operation("create_sequence")
    class CreateSequenceOp(MigrateOperation):
        """Create a SEQUENCE."""

        def __init__(self, sequence_name, **kw):
            self.sequence_name = sequence_name
            self.kw = kw

        @classmethod
        def create_sequence(cls, operations, sequence_name, **kw):
            """Issue a "CREATE SEQUENCE" instruction."""

            op = CreateSequenceOp(sequence_name, **kw)
            return operations.invoke(op)

Above, the ``CreateSequenceOp`` class represents a new operation that will
be available as ``op.create_sequence()``.   The reason the operation
is represented as a stateful class is so that an operation and a specific
set of arguments can be represented generically; the state can then correspond
to different kinds of operations, such as invoking the instruction against
a database, or autogenerating Python code for the operation into a
script.

In order to establish the migrate-script behavior of the new operation,
we use the :meth:`.Operations.implementation_for` decorator::

    @Operations.implementation_for(CreateSequenceOp)
    def create_sequence(operations, operation):
        operations.execute("CREATE SEQUENCE %s" % operation.sequence_name)

Above, we use the simplest possible technique of invoking our DDL, which
is just to call :meth:`.Operations.execute` with literal SQL.  If this is
all a custom operation needs, then this is fine.  However, options for
more comprehensive support include building out a custom SQL construct,
as documented at :ref:`sqlalchemy.ext.compiles`.

With the above two steps, a migration script can now use a new method
``op.create_sequence()`` that will proxy to our object as a classmethod::

    def upgrade():
        op.create_sequence("my_sequence")

The registration of new operations only needs to occur in time for the
``env.py`` script to invoke :meth:`.MigrationContext.run_migrations`;
within the module level of the ``env.py`` script is sufficient.


.. versionadded:: 0.8 - the migration operations available via the
   :class:`.Operations` class as well as the :mod:`alembic.op` namespace
   is now extensible using a plugin system.


.. _operation_objects:

Built-in Operation Objects
--------------------------

The migration operations present on :class:`.Operations` are themselves
delivered via operation objects that represent an operation and its
arguments.   All operations descend from the :class:`.MigrateOperation`
class, and are registered with the :class:`.Operations` class using
the :meth:`.Operations.register_operation` class decorator.  The
:class:`.MigrateOperation` objects also serve as the basis for how the
autogenerate system renders new migration scripts.

.. seealso::

    :ref:`operation_plugins`

    :ref:`customizing_revision`

The built-in operation objects are listed below.

.. automodule:: alembic.operations.ops
    :members:


Commands
=========

Alembic commands are all represented by functions in the :mod:`alembic.command`
package.  They all accept the same style of usage, being sent
the :class:`~.alembic.config.Config` object as the first argument.

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

.. currentmodule:: alembic.command

.. automodule:: alembic.command
    :members:

Configuration
==============

The :class:`.Config` object represents the configuration
passed to the Alembic environment.  From an API usage perspective,
it is needed for the following use cases:

* to create a :class:`.ScriptDirectory`, which allows you to work
  with the actual script files in a migration environment
* to create an :class:`.EnvironmentContext`, which allows you to
  actually run the ``env.py`` module within the migration environment
* to programatically run any of the commands in the :mod:`alembic.command`
  module.

The :class:`.Config` is *not* needed for these cases:

* to instantiate a :class:`.MigrationContext` directly - this object
  only needs a SQLAlchemy connection or dialect name.
* to instantiate a :class:`.Operations` object - this object only
  needs a :class:`.MigrationContext`.

.. currentmodule:: alembic.config

.. automodule:: alembic.config
    :members:

Script Directory
================

The :class:`.ScriptDirectory` object provides programmatic access
to the Alembic version files present in the filesystem.

.. automodule:: alembic.script
    :members:

Revision
========

The :class:`.RevisionMap` object serves as the basis for revision
management, used exclusively by :class:`.ScriptDirectory`.

.. automodule:: alembic.script.revision
    :members:

Autogeneration
==============

The autogenerate system has two areas of API that are public:

1. The ability to do a "diff" of a :class:`.MetaData` object against
   a database, and receive a data structure back.  This structure
   is available either as a rudimentary list of changes, or as
   a :class:`.MigrateOperation` structure.

2. The ability to alter how the ``alembic revision`` command generates
   revision scripts, including support for multiple revision scripts
   generated in one pass.

Getting Diffs
-------------

.. autofunction:: alembic.autogenerate.compare_metadata

.. autofunction:: alembic.autogenerate.produce_migrations

.. _customizing_revision:

Customizing Revision Generation
-------------------------------

.. versionadded:: 0.8.0 - the ``alembic revision`` system is now customizable.

The ``alembic revision`` command, also available programmatically
via :func:`.command.revision`, essentially produces a single migration
script after being run.  Whether or not the ``--autogenerate`` option
was specified basically determines if this script is a blank revision
script with empty ``upgrade()`` and ``downgrade()`` functions, or was
produced with alembic operation directives as the result of autogenerate.

In either case, the system creates a full plan of what is to be done
in the form of a :class:`.MigrateOperation` structure, which is then
used to produce the script.

For example, suppose we ran ``alembic revision --autogenerate``, and the
end result was that it produced a new revision ``'eced083f5df'``
with the following contents::

    """create the organization table."""

    # revision identifiers, used by Alembic.
    revision = 'eced083f5df'
    down_revision = 'beafc7d709f'

    from alembic import op
    import sqlalchemy as sa


    def upgrade():
        op.create_table(
            'organization',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(50), nullable=False)
        )
        op.add_column(
            'user',
            sa.Column('organization_id', sa.Integer())
        )
        op.create_foreign_key(
            'org_fk', 'user', 'organization', ['organization_id'], ['id']
        )

    def downgrade():
        op.drop_constraint('org_fk', 'user')
        op.drop_column('user', 'organization_id')
        op.drop_table('organization')

The above script is generated by a :class:`.MigrateOperation` structure
that looks like this::

    from alembic.operations import ops
    import sqlalchemy as sa

    migration_script = ops.MigrationScript(
        'eced083f5df',
        ops.UpgradeOps(
            ops=[
                ops.CreateTableOp(
                    'organization',
                    [
                        sa.Column('id', sa.Integer(), primary_key=True),
                        sa.Column('name', sa.String(50), nullable=False)
                    ]
                ),
                ops.ModifyTableOps(
                    'user',
                    ops=[
                        ops.AddColumnOp(
                            'user',
                            sa.Column('organization_id', sa.Integer())
                        ),
                        ops.CreateForeignKeyOp(
                            'org_fk', 'user', 'organization',
                            ['organization_id'], ['id']
                        )
                    ]
                )
            ]
        ),
        ops.DowngradeOps(
            ops=[
                ops.ModifyTableOps(
                    'user',
                    ops=[
                        ops.DropConstraintOp('org_fk', 'user'),
                        ops.DropColumnOp('user', 'organization_id')
                    ]
                ),
                ops.DropTableOp('organization')
            ]
        ),
        message='create the organization table.'
    )

When we deal with a :class:`.MigrationScript` structure, we can render
the upgrade/downgrade sections into strings for debugging purposes
using the :func:`.render_python_code` helper function::

    from alembic.autogenerate import render_python_code
    print(render_python_code(migration_script.upgrade_ops))

Renders::

    ### commands auto generated by Alembic - please adjust! ###
        op.create_table('organization',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        op.add_column('user', sa.Column('organization_id', sa.Integer(), nullable=True))
        op.create_foreign_key('org_fk', 'user', 'organization', ['organization_id'], ['id'])
        ### end Alembic commands ###

Given that structures like the above are used to generate new revision
files, and that we'd like to be able to alter these as they are created,
we then need a system to access this structure when the
:func:`.command.revision` command is used.  The
:paramref:`.EnvironmentContext.configure.process_revision_directives`
parameter gives us a way to alter this.   This is a function that
is passed the above structure as generated by Alembic, giving us a chance
to alter it.
For example, if we wanted to put all the "upgrade" operations into
a certain branch, and we wanted our script to not have any "downgrade"
operations at all, we could build an extension as follows, illustrated
within an ``env.py`` script::

    def process_revision_directives(context, revision, directives):
        script = directives[0]

        # set specific branch
        script.head = "mybranch@head"

        # erase downgrade operations
        script.downgrade_ops.ops[:] = []

    # ...

    def run_migrations_online():

        # ...
        with engine.connect() as connection:

            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                process_revision_directives=process_revision_directives)

            with context.begin_transaction():
                context.run_migrations()

Above, the ``directives`` argument is a Python list.  We may alter the
given structure within this list in-place, or replace it with a new
structure consisting of zero or more :class:`.MigrationScript` directives.
The :func:`.command.revision` command will then produce scripts corresponding
to whatever is in this list.

.. autofunction:: alembic.autogenerate.render_python_code

Autogenerating Custom Operation Directives
------------------------------------------

In the section :ref:`operation_plugins`, we talked about adding new
subclasses of :class:`.MigrateOperation` in order to add new ``op.``
directives.  In the preceding section :ref:`customizing_revision`, we
also learned that these same :class:`.MigrateOperation` structures are at
the base of how the autogenerate system knows what Python code to render.
How to connect these two systems, so that our own custom operation
directives can be used?  First off, we'd probably be implementing
a :paramref:`.EnvironmentContext.configure.process_revision_directives`
plugin as described previously, so that we can add our own directives
to the autogenerate stream.  What if we wanted to add our ``CreateSequenceOp``
to the autogenerate structure?  We basically need to define an autogenerate
renderer for it, as follows::

    # note: this is a continuation of the example from the
    # "Operation Plugins" section

    from alembic.autogenerate import renderers

    @renderers.dispatch_for(CreateSequenceOp)
    def render_create_sequence(autogen_context, op):
        return "op.create_sequence(%r, **%r)" % (
            op.sequence_name,
            op.kw
        )

With our render function established, we can our ``CreateSequenceOp``
generated in an autogenerate context using the :func:`.render_python_code`
debugging function in conjunction with an :class:`.UpgradeOps` structure::

    from alembic.operations import ops
    from alembic.autogenerate import render_python_code

    upgrade_ops = ops.UpgradeOps(
        ops=[
            CreateSequenceOp("my_seq")
        ]
    )

    print(render_python_code(upgrade_ops))

Which produces::

    ### commands auto generated by Alembic - please adjust! ###
        op.create_sequence('my_seq', **{})
        ### end Alembic commands ###

DDL Internals
=============

These are some of the constructs used to generate migration
instructions.  The APIs here build off of the :class:`sqlalchemy.schema.DDLElement`
and :mod:`sqlalchemy.ext.compiler` systems.

For programmatic usage of Alembic's migration directives, the easiest
route is to use the higher level functions given by :mod:`alembic.operations`.

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
-----

.. automodule:: alembic.ddl.mysql
    :members:
    :undoc-members:
    :show-inheritance:

MS-SQL
------

.. automodule:: alembic.ddl.mssql
    :members:
    :undoc-members:
    :show-inheritance:

Postgresql
----------

.. automodule:: alembic.ddl.postgresql
    :members:
    :undoc-members:
    :show-inheritance:

SQLite
------

.. automodule:: alembic.ddl.sqlite
    :members:
    :undoc-members:
    :show-inheritance:
