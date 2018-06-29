.. change::
    :tags: bug, autogenerate

    Fixed issue where "autoincrement=True" would not render for a column that
    specified it, since as of SQLAlchemy 1.1 this is no longer the default
    value for "autoincrement".  Note the behavior only takes effect against the
    SQLAlchemy 1.1.0 and higher; for pre-1.1 SQLAlchemy, "autoincrement=True"
    does not render as was the case before. Pull request courtesy  Elad Almos.
