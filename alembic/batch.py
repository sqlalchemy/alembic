class BatchOperationsImpl(object):
    def __init__(self, operations, table_name, recreate):
        self.operations = operations
        self.table_name = table_name
        self.recreate = recreate
        self.batch = []

    def flush(self):
        should_recreate = self.recreate is True or \
            self.operations.impl.__dialect__ in set(self.recreate)

        if not should_recreate:
            for opname, arg, kw in self.batch:
                fn = getattr(self.operations.impl, opname)
                fn(*arg, **kw)
        else:
            # pseudocode
            existing_table = _reflect_table(self.operations.impl, table_name)
            impl = ApplyBatchImpl(existing_table)
            for opname, arg, kw in self.batch:
                fn = getattr(impl, opname)
                fn(*arg, **kw)

            _create_new_table(use_a_temp_name)
            _copy_data_somehow(
                impl.use_column_transfer_data, use_insert_from_select_aswell)
            _drop_old_table(this_parts_easy)
            _rename_table_to_old_name(ditto)

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

    def alter_column(self, table_name, column_name,
                     nullable=None,
                     server_default=False,
                     name=None,
                     type_=None,
                     autoincrement=None,
                     **kw
                     ):
        existing = self.table.c[column_name]
        existing_transfer = self.column_transfers[column_name]
        if name != column_name:
            # something like this
            self.table.c.remove_column(existing)
            existing.table = None
            existing.name = name
            existing._set_parent(self.table)
            existing_transfer["name"] = name

        if type_ is not None:
            existing.type = type_
            existing_transfer["typecast"] = type_
        if nullable is not None:
            existing.nullable = nullable
        if server_default is not False:
            existing.server_default = server_default
        if autoincrement is not None:
            existing.autoincrement = bool(autoincrement)

    def add_column(self, table_name, column, **kw):
        column.table = None
        column._set_parent(self.table)

    def drop_column(self, table_name, column, **kw):
        col = self.table.c[column.name]
        col.table = None
        self.table.c.remove_column(col)
        del self.column_transfers[column.name]

    def add_constraint(self, const):
        raise NotImplementedError("TODO")

    def drop_constraint(self, const):
        raise NotImplementedError("TODO")

    def rename_table(self, *arg, **kw):
        raise NotImplementedError("TODO")
