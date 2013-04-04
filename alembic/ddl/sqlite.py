from alembic.ddl.impl import DefaultImpl
from alembic import util

#from sqlalchemy.ext.compiler import compiles
#from alembic.ddl.base import AddColumn, alter_table
#from sqlalchemy.schema import AddConstraint

class SQLiteImpl(DefaultImpl):
    __dialect__ = 'sqlite'

    transactional_ddl = False
    """SQLite supports transactional DDL, but pysqlite does not:
    see: http://bugs.python.org/issue10740
    """

    def add_constraint(self, const):
        # attempt to distinguish between an
        # auto-gen constraint and an explicit one
        if const._create_rule is None:
            raise NotImplementedError(
                    "No support for ALTER of constraints in SQLite dialect")
        elif const._create_rule(self):
            util.warn("Skipping unsupported ALTER for "
                        "creation of implicit constraint")


    def drop_constraint(self, const):
        if const._create_rule is None:
            raise NotImplementedError(
                    "No support for ALTER of constraints in SQLite dialect")


#@compiles(AddColumn, 'sqlite')
#def visit_add_column(element, compiler, **kw):
#    return "%s %s" % (
#        alter_table(compiler, element.table_name, element.schema),
#        add_column(compiler, element.column, **kw)
#    )


#def add_column(compiler, column, **kw):
#    text = "ADD COLUMN %s" % compiler.get_column_specification(column, **kw)
#    # need to modify SQLAlchemy so that the CHECK associated with a Boolean
#    # or Enum gets placed as part of the column constraints, not the Table
#    # see ticket 98
#    for const in column.constraints:
#        text += compiler.process(AddConstraint(const))
#    return text
