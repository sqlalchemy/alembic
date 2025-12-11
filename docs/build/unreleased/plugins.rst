.. change::
    :tags: feature, autogenerate

    Release 1.18.0 introduces a plugin system that allows for automatic
    loading of third-party extensions as well as configurable autogenerate
    compare functionality on a per-environment basis.

    The :class:`.Plugin` class provides a common interface for extensions that
    register handlers among Alembic's existing extension points such as
    :meth:`.Operations.register_operation` and
    :meth:`.Operations.implementation_for`. A new interface for registering
    autogenerate comparison handlers,
    :meth:`.Plugin.add_autogenerate_comparator`, provides for autogenerate
    compare functionality that may be custom-configured on a per-environment
    basis using the new
    :paramref:`.EnvironmentContext.configure.autogenerate_plugins` parameter.

    The change does not impact well known Alembic add-ons such as
    ``alembic-utils``, which continue to work as before; however, such add-ons
    have the option to provide plugin entrypoints going forward.

    As part of this change, Alembic's autogenerate compare functionality is
    reorganized into a series of internal plugins under the
    ``alembic.autogenerate`` namespace, which may be individually or
    collectively identified for inclusion and/or exclusion within the
    :meth:`.EnvironmentContext.configure` call using a new parameter
    :paramref:`.EnvironmentContext.configure.autogenerate_plugins`. This
    parameter is also where third party comparison plugins may also be
    indicated.

    See :ref:`alembic.plugins.toplevel` for complete documentation on
    the new :class:`.Plugin` class as well as autogenerate-specific usage
    instructions.
