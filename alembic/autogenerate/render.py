from sqlalchemy import schema as sa_schema, types as sqltypes, sql
import logging
from .. import compat
from ..ddl.base import _table_for_constraint, _fk_spec
import re
from ..compat import string_types

log = logging.getLogger(__name__)

MAX_PYTHON_ARGS = 255

try:
    from sqlalchemy.sql.naming import conv

    def _render_gen_name(autogen_context, name):
        if isinstance(name, conv):
            return _f_name(_alembic_autogenerate_prefix(autogen_context), name)
        else:
            return name
except ImportError:
    def _render_gen_name(autogen_context, name):
        return name


class _f_name(object):

    def __init__(self, prefix, name):
        self.prefix = prefix
        self.name = name

    def __repr__(self):
        return "%sf(%r)" % (self.prefix, _ident(self.name))


def _ident(name):
    """produce a __repr__() object for a string identifier that may
    use quoted_name() in SQLAlchemy 0.9 and greater.

    The issue worked around here is that quoted_name() doesn't have
    very good repr() behavior by itself when unicode is involved.

    """
    if name is None:
        return name
    elif compat.sqla_09 and isinstance(name, sql.elements.quoted_name):
        if compat.py2k:
            # the attempt to encode to ascii here isn't super ideal,
            # however we are trying to cut down on an explosion of
            # u'' literals only when py2k + SQLA 0.9, in particular
            # makes unit tests testing code generation very difficult
            try:
                return name.encode('ascii')
            except UnicodeError:
                return compat.text_type(name)
        else:
            return compat.text_type(name)
    elif isinstance(name, compat.string_types):
        return name


def _render_potential_expr(value, autogen_context, wrap_in_text=True):
    if isinstance(value, sql.ClauseElement):
        if compat.sqla_08:
            compile_kw = dict(compile_kwargs={'literal_binds': True})
        else:
            compile_kw = {}

        if wrap_in_text:
            template = "%(prefix)stext(%(sql)r)"
        else:
            template = "%(sql)r"

        return template % {
            "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
            "sql": compat.text_type(
                value.compile(dialect=autogen_context['dialect'],
                              **compile_kw)
            )
        }

    else:
        return repr(value)


def _add_table(table, autogen_context):
    args = [col for col in
            [_render_column(col, autogen_context) for col in table.c]
            if col] + \
        sorted([rcons for rcons in
                [_render_constraint(cons, autogen_context) for cons in
                 table.constraints]
                if rcons is not None
                ])

    if len(args) > MAX_PYTHON_ARGS:
        args = '*[' + ',\n'.join(args) + ']'
    else:
        args = ',\n'.join(args)

    text = "%(prefix)screate_table(%(tablename)r,\n%(args)s" % {
        'tablename': _ident(table.name),
        'prefix': _alembic_autogenerate_prefix(autogen_context),
        'args': args,
    }
    if table.schema:
        text += ",\nschema=%r" % _ident(table.schema)
    for k in sorted(table.kwargs):
        text += ",\n%s=%r" % (k.replace(" ", "_"), table.kwargs[k])
    text += "\n)"
    return text


def _drop_table(table, autogen_context):
    text = "%(prefix)sdrop_table(%(tname)r" % {
        "prefix": _alembic_autogenerate_prefix(autogen_context),
        "tname": _ident(table.name)
    }
    if table.schema:
        text += ", schema=%r" % _ident(table.schema)
    text += ")"
    return text


def _get_index_rendered_expressions(idx, autogen_context):
    if compat.sqla_08:
        return [repr(_ident(getattr(exp, "name", None)))
                if isinstance(exp, sa_schema.Column)
                else _render_potential_expr(exp, autogen_context)
                for exp in idx.expressions]
    else:
        return [
            repr(_ident(getattr(col, "name", None))) for col in idx.columns]


def _add_index(index, autogen_context):
    """
    Generate Alembic operations for the CREATE INDEX of an
    :class:`~sqlalchemy.schema.Index` instance.
    """

    has_batch = 'batch_prefix' in autogen_context

    if has_batch:
        tmpl = "%(prefix)screate_index(%(name)r, [%(columns)s], "\
            "unique=%(unique)r%(kwargs)s)"
    else:
        tmpl = "%(prefix)screate_index(%(name)r, %(table)r, [%(columns)s], "\
            "unique=%(unique)r%(schema)s%(kwargs)s)"

    text = tmpl % {
        'prefix': _alembic_autogenerate_prefix(autogen_context),
        'name': _render_gen_name(autogen_context, index.name),
        'table': _ident(index.table.name),
        'columns': ", ".join(
            _get_index_rendered_expressions(index, autogen_context)),
        'unique': index.unique or False,
        'schema': (", schema=%r" % _ident(index.table.schema))
        if index.table.schema else '',
        'kwargs': (
            ', ' +
            ', '.join(
                ["%s=%s" %
                 (key, _render_potential_expr(val, autogen_context))
                 for key, val in index.kwargs.items()]))
        if len(index.kwargs) else ''
    }
    return text


def _drop_index(index, autogen_context):
    """
    Generate Alembic operations for the DROP INDEX of an
    :class:`~sqlalchemy.schema.Index` instance.
    """
    has_batch = 'batch_prefix' in autogen_context

    if has_batch:
        tmpl = "%(prefix)sdrop_index(%(name)r)"
    else:
        tmpl = "%(prefix)sdrop_index(%(name)r, "\
            "table_name=%(table_name)r%(schema)s)"

    text = tmpl % {
        'prefix': _alembic_autogenerate_prefix(autogen_context),
        'name': _render_gen_name(autogen_context, index.name),
        'table_name': _ident(index.table.name),
        'schema': ((", schema=%r" % _ident(index.table.schema))
                   if index.table.schema else '')
    }
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

    has_batch = 'batch_prefix' in autogen_context

    if constraint.deferrable:
        opts.append(("deferrable", str(constraint.deferrable)))
    if constraint.initially:
        opts.append(("initially", str(constraint.initially)))
    if not has_batch and alter and constraint.table.schema:
        opts.append(("schema", _ident(constraint.table.schema)))
    if not alter and constraint.name:
        opts.append(
            ("name",
             _render_gen_name(autogen_context, constraint.name)))

    if alter:
        args = [
            repr(_render_gen_name(autogen_context, constraint.name))]
        if not has_batch:
            args += [repr(_ident(constraint.table.name))]
        args.append(repr([_ident(col.name) for col in constraint.columns]))
        args.extend(["%s=%r" % (k, v) for k, v in opts])
        return "%(prefix)screate_unique_constraint(%(args)s)" % {
            'prefix': _alembic_autogenerate_prefix(autogen_context),
            'args': ", ".join(args)
        }
    else:
        args = [repr(_ident(col.name)) for col in constraint.columns]
        args.extend(["%s=%r" % (k, v) for k, v in opts])
        return "%(prefix)sUniqueConstraint(%(args)s)" % {
            "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
            "args": ", ".join(args)
        }


def _add_fk_constraint(constraint, autogen_context):
    source_schema, source_table, \
        source_columns, target_schema, \
        target_table, target_columns = _fk_spec(constraint)

    args = [
        repr(_render_gen_name(autogen_context, constraint.name)),
        repr(_ident(source_table)),
        repr(_ident(target_table)),
        repr([_ident(col) for col in source_columns]),
        repr([_ident(col) for col in target_columns])
    ]
    if source_schema:
        args.append(
            "%s=%r" % ('source_schema', source_schema),
        )
    if target_schema:
        args.append(
            "%s=%r" % ('referent_schema', target_schema)
        )

    if constraint.deferrable:
        args.append("%s=%r" % ("deferrable", str(constraint.deferrable)))
    if constraint.initially:
        args.append("%s=%r" % ("initially", str(constraint.initially)))
    return "%(prefix)screate_foreign_key(%(args)s)" % {
        'prefix': _alembic_autogenerate_prefix(autogen_context),
        'args': ", ".join(args)
    }


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

    types = {
        "unique_constraint": "unique",
        "foreign_key_constraint": "foreignkey",
        "primary_key_constraint": "primary",
        "check_constraint": "check",
        "column_check_constraint": "check",
    }

    if 'batch_prefix' in autogen_context:
        template = "%(prefix)sdrop_constraint"\
            "(%(name)r, type_=%(type)r)"
    else:
        template = "%(prefix)sdrop_constraint"\
            "(%(name)r, '%(table_name)s'%(schema)s, type_=%(type)r)"

    constraint_table = _table_for_constraint(constraint)
    text = template % {
        'prefix': _alembic_autogenerate_prefix(autogen_context),
        'name': _render_gen_name(autogen_context, constraint.name),
        'table_name': _ident(constraint_table.name),
        'type': types[constraint.__visit_name__],
        'schema': (", schema='%s'" % _ident(constraint_table.schema))
        if constraint_table.schema else '',
    }
    return text


def _add_column(schema, tname, column, autogen_context):
    if 'batch_prefix' in autogen_context:
        template = "%(prefix)sadd_column(%(column)s)"
    else:
        template = "%(prefix)sadd_column(%(tname)r, %(column)s"
        if schema:
            template += ", schema=%(schema)r"
        template += ")"
    text = template % {
        "prefix": _alembic_autogenerate_prefix(autogen_context),
        "tname": tname,
        "column": _render_column(column, autogen_context),
        "schema": schema
    }
    return text


def _drop_column(schema, tname, column, autogen_context):
    if 'batch_prefix' in autogen_context:
        template = "%(prefix)sdrop_column(%(cname)r)"
    else:
        template = "%(prefix)sdrop_column(%(tname)r, %(cname)r"
        if schema:
            template += ", schema=%(schema)r"
        template += ")"

    text = template % {
        "prefix": _alembic_autogenerate_prefix(autogen_context),
        "tname": _ident(tname),
        "cname": _ident(column.name),
        "schema": _ident(schema)
    }
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
    indent = " " * 11

    if 'batch_prefix' in autogen_context:
        template = "%(prefix)salter_column(%(cname)r"
    else:
        template = "%(prefix)salter_column(%(tname)r, %(cname)r"

    text = template % {
        'prefix': _alembic_autogenerate_prefix(
            autogen_context),
        'tname': tname,
        'cname': cname}
    text += ",\n%sexisting_type=%s" % (
        indent,
        _repr_type(existing_type, autogen_context))
    if server_default is not False:
        rendered = _render_server_default(
            server_default, autogen_context)
        text += ",\n%sserver_default=%s" % (indent, rendered)

    if type_ is not None:
        text += ",\n%stype_=%s" % (indent,
                                   _repr_type(type_, autogen_context))
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
    if schema and "batch_prefix" not in autogen_context:
        text += ",\n%sschema=%r" % (indent, schema)
    text += ")"
    return text


def _user_autogenerate_prefix(autogen_context, target):
    prefix = autogen_context['opts']['user_module_prefix']
    if prefix is None:
        return "%s." % target.__module__
    else:
        return prefix


def _sqlalchemy_autogenerate_prefix(autogen_context):
    return autogen_context['opts']['sqlalchemy_module_prefix'] or ''


def _alembic_autogenerate_prefix(autogen_context):
    if 'batch_prefix' in autogen_context:
        return autogen_context['batch_prefix']
    else:
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
        'name': _ident(column.name),
        'type': _repr_type(column.type, autogen_context),
        'kw': ", ".join(["%s=%s" % (kwname, val) for kwname, val in opts])
    }


def _render_server_default(default, autogen_context, repr_=True):
    rendered = _user_defined_render("server_default", default, autogen_context)
    if rendered is not False:
        return rendered

    if isinstance(default, sa_schema.DefaultClause):
        if isinstance(default.arg, compat.string_types):
            default = default.arg
        else:
            return _render_potential_expr(default.arg, autogen_context)

    if isinstance(default, string_types) and repr_:
        default = repr(re.sub(r"^'|'$", "", default))

    return default


def _repr_type(type_, autogen_context):
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
    elif mod.startswith("sqlalchemy"):
        prefix = _sqlalchemy_autogenerate_prefix(autogen_context)
        return "%s%r" % (prefix, type_)
    else:
        prefix = _user_autogenerate_prefix(autogen_context, type_)
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
        opts.append(("name", repr(
            _render_gen_name(autogen_context, constraint.name))))
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
    colspec = fk._get_colspec()
    if metadata_schema is not None and colspec.count(".") == 1:
        # need to render schema breaking up tokens by hand, since the
        # ForeignKeyConstraint here may not actually have a remote
        # Table present
        # no schema in the colspec, render it
        colspec = "%s.%s" % (metadata_schema, colspec)
    return colspec


def _render_foreign_key(constraint, autogen_context):
    rendered = _user_defined_render("foreign_key", constraint, autogen_context)
    if rendered is not False:
        return rendered

    opts = []
    if constraint.name:
        opts.append(("name", repr(
            _render_gen_name(autogen_context, constraint.name))))
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
            "cols": ", ".join(
                "%r" % f.parent.key for f in constraint.elements),
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
        opts.append(
            (
                "name",
                repr(
                    _render_gen_name(autogen_context, constraint.name))
            )
        )
    return "%(prefix)sCheckConstraint(%(sqltext)s%(opts)s)" % {
        "prefix": _sqlalchemy_autogenerate_prefix(autogen_context),
        "opts": ", " + (", ".join("%s=%s" % (k, v)
                                  for k, v in opts)) if opts else "",
        "sqltext": _render_potential_expr(
            constraint.sqltext, autogen_context, wrap_in_text=False)
    }

_constraint_renderers = {
    sa_schema.PrimaryKeyConstraint: _render_primary_key,
    sa_schema.ForeignKeyConstraint: _render_foreign_key,
    sa_schema.UniqueConstraint: _render_unique_constraint,
    sa_schema.CheckConstraint: _render_check_constraint
}
