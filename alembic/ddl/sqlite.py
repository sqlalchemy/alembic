from .. import util
from .impl import DefaultImpl

#from sqlalchemy.ext.compiler import compiles
#from .base import AddColumn, alter_table
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

    def correct_for_autogen_constraints(self, conn_unique_constraints, conn_indexes,
                                        metadata_unique_constraints,
                                        metadata_indexes):

        def uq_sig(uq):
            return tuple(sorted(uq.columns.keys()))

        conn_unique_sigs = set(
                                uq_sig(uq)
                                for uq in conn_unique_constraints
                            )

        for idx in list(metadata_unique_constraints):
            # SQLite backend can't report on unnamed UNIQUE constraints,
            # so remove these, unless we see an exact signature match
            if idx.name is None and uq_sig(idx) not in conn_unique_sigs:
                metadata_unique_constraints.remove(idx)

        for idx in list(conn_unique_constraints):
            # just in case we fix the backend such that it does report
            # on them, blow them out of the reflected collection too otherwise
            # they will come up as removed.  if the backend supports this now,
            # add a version check here for the dialect.
            if idx.name is None:
                conn_uniques.remove(idx)

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
