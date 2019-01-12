import re

from .impl import DefaultImpl
from .. import util
from sqlalchemy import Table, MetaData

class SQLiteImpl(DefaultImpl):
    __dialect__ = "sqlite"

    transactional_ddl = False
    """SQLite supports transactional DDL, but pysqlite does not:
    see: http://bugs.python.org/issue10740
    """

    def requires_recreate_in_batch(self, batch_op):
        """Return True if the given :class:`.BatchOperationsImpl`
        would need the table to be recreated and copied in order to
        proceed.

        Normally, only returns True on SQLite when operations other
        than add_column are present.

        """
        for op in batch_op.batch:
            if op[0] not in ("add_column", "create_index", "drop_index"):
                return True
        else:
            return False

    def add_constraint(self, const):
        # attempt to distinguish between an
        # auto-gen constraint and an explicit one
        if const._create_rule is None:
            raise NotImplementedError(
                "No support for ALTER of constraints in SQLite dialect"
            )
        elif const._create_rule(self):
            util.warn(
                "Skipping unsupported ALTER for "
                "creation of implicit constraint"
            )

    def drop_column(self, table_name, column, schema=None, **kw):
        util.warn("dropping columns in sqlite is experimental. "
                  "ensure constraints and foreign keys are still correct. only use it for dev")

        temp_table_name = self.get_random_table_name()
        self.set_foreignkeys('OFF')
        old_table=Table(table_name, MetaData(bind=self.connection.engine), autoload=True,autoload_with=self.connection.engine)
        new_column_list= [x.name for x in old_table.columns._all_columns if x.name != column.name]
        new_table=Table(table_name, MetaData(bind=self.connection.engine), include_columns=new_column_list, autoload=True,autoload_with=self.connection.engine)
        self.rename_table(table_name,temp_table_name, schema)
        new_table.create()
        self.move_data_by_column(new_table.name,temp_table_name, new_column_list)
        self.drop_table(Table(temp_table_name, MetaData(bind=self.connection.engine), autoload=True,autoload_with=self.connection.engine))
        self.set_foreignkeys('ON')

    def drop_constraint(self, const):
        import pdb; pdb.set_trace()       
        util.warn("dropping constraints in sqlite is experimental. "
                  "ensure constraints and foreign keys are still correct. only use it for dev")

        self.set_foreignkeys('OFF')

        temp_table_name = self.get_random_table_name()
        new_column_list= duplicate_columns(const.table)
        
        new_table=Table(const.parent, MetaData(bind=self.connection.engine), autoload=True,autoload_with=self.connection.engine)
        self.rename_table(const.parent.name,temp_table_name, const.parent.schema)
        new_table.create()
        self.move_data(new_table.name,temp_table_name)
        self.drop_table(Table(temp_table_name, MetaData(bind=self.connection.engine), autoload=True,autoload_with=self.connection.engine))
        self.set_foreignkeys('ON')

    def duplicate_columns(table):
        [x.name for x in old_table.columns._all_columns if x.name != column.name]
        old_table=Table(const.table.name, MetaData(bind=self.connection.engine), autoload=True,autoload_with=self.connection.engine)
        ncl=old_table.columns._all_columns
        col=ncl[-1]
        from sqlalchemy.sql.schema import Column
        col2=Column('Creator', INTEGER(),table=old_table)
        from sqlalchemy.types import TypeEngine
        from sqlalchemy.types import *
        col2=Column('Creator', INTEGER())
        ncl[-1]=col2
        meta=MetaData()
        new_table=Table(old_table.name,None,*ncl)
        new_table=Table(old_table.name,meta,*ncl)

    def move_data(self, new_table_name,old_table_name):
        self.execute("INSERT INTO %s SELECT * from %s;" % (new_table_name, old_table_name))

    def move_data_by_column(self, new_table_name,old_table_name, columns):
        self.execute("INSERT INTO %s SELECT %s from %s;" % (new_table_name, ','.join(columns), old_table_name))

    def set_foreignkeys(self, state):
        sql_foreignkeys="PRAGMA foreign_keys = %s;" % state
        sql_legacyalter='PRAGMA legacy_alter_table=%s;' % ( 'OFF' if state=='ON' else 'ON')
        self.connection.execute(sql_foreignkeys)
        self.connection.execute(sql_legacyalter)
        result=self.connection.execute("PRAGMA foreign_keys;")
        self.static_output("pragma is"+str(result.fetchone()[0]))
        
    def get_random_table_name(self, len=8):
        import random, string
        return 'temp_'+''.join(random.choices(string.ascii_lowercase + string.digits, k=len))

    def compare_server_default(
        self,
        inspector_column,
        metadata_column,
        rendered_metadata_default,
        rendered_inspector_default,
    ):

        if rendered_metadata_default is not None:
            rendered_metadata_default = re.sub(
                r"^\"'|\"'$", "", rendered_metadata_default
            )
        if rendered_inspector_default is not None:
            rendered_inspector_default = re.sub(
                r"^\"'|\"'$", "", rendered_inspector_default
            )

        return rendered_inspector_default != rendered_metadata_default

    def correct_for_autogen_constraints(
        self,
        conn_unique_constraints,
        conn_indexes,
        metadata_unique_constraints,
        metadata_indexes,
    ):

        if util.sqla_100:
            return

        # adjustments to accommodate for SQLite unnamed unique constraints
        # not being reported from the backend; this was updated in
        # SQLA 1.0.

        def uq_sig(uq):
            return tuple(sorted(uq.columns.keys()))

        conn_unique_sigs = set(uq_sig(uq) for uq in conn_unique_constraints)

        for idx in list(metadata_unique_constraints):
            # SQLite backend can't report on unnamed UNIQUE constraints,
            # so remove these, unless we see an exact signature match
            if idx.name is None and uq_sig(idx) not in conn_unique_sigs:
                metadata_unique_constraints.remove(idx)


# @compiles(AddColumn, 'sqlite')
# def visit_add_column(element, compiler, **kw):
#    return "%s %s" % (
#        alter_table(compiler, element.table_name, element.schema),
#        add_column(compiler, element.column, **kw)
#    )


# def add_column(compiler, column, **kw):
#    text = "ADD COLUMN %s" % compiler.get_column_specification(column, **kw)
# need to modify SQLAlchemy so that the CHECK associated with a Boolean
# or Enum gets placed as part of the column constraints, not the Table
# see ticket 98
#    for const in column.constraints:
#        text += compiler.process(AddConstraint(const))
#    return text
