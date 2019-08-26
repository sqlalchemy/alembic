.. change::
    :tags: bug, py3k

    Fixed use of the deprecated "imp" module, which is used to detect  pep3147
    availability as well as to locate .pyc files, which started  emitting
    deprecation warnings during the test suite.   The warnings were not being
    emitted earlier during the test suite, the change is possibly due to
    changes in py.test itself but this is not clear. The check for pep3147 is
    set to True for any Python version 3.5 or greater now and importlib is used
    when available.  Note that some dependencies such as distutils may still be
    emitting this warning. Tests are adjusted to accommodate for dependencies
    that emit the warning as well.

