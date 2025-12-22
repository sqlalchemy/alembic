# mypy: allow-untyped-defs, allow-incomplete-defs, allow-untyped-calls
# mypy: no-warn-return-any, allow-any-generics
from __future__ import annotations

from typing import Any
from typing import cast
from typing import Collection
from typing import TYPE_CHECKING

from sqlalchemy.sql.elements import conv
from typing_extensions import Self

from ...util import sqla_compat

if TYPE_CHECKING:
    from sqlalchemy import Table
    from sqlalchemy.engine import Inspector
    from sqlalchemy.engine.interfaces import ReflectedForeignKeyConstraint
    from sqlalchemy.engine.interfaces import ReflectedIndex
    from sqlalchemy.engine.interfaces import ReflectedUniqueConstraint
    from sqlalchemy.engine.reflection import _ReflectionInfo

_INSP_KEYS = (
    "columns",
    "pk_constraint",
    "foreign_keys",
    "indexes",
    "unique_constraints",
    "table_comment",
    "check_constraints",
    "table_options",
)
_CONSTRAINT_INSP_KEYS = (
    "pk_constraint",
    "foreign_keys",
    "indexes",
    "unique_constraints",
    "check_constraints",
)


class _InspectorConv:
    __slots__ = ("inspector",)

    def __new__(cls, inspector: Inspector) -> Self:
        obj: Any
        if sqla_compat.sqla_2:
            obj = object.__new__(_SQLA2InspectorConv)
            _SQLA2InspectorConv.__init__(obj, inspector)
        else:
            obj = object.__new__(_LegacyInspectorConv)
            _LegacyInspectorConv.__init__(obj, inspector)
        return cast(Self, obj)

    def __init__(self, inspector: Inspector):
        self.inspector = inspector

    def pre_cache_tables(
        self,
        schema: str | None,
        tablenames: list[str],
        all_available_tablenames: Collection[str],
    ) -> None:
        pass

    def get_unique_constraints(
        self, tname: str, schema: str | None
    ) -> list[ReflectedUniqueConstraint]:
        raise NotImplementedError()

    def get_indexes(
        self, tname: str, schema: str | None
    ) -> list[ReflectedIndex]:
        raise NotImplementedError()

    def get_foreign_keys(
        self, tname: str, schema: str | None
    ) -> list[ReflectedForeignKeyConstraint]:
        raise NotImplementedError()

    def reflect_table(self, table: Table) -> None:
        raise NotImplementedError()


class _LegacyInspectorConv(_InspectorConv):

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

    def get_indexes(
        self, tname: str, schema: str | None
    ) -> list[ReflectedIndex]:
        return self._apply_reflectinfo_conv(
            self.inspector.get_indexes(tname, schema=schema)
        )

    def get_unique_constraints(
        self, tname: str, schema: str | None
    ) -> list[ReflectedUniqueConstraint]:
        return self._apply_reflectinfo_conv(
            self.inspector.get_unique_constraints(tname, schema=schema)
        )

    def get_foreign_keys(
        self, tname: str, schema: str | None
    ) -> list[ReflectedForeignKeyConstraint]:
        return self._apply_reflectinfo_conv(
            self.inspector.get_foreign_keys(tname, schema=schema)
        )

    def reflect_table(self, table: Table) -> None:
        self.inspector.reflect_table(table, include_columns=None)

        self._apply_constraint_conv(table.constraints)
        self._apply_constraint_conv(table.indexes)


class _SQLA2InspectorConv(_InspectorConv):

    def _pre_cache(
        self,
        schema: str | None,
        tablenames: list[str],
        all_available_tablenames: Collection[str],
        info_key: str,
        inspector_method: Any,
    ) -> None:

        if info_key in self.inspector.info_cache:
            return

        # heuristic vendored from SQLAlchemy 2.0
        # if more than 50% of the tables in the db are in filter_names load all
        # the tables, since it's most likely faster to avoid a filter on that
        # many tables. also if a dialect doesnt have a "multi" method then
        # return the filter names
        if tablenames and all_available_tablenames and len(tablenames) > 100:
            fraction = len(tablenames) / len(all_available_tablenames)
        else:
            fraction = None

        if (
            fraction is None
            or fraction <= 0.5
            or not self.inspector.dialect._overrides_default(
                inspector_method.__name__
            )
        ):
            optimized_filter_names = tablenames
        else:
            optimized_filter_names = None

        try:
            elements = inspector_method(
                schema=schema, filter_names=optimized_filter_names
            )
        except NotImplementedError:
            self.inspector.info_cache[info_key] = NotImplementedError
        else:
            self.inspector.info_cache[info_key] = elements

    def _return_from_cache(
        self,
        tname: str,
        schema: str | None,
        info_key: str,
        inspector_method: Any,
        apply_constraint_conv: bool = False,
        optional=True,
    ) -> Any:
        not_in_cache = object()

        if info_key in self.inspector.info_cache:
            cache = self.inspector.info_cache[info_key]
            if cache is NotImplementedError:
                if optional:
                    return {}
                else:
                    # maintain NotImplementedError as alembic compare
                    # uses these to determine classes of construct that it
                    # should not compare to DB elements
                    raise NotImplementedError()

            individual = cache.get((schema, tname), not_in_cache)

            if individual is not not_in_cache:
                if apply_constraint_conv and individual is not None:
                    return self._apply_reflectinfo_conv(individual)
                else:
                    return individual

        try:
            data = inspector_method(tname, schema=schema)
        except NotImplementedError:
            if optional:
                return {}
            else:
                raise

        if apply_constraint_conv:
            return self._apply_reflectinfo_conv(data)
        else:
            return data

    def get_unique_constraints(
        self, tname: str, schema: str | None
    ) -> list[ReflectedUniqueConstraint]:
        return self._return_from_cache(
            tname,
            schema,
            "alembic_unique_constraints",
            self.inspector.get_unique_constraints,
            apply_constraint_conv=True,
            optional=False,
        )

    def get_indexes(
        self, tname: str, schema: str | None
    ) -> list[ReflectedIndex]:
        return self._return_from_cache(
            tname,
            schema,
            "alembic_indexes",
            self.inspector.get_indexes,
            apply_constraint_conv=True,
            optional=False,
        )

    def get_foreign_keys(
        self, tname: str, schema: str | None
    ) -> list[ReflectedForeignKeyConstraint]:
        return self._return_from_cache(
            tname,
            schema,
            "alembic_foreign_keys",
            self.inspector.get_foreign_keys,
            apply_constraint_conv=True,
        )

    def _apply_reflectinfo_conv(self, consts):
        if not consts:
            return consts
        for const in consts if not isinstance(consts, dict) else [consts]:
            if const["name"] is not None and not isinstance(
                const["name"], conv
            ):
                const["name"] = conv(const["name"])
        return consts

    def pre_cache_tables(
        self,
        schema: str | None,
        tablenames: list[str],
        all_available_tablenames: Collection[str],
    ) -> None:
        for key in _INSP_KEYS:
            keyname = f"alembic_{key}"
            meth = getattr(self.inspector, f"get_multi_{key}")

            self._pre_cache(
                schema,
                tablenames,
                all_available_tablenames,
                keyname,
                meth,
            )

    def _make_reflection_info(
        self, tname: str, schema: str | None
    ) -> _ReflectionInfo:
        from sqlalchemy.engine.reflection import _ReflectionInfo

        table_key = (schema, tname)

        return _ReflectionInfo(
            unreflectable={},
            **{
                key: {
                    table_key: self._return_from_cache(
                        tname,
                        schema,
                        f"alembic_{key}",
                        getattr(self.inspector, f"get_{key}"),
                        apply_constraint_conv=(key in _CONSTRAINT_INSP_KEYS),
                    )
                }
                for key in _INSP_KEYS
            },
        )

    def reflect_table(self, table: Table) -> None:
        ri = self._make_reflection_info(table.name, table.schema)

        self.inspector.reflect_table(
            table,
            include_columns=None,
            resolve_fks=False,
            _reflect_info=ri,
        )
