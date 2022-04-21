from sqlalchemy import exc as sqla_exc
from sqlalchemy import text

from alembic.testing import exclusions
from alembic.testing.requirements import SuiteRequirements
from alembic.util import compat
from alembic.util import sqla_compat


class DefaultRequirements(SuiteRequirements):
    @property
    def unicode_string(self):
        return exclusions.skip_if(["oracle"])

    @property
    def alter_column(self):
        return exclusions.skip_if(["sqlite"], "no ALTER COLUMN support")

    @property
    def schemas(self):
        """Target database must support external schemas, and have one
        named 'test_schema'."""

        return exclusions.skip_if(["sqlite", "firebird"], "no schema support")

    @property
    def no_referential_integrity(self):
        """test will fail if referential integrity is enforced"""

        return exclusions.fails_on_everything_except("sqlite")

    @property
    def non_native_boolean(self):
        """test will fail if native boolean is provided"""

        return exclusions.fails_if(
            exclusions.LambdaPredicate(
                lambda config: config.db.dialect.supports_native_boolean
            )
        )

    @property
    def non_native_boolean_check_constraint(self):
        """backend creates a check constraint for booleans if enabled"""

        return exclusions.only_on(
            exclusions.LambdaPredicate(
                lambda config: not config.db.dialect.supports_native_boolean
                and config.db.dialect.non_native_boolean_check_constraint
            )
        )

    @property
    def check_constraints_w_enforcement(self):
        return exclusions.fails_on(["mysql", "mariadb"])

    @property
    def unnamed_constraints(self):
        """constraints without names are supported."""
        return exclusions.only_on(["sqlite"])

    @property
    def fk_names(self):
        """foreign key constraints always have names in the DB"""
        return exclusions.fails_on("sqlite")

    @property
    def reflects_fk_options(self):
        return exclusions.open()

    @property
    def fk_initially(self):
        """backend supports INITIALLY option in foreign keys"""
        return exclusions.only_on(["postgresql"])

    @property
    def fk_deferrable(self):
        """backend supports DEFERRABLE option in foreign keys"""
        return exclusions.only_on(["postgresql", "oracle"])

    @property
    def fk_deferrable_is_reflected(self):
        return self.fk_deferrable + exclusions.fails_on("oracle")

    @property
    def fk_ondelete_restrict(self):
        return exclusions.only_on(["postgresql", "sqlite", "mysql"])

    @property
    def fk_onupdate_restrict(self):
        return self.fk_onupdate + exclusions.fails_on(["mssql"])

    @property
    def fk_ondelete_noaction(self):
        return exclusions.only_on(
            ["postgresql", "mysql", "mariadb", "sqlite", "mssql"]
        )

    @property
    def fk_ondelete_is_reflected(self):
        def go(config):
            if exclusions.against(config, "mssql"):
                return not sqla_compat.sqla_14_26
            else:
                return False

        return exclusions.fails_if(go)

    @property
    def fk_onupdate_is_reflected(self):
        def go(config):
            if exclusions.against(config, "mssql"):
                return not sqla_compat.sqla_14_26
            else:
                return False

        return self.fk_onupdate + exclusions.fails_if(go)

    @property
    def fk_onupdate(self):
        return exclusions.only_on(
            ["postgresql", "mysql", "mariadb", "sqlite", "mssql"]
        )

    @property
    def reflects_unique_constraints_unambiguously(self):
        return exclusions.fails_on(["mysql", "mariadb", "oracle", "mssql"])

    @property
    def reports_unique_constraints_as_indexes(self):
        return exclusions.only_on(["mysql", "mariadb", "oracle"])

    @property
    def reports_unnamed_constraints(self):
        return exclusions.skip_if(["sqlite"])

    @property
    def reflects_indexes_w_sorting(self):
        # TODO: figure out what's happening on the SQLAlchemy side
        # when we reflect an index that has asc() / desc() on the column
        return exclusions.fails_on(["oracle"])

    @property
    def long_names(self):
        if sqla_compat.sqla_14:
            return exclusions.skip_if("oracle<18")
        else:
            return exclusions.skip_if("oracle")

    @property
    def reflects_pk_names(self):
        """Target driver reflects the name of primary key constraints."""

        return exclusions.fails_on_everything_except(
            "postgresql", "oracle", "mssql", "sybase", "sqlite"
        )

    @property
    def datetime_timezone(self):
        """target dialect supports timezone with datetime types."""

        return exclusions.only_on(["postgresql"])

    @property
    def postgresql(self):
        return exclusions.only_on(["postgresql"])

    @property
    def mysql(self):
        return exclusions.only_on(["mysql", "mariadb"])

    @property
    def oracle(self):
        return exclusions.only_on(["oracle"])

    @property
    def mssql(self):
        return exclusions.only_on(["mssql"])

    @property
    def covering_indexes(self):
        return exclusions.only_on(["postgresql >= 11", "mssql"])

    @property
    def postgresql_uuid_ossp(self):
        def check_uuid_ossp(config):
            if not exclusions.against(config, "postgresql"):
                return False
            try:
                config.db.execute("SELECT uuid_generate_v4()")
                return True
            except:
                return False

        return exclusions.only_if(check_uuid_ossp)

    def _has_pg_extension(self, name):
        def check(config):
            if not exclusions.against(config, "postgresql"):
                return False
            with config.db.connect() as conn:
                count = conn.scalar(
                    text(
                        "SELECT count(*) FROM pg_extension "
                        "WHERE extname='%s'" % name
                    )
                )
            return bool(count)

        return exclusions.only_if(check, "needs %s extension" % name)

    @property
    def hstore(self):
        return self._has_pg_extension("hstore")

    @property
    def btree_gist(self):
        return self._has_pg_extension("btree_gist")

    @property
    def autoincrement_on_composite_pk(self):
        return exclusions.skip_if(["sqlite"], "not supported by database")

    @property
    def integer_subtype_comparisons(self):
        """if a compare of Integer and BigInteger is supported yet."""
        return exclusions.skip_if(["oracle"], "not supported by alembic impl")

    @property
    def autocommit_isolation(self):
        """target database should support 'AUTOCOMMIT' isolation level"""

        return exclusions.only_on(["postgresql", "mysql", "mariadb"])

    @property
    def computed_columns(self):
        # TODO: in theory if these could come from SQLAlchemy dialects
        # that would be helpful
        return self.computed_columns_api + exclusions.skip_if(
            ["postgresql < 12", "sqlite < 3.31", "mysql < 5.7"]
        )

    @property
    def computed_reflects_as_server_default(self):
        # note that this rule will go away when SQLAlchemy correctly
        # supports reflection of the "computed" construct; the element
        # will consistently be present as both column.computed and
        # column.server_default for all supported backends.
        return (
            self.computed_columns
            + exclusions.only_if(
                ["postgresql", "oracle"],
                "backend reflects computed construct as a server default",
            )
            + exclusions.skip_if(self.computed_reflects_normally)
        )

    @property
    def computed_doesnt_reflect_as_server_default(self):
        # note that this rule will go away when SQLAlchemy correctly
        # supports reflection of the "computed" construct; the element
        # will consistently be present as both column.computed and
        # column.server_default for all supported backends.
        return (
            self.computed_columns
            + exclusions.skip_if(
                ["postgresql", "oracle"],
                "backend reflects computed construct as a server default",
            )
            + exclusions.skip_if(self.computed_reflects_normally)
        )

    @property
    def check_constraint_reflection(self):
        return exclusions.fails_on_everything_except(
            "postgresql",
            "sqlite",
            "oracle",
            self._mysql_and_check_constraints_exist,
        )

    def mysql_check_col_name_change(self, config):
        # MySQL has check constraints that enforce an reflect, however
        # they prevent a column's name from being changed due to a bug in
        # MariaDB 10.2 as well as MySQL 8.0.16
        if exclusions.against(config, ["mysql", "mariadb"]):
            if sqla_compat._is_mariadb(config.db.dialect):
                mnvi = sqla_compat._mariadb_normalized_version_info
                norm_version_info = mnvi(config.db.dialect)
                return norm_version_info >= (10, 2) and norm_version_info < (
                    10,
                    2,
                    22,
                )
            else:
                norm_version_info = config.db.dialect.server_version_info
                return norm_version_info >= (8, 0, 16)

        else:
            return True

    def _mysql_and_check_constraints_exist(self, config):
        # 1. we have mysql / mariadb and
        # 2. it enforces check constraints
        if exclusions.against(config, ["mysql", "mariadb"]):
            if sqla_compat._is_mariadb(config.db.dialect):
                mnvi = sqla_compat._mariadb_normalized_version_info
                norm_version_info = mnvi(config.db.dialect)
                return norm_version_info >= (10, 2)
            else:
                norm_version_info = config.db.dialect.server_version_info
                return norm_version_info >= (8, 0, 16)
        else:
            return False

    @property
    def json_type(self):
        return exclusions.only_on(
            [
                lambda config: exclusions.against(config, "mysql")
                and (
                    (
                        not config.db.dialect._is_mariadb
                        and exclusions.against(config, "mysql >= 5.7")
                    )
                    or (
                        config.db.dialect._mariadb_normalized_version_info
                        >= (10, 2, 7)
                    )
                ),
                "mariadb>=10.2.7",
                "postgresql >= 9.3",
                self._sqlite_json,
                self._mssql_json,
            ]
        )

    def _mssql_json(self, config):
        if not sqla_compat.sqla_14:
            return False
        else:
            return exclusions.against(config, "mssql")

    def _sqlite_json(self, config):
        if not sqla_compat.sqla_14:
            return False
        elif not exclusions.against(config, "sqlite >= 3.9"):
            return False
        else:
            with config.db.connect() as conn:
                try:
                    return (
                        conn.execute(
                            text(
                                """select json_extract('{"foo": "bar"}', """
                                """'$."foo"')"""
                            )
                        ).scalar()
                        == "bar"
                    )
                except sqla_exc.DBAPIError:
                    return False

    @property
    def identity_columns(self):
        # TODO: in theory if these could come from SQLAlchemy dialects
        # that would be helpful
        return self.identity_columns_api + exclusions.only_on(
            ["postgresql >= 10", "oracle >= 12", "mssql"]
        )

    @property
    def identity_columns_alter(self):
        # TODO: in theory if these could come from SQLAlchemy dialects
        # that would be helpful
        return self.identity_columns_api + exclusions.only_on(
            ["postgresql >= 10", "oracle >= 12"]
        )

    @property
    def supports_identity_on_null(self):
        return self.identity_columns + exclusions.only_on(["oracle"])

    @property
    def legacy_engine(self):
        return exclusions.only_if(
            lambda config: not getattr(config.db, "_is_future", False)
        )

    @property
    def stubs_test(self):
        def requirements():
            try:
                import black  # noqa
                import zimports  # noqa

                return False
            except Exception:
                return True

        imports = exclusions.skip_if(
            requirements, "black and zimports are required for this test"
        )
        version = exclusions.only_if(
            lambda _: compat.py39, "python 3.9 is required"
        )

        sqlalchemy = exclusions.only_if(
            lambda _: sqla_compat.sqla_2, "sqlalchemy 2 is required"
        )

        return imports + version + sqlalchemy
