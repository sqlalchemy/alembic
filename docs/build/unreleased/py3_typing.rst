.. change::
    :tags: feature, general

    pep-484 type annotations have been added throughout the library.
    Additionally, stub .pyi files have been added for the "dynamically"
    generated Alembic modules ``alembic.op`` and ``alembic.config``, which
    include complete function signatures and docstrings, so that the functions
    in these namespaces will have both IDE support (vscode, pycharm, etc) as
    well as support for typing tools like Mypy. The files themselves are
    statically generated from their source functions within the source tree.