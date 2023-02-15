.. change::
    :tags: bug, commands

    Fixed regression introduced in 1.7.0 where the "config" object passed to
    the template context when running the :func:`.merge` command
    programmatically failed to be correctly populated. Pull request courtesy
    Brendan Gann.
