.. change::
    :tags: bug, postgresql
    :tickets: 1321, 1327, 1356

    Additional fixes to PostgreSQL expression index compare feature.
    The compare now correctly accommodates casts and differences in
    spacing.
    Added detection logic for operation clauses inside the expression,
    skipping the compare of these expressions.
    To accommodate these changes the logic for the comparison of the
    indexes and unique constraints was moved to the dialect
    implementation, allowing greater flexibility.
