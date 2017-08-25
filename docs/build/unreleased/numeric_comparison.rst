.. change::
    :tags: bug, autogenerate
    :pullreq: bitbucket:70

    Fixed bug where comparison of ``Numeric`` types would produce
    a difference if the Python-side ``Numeric`` inadvertently specified
    a non-None "scale" with a "precision" of None, even though this ``Numeric``
    type will pass over the "scale" argument when rendering. Pull request
    courtesy Ivan Mmelnychuk.
