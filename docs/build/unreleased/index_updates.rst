.. change::
    :tags: usecase, autogenerate, postgresql

    Added support for autogenerate comparison of indexes on PostgreSQL which
    include SQL expressions, when using SQLAlchemy 2.0; the previous warning
    that such indexes were skipped are removed when the new functionality
    is in use.  When using SQLAlchemy versions prior to the 2.0 series,
    the indexes continue to be skipped with a warning.
