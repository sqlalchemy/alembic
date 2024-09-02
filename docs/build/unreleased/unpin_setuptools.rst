.. change::
    :tags: change, general

    The pin for ``setuptools<69.3`` in ``pyproject.toml`` has been removed.
    This pin was to prevent a sudden change to :pep:`625` in setuptools from
    taking place which changes the file name of SQLAlchemy's source
    distribution on pypi to be an all lower case name, and the change was
    extended to all SQLAlchemy projects to prevent any further surprises.
    However, the presence of this pin is now holding back environments that
    otherwise want to use a newer setuptools, so we've decided to move forward
    with this change, with the assumption that build environments will have
    largely accommodated the setuptools change by now.



