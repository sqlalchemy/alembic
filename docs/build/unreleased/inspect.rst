.. change::
    :tags: change

    The internal inspection routines no longer use SQLAlchemy's
    ``Inspector.from_engine()`` method, which is expected to be deprecated in
    1.4.  The ``inspect()`` function is now used.

