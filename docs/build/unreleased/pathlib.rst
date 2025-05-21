.. change::
    :tags: refactored, environment

    The command, config and script modules now rely on ``pathlib.Path`` for
    internal path manipulations, instead of ``os.path()`` operations.   This
    has some impact on both public and private (i.e. underscored) API functions:

    * Public API functions that accept parameters indicating file and directory
      paths as strings will continue to do so, but now will also accept
      ``os.PathLike`` objects as well.
    * Public API functions and accessors that return directory paths as strings
      such as :attr:`.ScriptDirectory.dir`, :attr:`.Config.config_file_name`
      will continue to do so.
    * Private API functions and accessors, i.e. all those that are prefixed
      with an underscore, that previously returned directory paths as
      strings may now return a Path object instead.
