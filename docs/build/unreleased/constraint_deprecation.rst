.. change::
    :tags: usecase

    Avoid deprecation warning in add/drop constraint added in SQLAlchemy 2.1.
    Ensure that alembic is compatible with the changes added in
    https://github.com/sqlalchemy/sqlalchemy/issues/13006
    by explicitly setting ``isolate_from_table=True`` when running with
    SQLAlchemy 2.1 or greater.
