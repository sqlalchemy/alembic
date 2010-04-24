def alter_column(table_name, column_name, 
                    nullable=NO_VALUE,
                    server_default=NO_VALUE,
                    name=NO_VALUE,
                    type=NO_VALUE
):
    
    if nullable is not NO_VALUE:
        ColumnNullable(table_name, column_name, nullable)
    if server_default is not NO_VALUE:
        ColumnDefault(table_name, column_name, server_default)
    
    # ... etc