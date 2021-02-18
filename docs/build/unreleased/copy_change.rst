.. change::
    :tags: bug

    Adjusted the use of SQLAlchemy's ".copy()" internals to use "._copy()"
    for version 1.4.0, as this method is being renamed.
