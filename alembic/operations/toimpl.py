from .ops import MigrationDispatch

class ToImpl(MigrationDispatch):
    """translates from ops objects into commands sent to DefaultImpl."""

    def alter_column(self, operation):
        compiler = self.impl.dialect.statement_compiler(
            self.impl.dialect,
            None
        )

        def _count_constraint(constraint):
            return not isinstance(
                constraint,
                sa_schema.PrimaryKeyConstraint) and \
                (not constraint._create_rule or
                    constraint._create_rule(compiler))

        if existing_type and type_:
            t = self.schema_obj.table(
                table_name,
                sa_schema.Column(column_name, existing_type),
                schema=schema
            )
            for constraint in t.constraints:
                if _count_constraint(constraint):
                    self.impl.drop_constraint(constraint)

        self.impl.alter_column(table_name, column_name,
                               nullable=nullable,
                               server_default=server_default,
                               name=new_column_name,
                               type_=type_,
                               schema=schema,
                               autoincrement=autoincrement,
                               existing_type=existing_type,
                               existing_server_default=existing_server_default,
                               existing_nullable=existing_nullable,
                               existing_autoincrement=existing_autoincrement
                               )

        if type_:
            t = self.schema_obj.table(
                table_name,
                self.schema_obj.column(column_name, type_),
                schema=schema
            )
            for constraint in t.constraints:
                if _count_constraint(constraint):
                    self.impl.add_constraint(constraint)
