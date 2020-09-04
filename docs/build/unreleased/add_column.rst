.. change::
    :tags: bug, batch

    Fixed issue where columns in a foreign-key referenced table would be
    replaced with null-type columns during a batch operation; while this did
    not generally have any side effects, it could theoretically impact a batch
    operation that also targets that table directly and also would interfere
    with future changes to the ``.append_column()`` method to disallow implicit
    replacement of columns.