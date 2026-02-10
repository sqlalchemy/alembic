.. change::
    :tags: bug, operations
    :tickets: 1232

    Reverted the behavior of :meth:`.Operations.add_column` that would
    automatically render the "PRIMARY KEY" keyword inline when a
    :class:`.Column` with ``primary_key=True`` is added. The automatic
    behavior, added in version 1.18.2, is now opt-in via the new
    :paramref:`.Operations.add_column.inline_primary_key` parameter. This
    change restores the ability to render a PostgreSQL SERIAL column, which is
    required to be ``primary_key=True``, while not impacting the ability to
    render a separate primary key constraint. This also provides consistency
    with the :paramref:`.Operations.add_column.inline_references` parameter and
    gives users explicit control over SQL generation.

    To render PRIMARY KEY inline, use the
    :paramref:`.Operations.add_column.inline_primary_key` parameter set to
    ``True``::

        op.add_column(
            "my_table",
            Column("id", Integer, primary_key=True),
            inline_primary_key=True
        )
