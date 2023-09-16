.. change::
    :tags: typing, bug
    :tickets: 1058, 1277

    Improved the ``op.execute()`` method to correctly accept the
    ``Executable`` type that is the same which is used in SQLAlchemy
    ``Connection.execute()``.  Pull request courtesy Mihail Milushev.
