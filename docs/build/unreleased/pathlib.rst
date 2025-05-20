.. change::
    :tags: change, environment

    The command, config and script modules now rely on ``pathlib.Path`` for
    internal path manipulations, instead of ``os.path()`` operations.   Public
    API functions that accept string directories and filenames continue to do
    so but also accept ``os.PathLike`` objects.  Public API functions and
    accessors that return paths as strings continue to do so.   Private API
    functions and accessors, i.e. all those that are prefixed with an
    underscore, may now return a Path object rather than a string to indicate
    file paths.
