from sqlalchemy import schema as sa_schema, types as sqltypes, sql
import logging
from .. import compat
import re
from ..compat import string_types

log = logging.getLogger(__name__)

def _render_potential_expr(value, autogen_context):
    if isinstance(value, sql.ClauseElement):
        if compat.sqla_08:
            compile_kw = dict(compile_kwargs={'literal_binds': True})
        else:
            compile_kw = {}

        return "%(prefix)stext(%(sql)r)" % {
            "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
            "sql": str(
                    value.compile(dialect=autogen_context['dialect'],
                    **compile_kw)
                )
        }

    else:
        return repr(value)

def _add_table(table, autogen_context):
    text = "%(prefix)screate_table(%(tablename)r,\n%(args)s" % {
        'tablename': table.name,
        'prefix': _alembic_autogenerate_prefix(autogen_context),
        'args': ',\n'.join(
            [col for col in
                [_render_column(col, autogen_context) for col in table.c]
            if col] +
            sorted([rcons for rcons in
                [_render_constraint(cons, autogen_context) for cons in
                    table.constraints]
                if rcons is not None
            ])
        )
    }
    if table.schema:
        text += ",\nschema=%r" % table.schema
    for k in sorted(table.kwargs):
        text += ",\n%s=%r" % (k.replace(" ", "_"), table.kwargs[k])
    text += "\n)"
    return text

def _drop_table(table, autogen_context):
    text = "%(prefix)sdrop_table(%(tname)r" % {
            "prefix": _alembic_autogenerate_prefix(autogen_context),
            "tname": table.name
        }
    if table.schema:
        text += ", schema=%r" % table.schema
    text += ")"
    return text

def _add_index(index, autogen_context):
    """
    Generate Alembic operations for the CREATE INDEX of an
    :class:`~sqlalchemy.schema.Index` instance.
    """
    from .compare import _get_index_column_names

    text = "%(prefix)screate_index('%(name)s', '%(table)s', %(columns)s, "\
                    "unique=%(unique)r%(schema)s%(kwargs)s)" % {
        'prefix': _alembic_autogenerate_prefix(autogen_context),
        'name': index.name,
        'table': index.table,
        'columns': _get_index_column_names(index),
        'unique': index.unique or False,
        'schema': (", schema='%s'" % index.table.schema) if index.table.schema else '',
        'kwargs': (', '+', '.join(
            ["%s=%s" % (key, _render_potential_expr(val, autogen_context))
                for key, val in index.kwargs.items()]))\
            if len(index.kwargs) else ''
    }
    return text

def _drop_index(index, autogen_context):
    """
    Generate Alembic operations for the DROP INDEX of an
    :class:`~sqlalchemy.schema.Index` instance.
    """
    text = "%sdrop_index('%s', '%s')" % (
                    _alembic_autogenerate_prefix(autogen_context),
                    index.name,
                    index.table)
    return text


def _render_unique_constraint(constraint, autogen_context):
    rendered = _user_defined_render("unique", constraint, autogen_context)
    if rendered is not False:
        return rendered

    return _uq_constraint(constraint, autogen_context, False)


def _add_unique_constraint(constraint, autogen_context):
    """
    Generate Alembic operations for the ALTER TABLE .. ADD CONSTRAINT ...
    UNIQUE of a :class:`~sqlalchemy.schema.UniqueConstraint` instance.
    """
    return _uq_constraint(constraint, autogen_context, True)

def _uq_constraint(constraint, autogen_context, alter):
    opts = []
    if constraint.deferrable:
        opts.append(("deferrable", str(constraint.deferrable)))
    if constraint.initially:
        opts.append(("initially", str(constraint.initially)))
    if alter and constraint.table.schema:
        opts.append(("schema", str(constraint.table.schema)))
    if not alter and constraint.name:
        opts.append(("name", constraint.name))

    if alter:
        args = [repr(constraint.name), repr(constraint.table.name)]
        args.append(repr([col.name for col in constraint.columns]))
        args.extend(["%s=%r" % (k, v) for k, v in opts])
        return "%(prefix)screate_unique_constraint(%(args)s)" % {
                'prefix': _alembic_autogenerate_prefix(autogen_context),
                'args': ", ".join(args)
            }
    else:
        args = [repr(col.name) for col in constraint.columns]
        args.extend(["%s=%r" % (k, v) for k, v in opts])
        return "%(prefix)sUniqueConstraint(%(args)s)" % {
            "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
            "args": ", ".join(args)
        }


def _add_fk_constraint(constraint, autogen_context):
    raise NotImplementedError()

def _add_pk_constraint(constraint, autogen_context):
    raise NotImplementedError()

def _add_check_constraint(constraint, autogen_context):
    raise NotImplementedError()

def _add_constraint(constraint, autogen_context):
    """
    Dispatcher for the different types of constraints.
    """
    funcs = {
        "unique_constraint": _add_unique_constraint,
        "foreign_key_constraint": _add_fk_constraint,
        "primary_key_constraint": _add_pk_constraint,
        "check_constraint": _add_check_constraint,
        "column_check_constraint": _add_check_constraint,
    }
    return funcs[constraint.__visit_name__](constraint, autogen_context)

def _drop_constraint(constraint, autogen_context):
    """
    Generate Alembic operations for the ALTER TABLE ... DROP CONSTRAINT
    of a  :class:`~sqlalchemy.schema.UniqueConstraint` instance.
    """
    text = "%(prefix)sdrop_constraint(%(name)r, '%(table)s')" % {
            'prefix': _alembic_autogenerate_prefix(autogen_context),
            'name': constraint.name,
            'table': constraint.table,
    }
    return text

def _add_column(schema, tname, column, autogen_context):
    text = "%(prefix)sadd_column(%(tname)r, %(column)s" % {
            "prefix": _alembic_autogenerate_prefix(autogen_context),
            "tname": tname,
            "column": _render_column(column, autogen_context)
            }
    if schema:
        text += ", schema=%r" % schema
    text += ")"
    return text

def _drop_column(schema, tname, column, autogen_context):
    text = "%(prefix)sdrop_column(%(tname)r, %(cname)r" % {
            "prefix": _alembic_autogenerate_prefix(autogen_context),
            "tname": tname,
            "cname": column.name
            }
    if schema:
        text += ", schema=%r" % schema
    text += ")"
    return text

def _modify_col(tname, cname,
                autogen_context,
                server_default=False,
                type_=None,
                nullable=None,
                existing_type=None,
                existing_nullable=None,
                existing_server_default=False,
                schema=None):
    sqla_prefix = _sqlalchemy_autogenerate_prefix(autogen_context)
    indent = " " * 11
    text = "%(prefix)salter_column(%(tname)r, %(cname)r" % {
                            'prefix': _alembic_autogenerate_prefix(
                                                autogen_context),
                            'tname': tname,
                            'cname': cname}
    text += ",\n%sexisting_type=%s" % (indent,
                    _repr_type(sqla_prefix, existing_type, autogen_context))
    if server_default is not False:
        rendered = _render_server_default(
                                server_default, autogen_context)
        text += ",\n%sserver_default=%s" % (indent, rendered)

    if type_ is not None:
        text += ",\n%stype_=%s" % (indent,
                        _repr_type(sqla_prefix, type_, autogen_context))
    if nullable is not None:
        text += ",\n%snullable=%r" % (
                        indent, nullable,)
    if existing_nullable is not None:
        text += ",\n%sexisting_nullable=%r" % (
                        indent, existing_nullable)
    if existing_server_default:
        rendered = _render_server_default(
                            existing_server_default,
                            autogen_context)
        text += ",\n%sexisting_server_default=%s" % (
                        indent, rendered)
    if schema:
        text += ",\n%sschema=%r" % (indent, schema)
    text += ")"
    return text

def _sqlalchemy_autogenerate_prefix(autogen_context):
    return autogen_context['opts']['sqlalchemy_module_prefix'] or ''

def _alembic_autogenerate_prefix(autogen_context):
    return autogen_context['opts']['alembic_module_prefix'] or ''

def _user_defined_render(type_, object_, autogen_context):
    if 'opts' in autogen_context and \
            'render_item' in autogen_context['opts']:
        render = autogen_context['opts']['render_item']
        if render:
            rendered = render(type_, object_, autogen_context)
            if rendered is not False:
                return rendered
    return False

def _render_column(column, autogen_context):
    rendered = _user_defined_render("column", column, autogen_context)
    if rendered is not False:
        return rendered

    opts = []
    if column.server_default:
        rendered = _render_server_default(
                            column.server_default, autogen_context
                    )
        if rendered:
            opts.append(("server_default", rendered))

    if not column.autoincrement:
        opts.append(("autoincrement", column.autoincrement))

    if column.nullable is not None:
        opts.append(("nullable", column.nullable))

    # TODO: for non-ascii colname, assign a "key"
    return "%(prefix)sColumn(%(name)r, %(type)s, %(kw)s)" % {
        'prefix': _sqlalchemy_autogenerate_prefix(autogen_context),
        'name': column.name,
        'type': _repr_type(_sqlalchemy_autogenerate_prefix(autogen_context),
                                column.type, autogen_context),
        'kw': ", ".join(["%s=%s" % (kwname, val) for kwname, val in opts])
    }

def _render_server_default(default, autogen_context):
    rendered = _user_defined_render("server_default", default, autogen_context)
    if rendered is not False:
        return rendered

    if isinstance(default, sa_schema.DefaultClause):
        if isinstance(default.arg, string_types):
            default = default.arg
        else:
            default = str(default.arg.compile(
                            dialect=autogen_context['dialect']))
    if isinstance(default, string_types):
        # TODO: this is just a hack to get
        # tests to pass until we figure out
        # WTF sqlite is doing
        default = re.sub(r"^'|'$", "", default)
        return repr(default)
    else:
        return None

def _repr_type(prefix, type_, autogen_context):
    rendered = _user_defined_render("type", type_, autogen_context)
    if rendered is not False:
        return rendered

    mod = type(type_).__module__
    imports = autogen_context.get('imports', None)
    if mod.startswith("sqlalchemy.dialects"):
        dname = re.match(r"sqlalchemy\.dialects\.(\w+)", mod).group(1)
        if imports is not None:
            imports.add("from sqlalchemy.dialects import %s" % dname)
        return "%s.%r" % (dname, type_)
    else:
        return "%s%r" % (prefix, type_)

def _render_constraint(constraint, autogen_context):
    renderer = _constraint_renderers.get(type(constraint), None)
    if renderer:
        return renderer(constraint, autogen_context)
    else:
        return None

def _render_primary_key(constraint, autogen_context):
    rendered = _user_defined_render("primary_key", constraint, autogen_context)
    if rendered is not False:
        return rendered

    if not constraint.columns:
        return None

    opts = []
    if constraint.name:
        opts.append(("name", repr(constraint.name)))
    return "%(prefix)sPrimaryKeyConstraint(%(args)s)" % {
        "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
        "args": ", ".join(
            [repr(c.key) for c in constraint.columns] +
            ["%s=%s" % (kwname, val) for kwname, val in opts]
        ),
    }

def _fk_colspec(fk, metadata_schema):
    """Implement a 'safe' version of ForeignKey._get_colspec() that
    never tries to resolve the remote table.

    """
    if metadata_schema is None:
        return fk._get_colspec()
    else:
        # need to render schema breaking up tokens by hand, since the
        # ForeignKeyConstraint here may not actually have a remote
        # Table present
        tokens = fk._colspec.split(".")
        # no schema in the colspec, render it
        if len(tokens) == 2:
            return "%s.%s" % (metadata_schema, fk._colspec)
        else:
            return fk._colspec

def _render_foreign_key(constraint, autogen_context):
    rendered = _user_defined_render("foreign_key", constraint, autogen_context)
    if rendered is not False:
        return rendered

    opts = []
    if constraint.name:
        opts.append(("name", repr(constraint.name)))
    if constraint.onupdate:
        opts.append(("onupdate", repr(constraint.onupdate)))
    if constraint.ondelete:
        opts.append(("ondelete", repr(constraint.ondelete)))
    if constraint.initially:
        opts.append(("initially", repr(constraint.initially)))
    if constraint.deferrable:
        opts.append(("deferrable", repr(constraint.deferrable)))
    if constraint.use_alter:
        opts.append(("use_alter", repr(constraint.use_alter)))

    apply_metadata_schema = constraint.parent.metadata.schema
    return "%(prefix)sForeignKeyConstraint([%(cols)s], "\
            "[%(refcols)s], %(args)s)" % {
        "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
        "cols": ", ".join("'%s'" % f.parent.key for f in constraint.elements),
        "refcols": ", ".join(repr(_fk_colspec(f, apply_metadata_schema))
                            for f in constraint.elements),
        "args": ", ".join(
            ["%s=%s" % (kwname, val) for kwname, val in opts]
        ),
    }

def _render_check_constraint(constraint, autogen_context):
    rendered = _user_defined_render("check", constraint, autogen_context)
    if rendered is not False:
        return rendered

    # detect the constraint being part of
    # a parent type which is probably in the Table already.
    # ideally SQLAlchemy would give us more of a first class
    # way to detect this.
    if constraint._create_rule and \
        hasattr(constraint._create_rule, 'target') and \
        isinstance(constraint._create_rule.target,
                sqltypes.TypeEngine):
        return None
    opts = []
    if constraint.name:
        opts.append(("name", repr(constraint.name)))
    return "%(prefix)sCheckConstraint(%(sqltext)r%(opts)s)" % {
            "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
            "opts": ", " + (", ".join("%s=%s" % (k, v)
                            for k, v in opts)) if opts else "",
            "sqltext": str(
                constraint.sqltext.compile(
                    dialect=autogen_context['dialect']
                )
            )
        }

_constraint_renderers = {
    sa_schema.PrimaryKeyConstraint: _render_primary_key,
    sa_schema.ForeignKeyConstraint: _render_foreign_key,
    sa_schema.UniqueConstraint: _render_unique_constraint,
    sa_schema.CheckConstraint: _render_check_constraint
}
