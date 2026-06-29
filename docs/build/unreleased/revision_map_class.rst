.. change::
    :tags: usecase, scripts
    :tickets:

    Added a ``revision_map_class`` configuration option to
    :class:`.ScriptDirectory`, allowing a custom subclass of
    :class:`.RevisionMap` to be specified.  This enables external packages to
    implement custom revision ordering logic, such as ordering based on git
    history, without changes to Alembic core.  The option can be set in
    ``alembic.ini`` or ``pyproject.toml`` using a dotted Python path in
    ``"module:ClassName"`` format.  :class:`.RevisionMap` is now also exported
    from the ``alembic.script`` package for convenient subclassing.

