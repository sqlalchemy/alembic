.. change::
    :tags: change, internals

    The test suite for Alembic now makes use of SQLAlchemy's testing framework
    directly.  Previously, Alembic had its own version of this framework that
    was mostly copied from that of SQLAlchemy to enable testing with older
    SQLAlchemy versions.  The majority of this code is now removed so that both
    projects can leverage improvements from a common testing framework.
