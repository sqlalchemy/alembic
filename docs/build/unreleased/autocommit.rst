.. change::
    :tags: changed, environment

    To accommodate SQLAlchemy 1.4 and 2.0, the migration model now no longer
    assumes that the SQLAlchemy Connection will autocommit an individual
    operation.   This essentially means that for databases that use
    non-transactional DDL (pysqlite current driver behavior, MySQL), there is
    still a BEGIN/COMMIT block that will surround each individual migration.
    Databases that support transactional DDL should continue to have the
    same flow, either per migration or per-entire run, depending on the
    value of the :paramref:`.Environment.configure.transaction_per_migration`
    flag.


.. change::
    :tags: changed, environment

    A :class:`.CommandError` is raised if a ``sqlalchemy.engine.Engine`` is
    passed to the :meth:`.MigrationContext.configure` method instead of a
    ``sqlalchemy.engine.Connection`` object.  Previously, this would be a
    warning only.