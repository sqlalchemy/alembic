from .. import util


to_impl = util.Dispatcher()


class MigrateOperation(object):
    """base class for migration command and organization objects."""


class AddConstraintOp(MigrateOperation):
    pass


class DropConstraintOp(MigrateOperation):
    def __init__(self, name, table_name, type_=None, schema=None):
        self.name = name
        self.table_name = table_name
        self.type_ = type_
        self.schema = schema


class CreateUniqueConstraintOp(AddConstraintOp):
    def __init__(self, name, local_cols, **kw):
        self.name = name
        self.local_cols = local_cols
        self.kw = kw


class CreateCheckConstraintOp(AddConstraintOp):
    def __init__(
            self, name, source, condition, schema=None, **kw):
        self.name = name
        self.source = source
        self.condition = condition
        self.schema = schema
        self.kw = kw


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


class DropIndexOp(MigrateOperation):
    def __init__(self, name, table_name=None, schema=None):
        self.name = name
        self.table_name = table_name
        self.schema = schema


class CreateTableOp(MigrateOperation):
    def __init__(self, name, *columns, **kw):
        self.name = name
        self.columns = columns
        self.kw = kw


class DropTableOp(MigrateOperation):
    def __init__(self, name, schema=None, table_kw=None):
        self.name = name
        self.schema = schema
        self.table_kw = table_kw or {}


class AlterTableOp(MigrateOperation):

    def __init__(self, table_name, schema=None):
        self.table_name = table_name
        self.schema = schema


class RenameTableOp(AlterTableOp):

    def __init__(self, old_table_name, new_table_name, schema=None):
        super(RenameTableOp, self).__init__(old_table_name, schema=schema)
        self.new_table_name = new_table_name


class AlterColumnOp(AlterTableOp):

    def __init__(
            self, table_name, column_name, schema=None,
            existing_type=None,
            existing_server_default=False,
            existing_nullable=None
    ):
        super(AlterColumnOp, self).__init__(table_name, schema=schema)
        self.column_name = column_name
        self.existing_type = existing_type
        self.existing_server_default = existing_server_default
        self.existing_nullable = existing_nullable

    modify_nullable = None
    modify_server_default = False
    modify_name = None
    modify_type = None
    kw = None


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


class MigrationScript(MigrateOperation):
    """represents a migration script.

    E.g. when autogenerate encounters this object, this corresponds to the
    production of an actual script file.

    A normal :class:`.MigrationScript` object would contain a single
    :class:`.UpgradeOps` and a single :class:`.DowngradeOps` directive.

    """

    def __init__(
            self, rev_id, message, imports, upgrade_ops, downgrade_ops,
            head, splice, branch_label, version_path):
        self.rev_id = rev_id
        self.message = message
        self.imports = imports
        self.head = head
        self.splice = splice
        self.branch_label = branch_label
        self.version_path = version_path
        self.upgrade_ops = upgrade_ops
        self.downgrade_ops = downgrade_ops

