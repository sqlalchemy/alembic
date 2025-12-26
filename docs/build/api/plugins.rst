.. _alembic.plugins.toplevel:

=======
Plugins
=======

.. versionadded:: 1.18.0

Alembic provides a plugin system that allows third-party extensions to
integrate with Alembic's functionality. Plugins can register custom operations,
operation implementations, autogenerate comparison functions, and other
extension points to add new capabilities to Alembic.

The plugin system provides a structured way to organize and distribute these
extensions, allowing them to be discovered automatically using Python
entry points.

Overview
========

The :class:`.Plugin` class provides the foundation for creating plugins.
A plugin's ``setup()`` function can perform various types of registrations:

* **Custom operations** - Register new operation directives using
  :meth:`.Operations.register_operation` (e.g., ``op.create_view()``)
* **Operation implementations** - Provide database-specific implementations
  using :meth:`.Operations.implementation_for`
* **Autogenerate comparators** - Add comparison functions for detecting
  schema differences during autogeneration
* **Other extensions** - Register any other global handlers or customizations

A single plugin can register handlers across all of these categories. For
example, a plugin for custom database objects might register both the
operations to create/drop those objects and the autogenerate logic to
detect changes to them.

.. seealso::

    :ref:`replaceable_objects` - Cookbook recipe demonstrating custom
    operations and implementations that would be suitable for packaging
    as a plugin

Installing and Using Plugins
============================

Third-party plugins are typically distributed as Python packages that can be
installed via pip or other package managers::

    pip install mycompany-alembic-plugin

Once installed, plugins that use Python's entry point system are automatically
discovered and loaded by Alembic at startup, which calls the plugin's
``setup()`` function to perform any registrations.

Enable Autogenerate Plugins
---------------------------

For plugins that provide autogenerate comparison functions via the
:meth:`.Plugin.add_autogenerate_comparator` hook, the specific autogenerate
functionality registered by the plugin must be enabled with
:paramref:`.EnvironmentContext.configure.autogenerate_plugins` parameter, which
by default indicates that only Alembic's built-in plugins should be used.
Note that this step does not apply to older plugins that may be registering
autogenerate comparison functions globally.

See the section :ref:`plugins_autogenerate` for background on enabling
autogenerate comparison plugins per environment.

Using Plugins without entry points (such as local plugin code)
--------------------------------------------------------------

Plugins do not need to be published with entry points to be used. A plugin
can be manually registered by calling :meth:`.Plugin.setup_plugin_from_module`
in the ``env.py`` file::

    from alembic.runtime.plugins import Plugin
    import myproject.alembic_plugin

    # Register the plugin manually
    Plugin.setup_plugin_from_module(
        myproject.alembic_plugin,
        "myproject.custom_operations"
    )

This approach is useful for project-specific plugins that are not intended
for distribution, or for testing plugins during development.

.. _plugins_autogenerate:

Enabling Autogenerate Plugins in env.py
=======================================

If a plugin provides autogenerate functionality that's registered via the
:meth:`.Plugin.add_autogenerate_comparator` hook, it can be selectively enabled
or disabled using the
:paramref:`.EnvironmentContext.configure.autogenerate_plugins` parameter in the
:meth:`.EnvironmentContext.configure` call, typically as used within the
``env.py`` file.   This parameter is passed as a list of strings each naming a
specific plugin or a matching wildcard.  The default value is
``["alembic.autogenerate.*"]`` which indicates that the full set of Alembic's
internal plugins should be used.

The :paramref:`.EnvironmentContext.configure.autogenerate_plugins` parameter
accepts a list of string patterns:

* Simple names match plugin names exactly: ``"alembic.autogenerate.tables"``
* Wildcards match multiple plugins: ``"alembic.autogenerate.*"`` matches all
  built-in plugins
* Negation patterns exclude plugins: ``"~alembic.autogenerate.comments"``
  excludes the comments plugin

For example, to use all built-in plugins except comments, plus a custom
plugin::

    context.configure(
        # ...
        autogenerate_plugins=[
            "alembic.autogenerate.*",
            "~alembic.autogenerate.comments",
            "mycompany.custom_types",
        ]
    )

The wildcard syntax using ``*`` indicates that tokens in that segment
of the name (separated by period characters) will match any name.   For
Alembic's ``alembic.autogenerate.*`` namespace, the built in names being
invoked are:

* ``alembic.autogenerate.schemas`` - Schema creation and dropping
* ``alembic.autogenerate.tables`` - Table creation, dropping, and modification.
  This plugin depends on the ``schemas`` plugin in order to iterate through
  tables.
* ``alembic.autogenerate.types`` - Column type changes.  This plugin depends on
  the ``tables`` plugin in order to iterate through columns.
* ``alembic.autogenerate.constraints`` - Constraint creation and dropping. This
  plugin depends on the ``tables`` plugin in order to iterate through columns.
* ``alembic.autogenerate.defaults`` - Server default changes. This plugin
  depends on the ``tables`` plugin in order to iterate through columns.
* ``alembic.autogenerate.comments`` - Table and column comment changes.  This
  plugin depends on the ``tables`` plugin in order to iterate through columns.

While these names can be specified individually, they are subject to change
as Alembic evolves. Using the wildcard pattern is recommended.

Omitting the built-in plugins entirely would prevent autogeneration from
proceeding, unless other plugins were provided that replaced its functionality
(which is possible!). Additionally, as noted above, the column-oriented plugins
rely on the table- and schema- oriented plugins in order to receive iterated
columns.

The :paramref:`.EnvironmentContext.configure.autogenerate_plugins`
parameter only controls which plugins participate in autogenerate
operations. Other plugin functionality, such as custom operations
registered with :meth:`.Operations.register_operation`, is available
regardless of this setting.




Writing a Plugin
================

Creating a Plugin Module
-------------------------

A plugin module must define a ``setup()`` function that accepts a
:class:`.Plugin` instance. This function is called when the plugin is
loaded, either automatically via entry points or manually via
:meth:`.Plugin.setup_plugin_from_module`::

    from alembic import op
    from alembic.operations import Operations
    from alembic.runtime.plugins import Plugin
    from alembic.util import DispatchPriority

    def setup(plugin: Plugin) -> None:
        """Setup function called by Alembic when loading the plugin."""

        # Register custom operations
        Operations.register_operation("create_view")(CreateViewOp)
        Operations.implementation_for(CreateViewOp)(create_view_impl)

        # Register autogenerate comparison functions
        plugin.add_autogenerate_comparator(
            _compare_views,
            "view",
            qualifier="default",
            priority=DispatchPriority.MEDIUM,
        )

The ``setup()`` function serves as the entry point for all plugin
registrations. It can call various Alembic APIs to extend functionality.

Publishing a Plugin
-------------------

To make a plugin available for installation via pip, create a package with
an entry point in ``pyproject.toml``::

    [project.entry-points."alembic.plugins"]
    mycompany.plugin_name = "mycompany.alembic_plugin"

Where ``mycompany.alembic_plugin`` is the module containing the ``setup()``
function.

When the package is installed, Alembic automatically discovers and loads the
plugin through the entry point system. If the plugin provides autogenerate
functionality, users can then enable it by adding its name
``mycompany.plugin_name`` to the ``autogenerate_plugins`` list in their
``env.py``.

Registering Custom Operations
------------------------------

Plugins can register new operation directives that become available as
``op.custom_operation()`` in migration scripts. This is done using
:meth:`.Operations.register_operation` and
:meth:`.Operations.implementation_for`.

Example from the :ref:`replaceable_objects` recipe::

    from alembic.operations import Operations, MigrateOperation

    class CreateViewOp(MigrateOperation):
        def __init__(self, view_name, select_stmt):
            self.view_name = view_name
            self.select_stmt = select_stmt

    @Operations.register_operation("create_view")
    class CreateViewOp(CreateViewOp):
        pass

    @Operations.implementation_for(CreateViewOp)
    def create_view(operations, operation):
        operations.execute(
            f"CREATE VIEW {operation.view_name} AS {operation.select_stmt}"
        )

These registrations can be performed in the plugin's ``setup()`` function,
making the custom operations available globally.

.. seealso::

    :ref:`replaceable_objects` - Complete example of registering custom
    operations

    :ref:`operation_plugins` - Documentation on the operations plugin system

.. _plugins_registering_autogenerate:

Registering Autogenerate Comparators at the Plugin Level
--------------------------------------------------------

Plugins can register comparison functions that participate in the autogenerate
process, detecting differences between database schema and SQLAlchemy metadata.
These functions may be registered globally, where they take place
unconditionally as documented at
:ref:`autogenerate_global_comparison_function`; for older versions of Alembic
prior to 1.18.0 this is the only registration system available.  However when
targeting Alembic 1.18.0 or higher, the :class:`.Plugin` approach provides a
more configurable version of these registration hooks.

Plugin level comparison functions are registered using
:meth:`.Plugin.add_autogenerate_comparator`. Each comparison function
establishes itself as part of a named "target", which is invoked by a parent
handler.   For example, if a handler establishes itself as part of the
``"column"`` target, it will be invoked when the
``alembic.autogenerate.tables`` plugin proceeds through SQLAlchemy ``Table``
objects and invokes comparison operations for pairs of same-named columns.

For an example of a complete comparison function, see the example at
:ref:`autogenerate_global_comparison_function`.

The current levels of comparison are the same between global and plugin-level
comparison functions, and include:

* ``"autogenerate"`` - this target is invoked at the top of the autogenerate
  chain.  These hooks are passed a :class:`.AutogenContext` and an
  :class:`.UpgradeOps` collection.  Functions that subscribe to the
  ``autogenerate`` target should look like::

    from alembic.autogenerate.api import AutogenContext
    from alembic.operations.ops import UpgradeOps
    from alembic.runtime.plugins import Plugin
    from alembic.util import PriorityDispatchResult

    def autogen_toplevel(
        autogen_context: AutogenContext, upgrade_ops: UpgradeOps
    ) -> PriorityDispatchResult:
        #  ...


    def setup(plugin: Plugin) -> None:
        plugin.add_autogenerate_comparator(autogen_toplevel, "autogenerate")

  The function should return either :attr:`.PriorityDispatchResult.CONTINUE` or
  :attr:`.PriorityDispatchResult.STOP` to halt any further comparisons from
  proceeding, and should respond to detected changes by mutating the given
  :class:`.UpgradeOps` collection in place (the :class:`.DowngradeOps` version
  is produced later by reversing the :class:`.UpgradeOps`).

  An autogenerate compare function that seeks to run entirely independently of
  Alembic's built-in autogenerate plugins, or to replace them completely, would
  register at the ``"autogenerate"`` level.   The remaining levels indicated
  below are all invoked from within Alembic's own autogenerate plugins and will
  not take place if ``alembic.autogenerate.*`` is not enabled.

  .. versionadded:: 1.18.0 The ``"autogenerate"`` comparison scope was
     introduced, replacing ``"schema"`` as the topmost comparison scope.

* ``"schema"`` - this target is invoked for each individual "schema" being
  compared, and hooks are passed a :class:`.AutogenContext`, an
  :class:`.UpgradeOps` collection, and a set of schema names, featuring the
  value ``None`` for the "default" schema.   Functions that subscribe to the
  ``"schema"`` target should look like::

    from alembic.autogenerate.api import AutogenContext
    from alembic.operations.ops import UpgradeOps
    from alembic.runtime.plugins import Plugin
    from alembic.util import PriorityDispatchResult

    def autogen_for_tables(
        autogen_context: AutogenContext,
        upgrade_ops: UpgradeOps,
        schemas: set[str | None],
    ) -> PriorityDispatchResult:
        # ...

    def setup(plugin: Plugin) -> None:
        plugin.add_autogenerate_comparator(
            autogen_for_tables,
            "schema",
            "tables",
        )

  The function should normally return :attr:`.PriorityDispatchResult.CONTINUE`
  and should respond to detected changes by mutating the given
  :class:`.UpgradeOps` collection in place (the :class:`.DowngradeOps` version
  is produced later by reversing the :class:`.UpgradeOps`).

  The registration example above includes the ``"tables"`` "compare element",
  which is optional.   This indicates that the comparison function is part of a
  chain called "tables", which is what Alembic's own
  ``alembic.autogenerate.tables`` plugin uses.   If our custom comparison
  function were to return the value :attr:`.PriorityDispatchResult.STOP`,
  further comparison functions in the ``"tables"`` chain would not be called.
  Similarly, if another plugin in the ``"tables"`` chain returned
  :attr:`.PriorityDispatchResult.STOP`, then our plugin would not be called.
  Making use of :attr:`.PriorityDispatchResult.STOP` in terms of other plugins
  in the same "compare element" may be assisted by placing our function in the
  comparator chain using :attr:`.DispatchPriority.FIRST` or
  :attr:`.DispatchPriority.LAST` when registering.

* ``"table"`` - this target is invoked per ``Table`` being compared between a
  database autoloaded version and the local metadata version. These hooks are
  passed an :class:`.AutogenContext`, a :class:`.ModifyTableOps` collection, a
  schema name, table name, a :class:`~sqlalchemy.schema.Table` reflected from
  the database if any or ``None``, and a :class:`~sqlalchemy.schema.Table`
  present in the local :class:`~sqlalchemy.schema.MetaData`. If the
  :class:`.ModifyTableOps` collection contains changes after all hooks are run,
  it is included in the migration script::

    from sqlalchemy import quoted_name
    from sqlalchemy import Table

    from alembic.autogenerate.api import AutogenContext
    from alembic.operations.ops import ModifyTableOps
    from alembic.runtime.plugins import Plugin
    from alembic.util import PriorityDispatchResult

    def compare_tables(
        autogen_context: AutogenContext,
        modify_table_ops: ModifyTableOps,
        schema: str | None,
        tname: quoted_name | str,
        conn_table: Table | None,
        metadata_table: Table | None,
    ) -> PriorityDispatchResult:
        # ...


    def setup(plugin: Plugin) -> None:
        plugin.add_autogenerate_comparator(compare_tables, "table")

  This hook may be used to compare elements of tables, such as comments
  or database-specific storage configurations.  It should mutate the given
  :class:`.ModifyTableOps` object in place to add new change operations.

* ``"column"`` - this target is invoked per ``Column`` being compared between a
  database autoloaded version and the local metadata version.
  These hooks are passed an :class:`.AutogenContext`,
  an :class:`.AlterColumnOp` object, a schema name, table name,
  column name, a :class:`~sqlalchemy.schema.Column` reflected from the
  database and a :class:`~sqlalchemy.schema.Column` present in the
  local table.  If the :class:`.AlterColumnOp` contains changes after
  all hooks are run, it is included in the migration script;
  a "change" is considered to be present if any of the ``modify_`` attributes
  are set to a non-default value, or there are any keys
  in the ``.kw`` collection with the prefix ``"modify_"``::

    from typing import Any
    from sqlalchemy import quoted_name
    from sqlalchemy import Table

    from alembic.autogenerate.api import AutogenContext
    from alembic.operations.ops import AlterColumnOp
    from alembic.runtime.plugins import Plugin
    from alembic.util import PriorityDispatchResult

    def compare_columns(
        autogen_context: AutogenContext,
        alter_column_op: AlterColumnOp,
        schema: str | None,
        tname: quoted_name | str,
        cname: quoted_name | str,
        conn_col: Column[Any],
        metadata_col: Column[Any],
    ) -> PriorityDispatchResult:
      # ...


    def setup(plugin: Plugin) -> None:
        plugin.add_autogenerate_comparator(compare_columns, "column")

  Pre-existing compare chains within the ``"column"`` target include
  ``"comment"``, ``"server_default"``, and ``"types"``. Comparison functions
  here should mutate the given :class:`.AlterColumnOp` object in place to add
  new change operations.

.. seealso::

    :ref:`alembic.autogenerate.toplevel` - Detailed documentation on the
    autogenerate system

    :ref:`autogenerate_global_comparison_function` - a companion section
    to this one which explains autogenerate comparison functions in terms of
    the older "global" dispatch, but also includes a complete example of a
    comparison function.

    :ref:`customizing_revision` - Customizing autogenerate behavior


Plugin API Reference
====================

.. autoclass:: alembic.runtime.plugins.Plugin
    :members:

.. autoclass:: alembic.util.langhelpers.PriorityDispatchResult
    :members:

.. autoclass:: alembic.util.langhelpers.DispatchPriority
    :members:

.. seealso::

    :paramref:`.EnvironmentContext.configure.autogenerate_plugins` -
    Configuration parameter for enabling autogenerate plugins

    :ref:`operation_plugins` - Documentation on custom operations

    :ref:`replaceable_objects` - Example of custom operations suitable
    for a plugin

    :ref:`customizing_revision` - General information on customizing
    autogenerate behavior
