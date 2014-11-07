from sqlalchemy import Table, MetaData, Index, select
from sqlalchemy import types as sqltypes
from sqlalchemy.util import OrderedDict


class BatchOperationsImpl(object):
    def __init__(self, operations, table_name, schema, recreate, copy_from):
        self.operations = operations
        self.table_name = table_name
        self.schema = schema
        if recreate not in ('auto', 'always', 'never'):
            raise ValueError(
                "recreate may be one of 'auto', 'always', or 'never'.")
        self.recreate = recreate
        self.copy_from = copy_from
        self.batch = []

    @property
    def dialect(self):
        return self.operations.impl.dialect

    @property
    def impl(self):
        return self.operations.impl

    def _should_recreate(self):
        if self.recreate == 'auto':
            return self.operations.impl.requires_recreate_in_batch(self)
        elif self.recreate == 'always':
            return True
        else:
            return False

    def flush(self):
        should_recreate = self._should_recreate()

        if not should_recreate:
            for opname, arg, kw in self.batch:
                fn = getattr(self.operations.impl, opname)
                fn(*arg, **kw)
        else:
            m1 = MetaData()
            existing_table = Table(
                self.table_name, m1, schema=self.schema,
                autoload=True, autoload_with=self.operations.get_bind())

            batch_impl = ApplyBatchImpl(existing_table)
            for opname, arg, kw in self.batch:
                fn = getattr(batch_impl, opname)
                fn(*arg, **kw)

            batch_impl._create(self.impl)


    def alter_column(self, *arg, **kw):
        self.batch.append(
            ("alter_column", arg, kw)
        )

    def add_column(self, *arg, **kw):
        self.batch.append(
            ("add_column", arg, kw)
        )

    def drop_column(self, *arg, **kw):
        self.batch.append(
            ("drop_column", arg, kw)
        )

    def add_constraint(self, const):
        self.batch.append(
            ("add_constraint", (const,), {})
        )

    def drop_constraint(self, const):
        self.batch.append(
            ("drop_constraint", (const, ), {})
        )

    def rename_table(self, *arg, **kw):
        self.batch.append(
            ("rename_table", arg, kw)
        )

    def create_table(self, table):
        raise NotImplementedError("Can't create table in batch mode")

    def drop_table(self, table):
        raise NotImplementedError("Can't drop table in batch mode")

    def create_index(self, index):
        raise NotImplementedError("Can't create index in batch mode")

    def drop_index(self, index):
        raise NotImplementedError("Can't drop index in batch mode")


class ApplyBatchImpl(object):
    def __init__(self, table):
        self.table = table  # this is a Table object
        self.column_transfers = dict(
            (c.name, {}) for c in self.table.c
        )
        self._grab_table_elements()

    def _grab_table_elements(self):
        schema = self.table.schema
        self.columns = OrderedDict()
        for c in self.table.c:
            c_copy = c.copy(schema=schema)
            c_copy.unique = c_copy.index = False
            self.columns[c.name] = c_copy
        self.named_constraints = {}
        self.unnamed_constraints = []
        self.indexes = {}
        for const in self.table.constraints:
            if const.name:
                self.named_constraints[const.name] = const
            else:
                self.unnamed_constraints.append(const)
        for idx in self.table.indexes:
            self.indexes[idx.name] = idx

    def _transfer_elements_to_new_table(self):
        m = MetaData()
        schema = self.table.schema
        new_table = Table(
            '_alembic_batch_temp', m, *self.columns.values(), schema=schema)

        for c in list(self.named_constraints.values()) + \
                self.unnamed_constraints:
            c_copy = c.copy(schema=schema, target_table=new_table)
            new_table.append_constraint(c_copy)

        for index in self.indexes.values():
            Index(index.name,
                  unique=index.unique,
                  *[new_table.c[col] for col in index.columns.keys()],
                  **index.kwargs)
        return new_table

    def _create(self, op_impl):
        new_table = self._transfer_elements_to_new_table()
        op_impl.create_table(new_table)

        op_impl.bind.execute(
            new_table.insert(inline=True).from_select(
                list(self.column_transfers.keys()),
                select([
                    self.table.c[key]
                    for key in self.column_transfers
                ])
            )
        )

        op_impl.drop_table(self.table)
        op_impl.rename_table(
            "_alembic_batch_temp",
            self.table.name,
            schema=self.table.schema
        )

    def alter_column(self, table_name, column_name,
                     nullable=None,
                     server_default=False,
                     new_column_name=None,
                     type_=None,
                     autoincrement=None,
                     **kw
                     ):
        existing = self.columns[column_name]
        existing_transfer = self.column_transfers[column_name]
        if new_column_name is not None and new_column_name != column_name:
            # note that we don't change '.key' - we keep referring
            # to the renamed column by its old key in _create().  neat!
            existing.name = new_column_name
            existing_transfer["name"] = new_column_name

        if type_ is not None:
            type_ = sqltypes.to_instance(type_)
            existing.type = type_
            existing_transfer["typecast"] = type_
        if nullable is not None:
            existing.nullable = nullable
        if server_default is not False:
            existing.server_default = server_default
        if autoincrement is not None:
            existing.autoincrement = bool(autoincrement)

    def add_column(self, table_name, column, **kw):
        self.columns[column.name] = column

    def drop_column(self, table_name, column, **kw):
        del self.columns[column.name]
        del self.column_transfers[column.name]

    def add_constraint(self, const):
        raise NotImplementedError("TODO")

    def drop_constraint(self, const):
        raise NotImplementedError("TODO")

    def rename_table(self, *arg, **kw):
        raise NotImplementedError("TODO")
