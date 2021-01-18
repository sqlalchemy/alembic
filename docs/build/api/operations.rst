.. _alembic.operations.toplevel:

=====================
Operation Directives
=====================

.. note:: this section discusses the **internal API of Alembic** as regards
   the internal system of defining migration operation directives.
   This section is only useful for developers who wish to extend the
   capabilities of Alembic.  For end-user guidance on Alembic migration
   operations, please see :ref:`ops`.

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
proxied out to the ``alembic.op`` module, so that they are available
using module-style access.

For an overview of how to use an :class:`.Operations` object directly
in programs, as well as for reference to the standard operation methods
as well as "batch" methods, see :ref:`ops`.

.. _operation_plugins:

Operation Plugins
=====================

The Operations object is extensible using a plugin system.   This system
allows one to add new ``op.<some_operation>`` methods at runtime.  The
steps to use this system are to first create a subclass of
:class:`.MigrateOperation`, register it using the :meth:`.Operations.register_operation`
class decorator, then build a default "implementation" function which is
established using the :meth:`.Operations.implementation_for` decorator.

Below we illustrate a very simple operation ``CreateSequenceOp`` which
will implement a new method ``op.create_sequence()`` for use in
migration scripts::

    from alembic.operations import Operations, MigrateOperation

    @Operations.register_operation("create_sequence")
    class CreateSequenceOp(MigrateOperation):
        """Create a SEQUENCE."""

        def __init__(self, sequence_name, schema=None):
            self.sequence_name = sequence_name
            self.schema = schema

        @classmethod
        def create_sequence(cls, operations, sequence_name, **kw):
            """Issue a "CREATE SEQUENCE" instruction."""

            op = CreateSequenceOp(sequence_name, **kw)
            return operations.invoke(op)

        def reverse(self):
            # only needed to support autogenerate
            return DropSequenceOp(self.sequence_name, schema=self.schema)

    @Operations.register_operation("drop_sequence")
    class DropSequenceOp(MigrateOperation):
        """Drop a SEQUENCE."""

        def __init__(self, sequence_name, schema=None):
            self.sequence_name = sequence_name
            self.schema = schema

        @classmethod
        def drop_sequence(cls, operations, sequence_name, **kw):
            """Issue a "DROP SEQUENCE" instruction."""

            op = DropSequenceOp(sequence_name, **kw)
            return operations.invoke(op)

        def reverse(self):
            # only needed to support autogenerate
            return CreateSequenceOp(self.sequence_name, schema=self.schema)

Above, the ``CreateSequenceOp`` and ``DropSequenceOp`` classes represent
new operations that will
be available as ``op.create_sequence()`` and ``op.drop_sequence()``.
The reason the operations
are represented as stateful classes is so that an operation and a specific
set of arguments can be represented generically; the state can then correspond
to different kinds of operations, such as invoking the instruction against
a database, or autogenerating Python code for the operation into a
script.

In order to establish the migrate-script behavior of the new operations,
we use the :meth:`.Operations.implementation_for` decorator::

    @Operations.implementation_for(CreateSequenceOp)
    def create_sequence(operations, operation):
        if operation.schema is not None:
            name = "%s.%s" % (operation.schema, operation.sequence_name)
        else:
            name = operation.sequence_name
        operations.execute("CREATE SEQUENCE %s" % name)


    @Operations.implementation_for(DropSequenceOp)
    def drop_sequence(operations, operation):
        if operation.schema is not None:
            name = "%s.%s" % (operation.schema, operation.sequence_name)
        else:
            name = operation.sequence_name
        operations.execute("DROP SEQUENCE %s" % name)

Above, we use the simplest possible technique of invoking our DDL, which
is just to call :meth:`.Operations.execute` with literal SQL.  If this is
all a custom operation needs, then this is fine.  However, options for
more comprehensive support include building out a custom SQL construct,
as documented at :ref:`sqlalchemy.ext.compiler_toplevel`.

With the above two steps, a migration script can now use new methods
``op.create_sequence()`` and ``op.drop_sequence()`` that will proxy to
our object as a classmethod::

    def upgrade():
        op.create_sequence("my_sequence")

    def downgrade():
        op.drop_sequence("my_sequence")

The registration of new operations only needs to occur in time for the
``env.py`` script to invoke :meth:`.MigrationContext.run_migrations`;
within the module level of the ``env.py`` script is sufficient.

.. seealso::

    :ref:`autogen_custom_ops` - how to add autogenerate support to
    custom operations.

.. _operation_objects:
.. _alembic.operations.ops.toplevel:

Built-in Operation Objects
==============================

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
