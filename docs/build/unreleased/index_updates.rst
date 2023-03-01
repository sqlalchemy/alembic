.. change::
    :tags: usecase, autogenerate, postgresql

    Added support for autogenerate comparison of indexes on PostgreSQL which
    include SQL expressions; the previous warning that such indexes were
    skipped is now removed. This functionality requires SQLAlchemy 2.0.
    For older SQLAlchemy versions, these indexes are still skipped.
