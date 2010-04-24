from sqlalchemy import util

NO_VALUE = util.symbol("NO_VALUE")

def alter_column(table_name, column_name, 
                    nullable=NO_VALUE,
                    server_default=NO_VALUE,
                    name=NO_VALUE,
                    type=NO_VALUE
):
    """Issue ALTER COLUMN using the current change context."""
    
    # TODO: dispatch to ddl.op