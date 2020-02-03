.. change::
    :tags: usecase, environment
    :tickets: 648

    Moved the use of the ``__file__`` attribute at the base of the Alembic
    package into the one place that it is specifically needed, which is when
    the config attempts to locate the template directory. This helps to allow
    Alembic to be fully importable in environments that are using Python
    memory-only import schemes.  Pull request courtesy layday.
