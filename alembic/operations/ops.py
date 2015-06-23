
class MigrateOperation(object):
    """base class for migration command and organization objects."""

    def dispatch_for(self, handler):
        raise NotImplementedError()


class AddConstraintOp(MigrateOperation):
    pass


class DropConstraintOp(MigrateOperation):
    def __init__(self, name, type_=None):
        self.name = name
        self.type_ = type_

    def dispatch_for(self, handler):
        return handler.drop_constraint


class CreateUniqueConstraintOp(AddConstraintOp):
    def __init__(self, name, local_cols, **kw):
        self.name = name
        self.local_cols = local_cols
        self.kw = kw

    def dispatch_for(self, handler):
        return handler.create_unique_constraint


class CreateCheckConstraintOp(AddConstraintOp):
    def __init__(
            self, name, source, condition, schema=None, **kw):
        self.name = name
        self.source = source
        self.condition = condition
        self.schema = schema
        self.kw = kw

    def dispatch_for(self, handler):
        return handler.create_check_constraint


class CreateIndexOp(MigrateOperation):
    def __init__(
            self, name, table_name, columns, schema=None,
            unique=False, quote=None, **kw):
        self.name = name
        self.table_name = table_name
        self.columns = columns
        self.schema = schema
        self.unique = unique
        self.quote = quote
        self.kw = kw

    def dispatch_for(self, handler):
        return handler.create_index


class DropIndexOp(MigrateOperation):
    def __init__(self, name, table_name=None, schema=None):
        self.name = name
        self.table_name = table_name
        self.schema = schema

    def dispatch_for(self, handler):
        return handler.drop_index


class CreateTableOp(MigrateOperation):
    def __init__(self, name, *columns, **kw):
        self.name = name
        self.columns = columns
        self.kw = kw

    def dispatch_for(self, handler):
        return handler.create_table


class DropTableOp(MigrateOperation):
    def __init__(self, name, **kw):
        self.name = name
        self.kw = kw

    def dispatch_for(self, handler):
        return handler.drop_table


class AlterTableOp(MigrateOperation):

    def __init__(self, table_name, schema=None):
        self.table_name = table_name
        self.schema = schema

    def dispatch_for(self, handler):
        return handler.alter_table


class RenameTableOp(AlterTableOp):

    def __init__(self, old_table_name, new_table_name, schema=None):
        super(RenameTableOp, self).__init__(old_table_name, schema=schema)
        self.new_table_name = new_table_name

    def dispatch_for(self, handler):
        return handler.rename_table


class AlterColumnOp(AlterTableOp):

    def __init__(self, table_name, column_name, schema=None):
        super(AlterColumnOp, self).__init__(table_name, schema=schema)
        self.column_name = column_name

    modify_nullable = None
    modify_server_default = False
    modify_name = None
    modify_type = None

    def dispatch_for(self, handler):
        return handler.alter_column

    @classmethod
    def from_alter_column(
        cls, table_name, column_name,
        nullable=None,
        server_default=False,
        name=None,
        type_=None,
        schema=None,
        existing_type=None,
        existing_server_default=None,
            existing_nullable=None):
        """Generate an AlterColumn object from a set of 'alter_column'
        arguments.

        The 'alter_column' arguments are common throughout Alembic, both
        because this is the legacy API for altering columns as well as that
        it remains the primary public API from the Operations object.
        Internally, we seek to be able to convert between these arguments
        and distinct AlterColumnElement operations grouped together.

        """

        alt = AlterColumnOp(
            table_name, column_name, schema=schema,
            existing_type=existing_type,
            existing_server_default=existing_server_default,
            existing_nullable=existing_nullable
        )

        if name is not None:
            alt.modify_name = name
        if type_ is not None:
            alt.modify_type = type_,
        if server_default is not False:
            alt.modify_server_default = server_default
        if nullable is not None:
            alt.modify_nullable = nullable

        return alt

    @property
    def has_nullable(self):
        return self.modify_nullable is not None

    @property
    def has_type(self):
        return self.modify_type is not None

    @property
    def has_server_default(self):
        return self.modify_server_default is not False

    @property
    def has_name(self):
        return self.modify_name is not None


class AddColumnOp(AlterTableOp):

    def __init__(self, name, column, schema=None):
        super(AddColumnOp, self).__init__(name, schema=schema)
        self.column = column


class DropColumnOp(AlterTableOp):

    def __init__(self, name, column, schema=None):
        super(DropColumnOp, self).__init__(name, schema=schema)
        self.column = column


class BulkInsertOp(MigrateOperation):
    def __init__(self, table, rows, multiinsert=True):
        self.table = table
        self.rows = rows
        self.multiinsert = multiinsert

    def dispatch_for(self, handler):
        return handler.bulk_insert


class OpContainer(MigrateOperation):
    def __init__(self, ops):
        self.ops = ops


class ModifyTableOps(OpContainer):
    """Contains a sequence of operations that all apply to a single Table."""

    def __init__(self, table_name, ops, schema=None):
        super(ModifyTableOps, self).__init__(ops)
        self.table_name = table_name
        self.schema = schema


class UpgradeOps(OpContainer):
    """contains a sequence of operations that would apply to the
    'upgrade' stream of a script."""


class DowngradeOps(OpContainer):
    """contains a sequence of operations that would apply to the
    'downgrade' stream of a script."""


class MigrationScript(OpContainer):
    """represents a migration script.

    E.g. when autogenerate encounters this object, this corresponds to the
    production of an actual script file.

    A normal :class:`.MigrationScript` object would contain a single
    :class:`.UpgradeOps` and a single :class:`.DowngradeOps` directive.

    """


class MigrationDispatch(object):
    def handle(self, operation, **kw):
        fn = operation.dispatch_for(self)
        return fn(operation, **kw)

