from __future__ import annotations

import re

_postgresql_add_enum_value_re = re.compile(
    r"(?is)^\s*ALTER\s+TYPE\b.*\bADD\s+VALUE\b"
)
_postgresql_add_value_token_re = re.compile(
    r"(?i)\bADD\s+VALUE\b(?!\s+IF\s+NOT\s+EXISTS)"
)


def add_if_not_exists_to_enum_value(sqltext: str) -> str:
    if not _postgresql_add_enum_value_re.search(sqltext):
        return sqltext
    return _postgresql_add_value_token_re.sub(
        "ADD VALUE IF NOT EXISTS", sqltext, count=1
    )

