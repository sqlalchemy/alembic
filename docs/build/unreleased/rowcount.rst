.. change::
    :tags: bug, environment

    The check for matched rowcount when the alembic_version table is updated or
    deleted from is now conditional based on whether or not the dialect
    supports the concept of "rowcount" for UPDATE or DELETE rows matched.  Some
    third party dialects do not support this concept.  Pull request courtesy Ke
    Zhu.
