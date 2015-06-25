import itertools
from ..operations import ops


def _to_migration_script(autogen_context, migration_script, diffs):
    _to_upgrade_op(
        autogen_context,
        diffs,
        migration_script.upgrade_ops,
    )

    _to_downgrade_op(
        autogen_context,
        diffs,
        migration_script.downgrade_ops,
    )


def _to_upgrade_op(autogen_context, diffs, upgrade_ops):
    return _to_updown_op(autogen_context, diffs, upgrade_ops, "upgrade")


def _to_downgrade_op(autogen_context, diffs, downgrade_ops):
    return _to_updown_op(autogen_context, diffs, downgrade_ops, "downgrade")


def _to_updown_op(autogen_context, diffs, op_container, type_):
    if not diffs:
        return

    if type_ == 'downgrade':
        diffs = reversed(diffs)

    dest = [op_container.ops]

    for (schema, table), subdiffs in _group_diffs_by_table(diffs):
        if table is not None:
            table_ops = []
            op = ops.ModifyTableOps(table.name, table_ops, schema=table.schema)
            dest[-1].append(op)
            dest.append(ops)
        for diff in subdiffs:
            _produce_command(autogen_context, diff, dest[-1], type_)
        dest.pop(-1)


def _produce_command(autogen_context, diff, ops, updown):
    if isinstance(diff, tuple):
        _produce_adddrop_command(updown, diff, autogen_context)
    else:
        _produce_modify_command(updown, diff, autogen_context)


def _produce_adddrop_command(updown, diff, autogen_context):
    cmd_type = diff[0]
    adddrop, cmd_type = cmd_type.split("_")

    cmd_args = diff[1:] + (autogen_context,)

    _commands = {
        "table": (ops.DropTableOp.from_table, ops.CreateTableOp.from_table),
        "column": (
            ops.DropColumnOp.from_column_and_tablename,
            ops.AddColumnOp.from_column_and_tablename),
        "index": (ops.DropIndexOp.from_index, ops.CreateIndexOp.from_index),
        "constraint": (
            ops.DropConstraintOp.from_constraint,
            ops.AddConstraintOp.from_constraint),
        "fk": (
            ops.DropConstraintOp.from_constraint,
            ops.CreateForeignKeyOp.from_constraint)
    }

    cmd_callables = _commands[cmd_type]

    if (
        updown == "upgrade" and adddrop == "add"
    ) or (
        updown == "downgrade" and adddrop == "remove"
    ):
        return cmd_callables[1](*cmd_args)
    else:
        return cmd_callables[0](*cmd_args)


def _produce_modify_command(updown, diffs, autogen_context):
    sname, tname, cname = diffs[0][1:4]
    kw = {}

    _arg_struct = {
        "modify_type": ("existing_type", "modify_type"),
        "modify_nullable": ("existing_nullable", "modify_nullable"),
        "modify_default": ("existing_server_default", "modify_server_default"),
    }
    for diff in diffs:
        diff_kw = diff[4]
        for arg in ("existing_type",
                    "existing_nullable",
                    "existing_server_default"):
            if arg in diff_kw:
                kw.setdefault(arg, diff_kw[arg])
        old_kw, new_kw = _arg_struct[diff[0]]
        if updown == "upgrade":
            kw[new_kw] = diff[-1]
            kw[old_kw] = diff[-2]
        else:
            kw[new_kw] = diff[-2]
            kw[old_kw] = diff[-1]

    if "nullable" in kw:
        kw.pop("existing_nullable", None)
    if "server_default" in kw:
        kw.pop("existing_server_default", None)

    return ops.AlterColumnOp(
        tname, cname, schema=sname,
        **kw
    )


def _group_diffs_by_table(diffs):
    _adddrop = {
        "table": lambda diff: (None, None),
        "column": lambda diff: (diff[0], diff[1]),
        "index": lambda diff: (diff[0].table.schema, diff[0].table.name),
        "constraint": lambda diff: (diff[0].table.schema, diff[0].table.name),
        "fk": lambda diff: (diff[0].parent.schema, diff[0].parent.name)
    }

    def _derive_table(diff):
        if isinstance(diff, tuple):
            cmd_type = diff[0]
            adddrop, cmd_type = cmd_type.split("_")
            return _adddrop[cmd_type](diff[1:])
        else:
            sname, tname = diff[0][1:3]
            return sname, tname

    return itertools.groupby(diffs, _derive_table)

