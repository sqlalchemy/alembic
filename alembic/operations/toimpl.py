from . import ops
from sqlalchemy import schema as sa_schema


@ops.to_impl.dispatch_for(ops.AlterColumnOp)
def alter_column(operations, operation):

    compiler = operations.impl.dialect.statement_compiler(
        operations.impl.dialect,
        None
    )

    existing_type = operation.existing_type
    existing_nullable = operation.existing_nullable
    existing_server_default = operation.existing_server_default
    type_ = operation.modify_type
    column_name = operation.column_name
    table_name = operation.table_name
    schema = operation.schema
    server_default = operation.modify_server_default
    new_column_name = operation.modify_name
    nullable = operation.modify_nullable

    def _count_constraint(constraint):
        return not isinstance(
            constraint,
            sa_schema.PrimaryKeyConstraint) and \
            (not constraint._create_rule or
                constraint._create_rule(compiler))

    if existing_type and type_:
        t = operations.schema_obj.table(
            table_name,
            sa_schema.Column(column_name, existing_type),
            schema=schema
        )
        for constraint in t.constraints:
            if _count_constraint(constraint):
                operations.impl.drop_constraint(constraint)

    operations.impl.alter_column(
        table_name, column_name,
        nullable=nullable,
        server_default=server_default,
        name=new_column_name,
        type_=type_,
        schema=schema,
        existing_type=existing_type,
        existing_server_default=existing_server_default,
        existing_nullable=existing_nullable,
        **operation.kw
    )

    if type_:
        t = operations.schema_obj.table(
            table_name,
            operations.schema_obj.column(column_name, type_),
            schema=schema
        )
        for constraint in t.constraints:
            if _count_constraint(constraint):
                operations.impl.add_constraint(constraint)


@ops.to_impl.dispatch_for(ops.DropTableOp)
def drop_table(operations, operation):
    operations.impl.drop_table(
        operations.schema_obj.table(
            operation.name,
            schema=operation.schema,
            **operation.table_kw)
    )
