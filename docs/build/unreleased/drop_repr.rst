.. change::
    :tags: bug, autogenerate

    The "op.drop_constraint()" directive will now render using ``repr()`` for
    the schema name, in the same way that "schema" renders for all the other op
    directives.  Pull request courtesy Denis Kataev.
