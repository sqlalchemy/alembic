.. change::
    :tags: feature, general

    pep-484 type annotations have been added throughout the library. This
    should be helpful in providing Mypy and IDE support, however there is not
    full support for Alembic's dynamically modified "op" namespace as of yet; a
    future release will likely modify the approach used for importing this
    namespace to be better compatible with pep-484 capabilities.