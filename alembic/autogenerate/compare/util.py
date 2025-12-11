# mypy: allow-untyped-defs, allow-incomplete-defs, allow-untyped-calls
# mypy: no-warn-return-any, allow-any-generics

from sqlalchemy.sql.elements import conv


class _InspectorConv:
    __slots__ = ("inspector",)

    def __init__(self, inspector):
        self.inspector = inspector

    def _apply_reflectinfo_conv(self, consts):
        if not consts:
            return consts
        for const in consts:
            if const["name"] is not None and not isinstance(
                const["name"], conv
            ):
                const["name"] = conv(const["name"])
        return consts

    def _apply_constraint_conv(self, consts):
        if not consts:
            return consts
        for const in consts:
            if const.name is not None and not isinstance(const.name, conv):
                const.name = conv(const.name)
        return consts

    def get_indexes(self, *args, **kw):
        return self._apply_reflectinfo_conv(
            self.inspector.get_indexes(*args, **kw)
        )

    def get_unique_constraints(self, *args, **kw):
        return self._apply_reflectinfo_conv(
            self.inspector.get_unique_constraints(*args, **kw)
        )

    def get_foreign_keys(self, *args, **kw):
        return self._apply_reflectinfo_conv(
            self.inspector.get_foreign_keys(*args, **kw)
        )

    def reflect_table(self, table, *, include_columns):
        self.inspector.reflect_table(table, include_columns=include_columns)

        # I had a cool version of this using _ReflectInfo, however that doesn't
        # work in 1.4 and it's not public API in 2.x.  Then this is just a two
        # liner.  So there's no competition...
        self._apply_constraint_conv(table.constraints)
        self._apply_constraint_conv(table.indexes)
