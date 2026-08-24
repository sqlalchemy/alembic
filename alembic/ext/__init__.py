"""Opt-in plugins that ship with Alembic.

Plugins in this namespace are deliberately outside of
``alembic.autogenerate``, so that they are not matched by the default
``"alembic.autogenerate.*"`` wildcard and must instead be named explicitly
within :paramref:`.EnvironmentContext.configure.autogenerate_plugins`.

"""
