import os

from .script import ScriptDirectory
from .runtime.environment import EnvironmentContext
from . import util
from . import autogenerate as autogen


def list_templates(config):
    """List available templates"""

    config.print_stdout("Available templates:\n")
    for tempname in os.listdir(config.get_template_directory()):
        with open(os.path.join(
                config.get_template_directory(),
                tempname,
                'README')) as readme:
            synopsis = next(readme)
        config.print_stdout("%s - %s", tempname, synopsis)

    config.print_stdout("\nTemplates are used via the 'init' command, e.g.:")
    config.print_stdout("\n  alembic init --template generic ./scripts")


def init(config, directory, template='generic'):
    """Initialize a new scripts directory."""

    if os.access(directory, os.F_OK):
        raise util.CommandError("Directory %s already exists" % directory)

    template_dir = os.path.join(config.get_template_directory(),
                                template)
    if not os.access(template_dir, os.F_OK):
        raise util.CommandError("No such template %r" % template)

    util.status("Creating directory %s" % os.path.abspath(directory),
                os.makedirs, directory)

    versions = os.path.join(directory, 'versions')
    util.status("Creating directory %s" % os.path.abspath(versions),
                os.makedirs, versions)

    script = ScriptDirectory(directory)

    for file_ in os.listdir(template_dir):
        file_path = os.path.join(template_dir, file_)
        if file_ == 'alembic.ini.mako':
            config_file = os.path.abspath(config.config_file_name)
            if os.access(config_file, os.F_OK):
                util.msg("File %s already exists, skipping" % config_file)
            else:
                script._generate_template(
                    file_path,
                    config_file,
                    script_location=directory
                )
        elif os.path.isfile(file_path):
            output_file = os.path.join(directory, file_)
            script._copy_file(
                file_path,
                output_file
            )

    util.msg("Please edit configuration/connection/logging "
             "settings in %r before proceeding." % config_file)


def revision(
        config, message=None, autogenerate=False, sql=False,
        head="head", splice=False, branch_label=None,
        version_path=None, rev_id=None, depends_on=None):
    """Create a new revision file."""

    script_directory = ScriptDirectory.from_config(config)

    command_args = dict(
        message=message,
        autogenerate=autogenerate,
        sql=sql, head=head, splice=splice, branch_label=branch_label,
        version_path=version_path, rev_id=rev_id, depends_on=depends_on
    )
    revision_context = autogen.RevisionContext(
        config, script_directory, command_args)

    environment = util.asbool(
        config.get_main_option("revision_environment")
    )

    if autogenerate:
        environment = True

        if sql:
            raise util.CommandError(
                "Using --sql with --autogenerate does not make any sense")

        def retrieve_migrations(rev, context):
            revision_context.run_autogenerate(rev, context)
            return []
    elif environment:
        def retrieve_migrations(rev, context):
            revision_context.run_no_autogenerate(rev, context)
            return []
    elif sql:
        raise util.CommandError(
            "Using --sql with the revision command when "
            "revision_environment is not configured does not make any sense")

    if environment:
        with EnvironmentContext(
            config,
            script_directory,
            fn=retrieve_migrations,
            as_sql=sql,
            template_args=revision_context.template_args,
            revision_context=revision_context
        ):
            script_directory.run_env()

    scripts = [
        script for script in
        revision_context.generate_scripts()
    ]
    if len(scripts) == 1:
        return scripts[0]
    else:
        return scripts


def merge(config, revisions, message=None, branch_label=None, rev_id=None):
    """Merge two revisions together.  Creates a new migration file.

    .. versionadded:: 0.7.0

    .. seealso::

        :ref:`branches`

    """

    script = ScriptDirectory.from_config(config)
    template_args = {
        'config': config  # Let templates use config for
                          # e.g. multiple databases
    }
    return script.generate_revision(
        rev_id or util.rev_id(), message, refresh=True,
        head=revisions, branch_labels=branch_label,
        **template_args)


def upgrade(config, revision, sql=False, tag=None):
    """Upgrade to a later version."""

    script = ScriptDirectory.from_config(config)

    starting_rev = None
    if ":" in revision:
        if not sql:
            raise util.CommandError("Range revision not allowed")
        starting_rev, revision = revision.split(':', 2)

    def upgrade(rev, context):
        return script._upgrade_revs(revision, rev)

    with EnvironmentContext(
        config,
        script,
        fn=upgrade,
        as_sql=sql,
        starting_rev=starting_rev,
        destination_rev=revision,
        tag=tag
    ):
        script.run_env()


def downgrade(config, revision, sql=False, tag=None):
    """Revert to a previous version."""

    script = ScriptDirectory.from_config(config)
    starting_rev = None
    if ":" in revision:
        if not sql:
            raise util.CommandError("Range revision not allowed")
        starting_rev, revision = revision.split(':', 2)
    elif sql:
        raise util.CommandError(
            "downgrade with --sql requires <fromrev>:<torev>")

    def downgrade(rev, context):
        return script._downgrade_revs(revision, rev)

    with EnvironmentContext(
        config,
        script,
        fn=downgrade,
        as_sql=sql,
        starting_rev=starting_rev,
        destination_rev=revision,
        tag=tag
    ):
        script.run_env()


def show(config, rev):
    """Show the revision(s) denoted by the given symbol."""

    script = ScriptDirectory.from_config(config)

    if rev == "current":
        def show_current(rev, context):
            for sc in script.get_revisions(rev):
                config.print_stdout(sc.log_entry)
            return []
        with EnvironmentContext(
            config,
            script,
            fn=show_current
        ):
            script.run_env()
    else:
        for sc in script.get_revisions(rev):
            config.print_stdout(sc.log_entry)


def history(config, rev_range=None, verbose=False):
    """List changeset scripts in chronological order."""

    script = ScriptDirectory.from_config(config)
    if rev_range is not None:
        if ":" not in rev_range:
            raise util.CommandError(
                "History range requires [start]:[end], "
                "[start]:, or :[end]")
        base, head = rev_range.strip().split(":")
    else:
        base = head = None

    def _display_history(config, script, base, head):
        for sc in script.walk_revisions(
                base=base or "base",
                head=head or "heads"):
            config.print_stdout(
                sc.cmd_format(
                    verbose=verbose, include_branches=True,
                    include_doc=True, include_parents=True))

    def _display_history_w_current(config, script, base=None, head=None):
        def _display_current_history(rev, context):
            if head is None:
                _display_history(config, script, base, rev)
            elif base is None:
                _display_history(config, script, rev, head)
            return []

        with EnvironmentContext(
            config,
            script,
            fn=_display_current_history
        ):
            script.run_env()

    if base == "current":
        _display_history_w_current(config, script, head=head)
    elif head == "current":
        _display_history_w_current(config, script, base=base)
    else:
        _display_history(config, script, base, head)


def heads(config, verbose=False, resolve_dependencies=False):
    """Show current available heads in the script directory"""

    script = ScriptDirectory.from_config(config)
    if resolve_dependencies:
        heads = script.get_revisions("heads")
    else:
        heads = script.get_revisions(script.get_heads())

    for rev in heads:
        config.print_stdout(
            rev.cmd_format(
                verbose, include_branches=True, tree_indicators=False))


def branches(config, verbose=False):
    """Show current branch points"""
    script = ScriptDirectory.from_config(config)
    for sc in script.walk_revisions():
        if sc.is_branch_point:
            config.print_stdout(
                "%s\n%s\n",
                sc.cmd_format(verbose, include_branches=True),
                "\n".join(
                    "%s -> %s" % (
                        " " * len(str(sc.revision)),
                        rev_obj.cmd_format(
                            False, include_branches=True, include_doc=verbose)
                    ) for rev_obj in
                    (script.get_revision(rev) for rev in sc.nextrev)
                )
            )


def current(config, verbose=False, head_only=False):
    """Display the current revision for a database."""

    script = ScriptDirectory.from_config(config)

    if head_only:
        util.warn("--head-only is deprecated")

    def display_version(rev, context):
        if verbose:
            config.print_stdout(
                "Current revision(s) for %s:",
                util.obfuscate_url_pw(context.connection.engine.url)
            )
        for rev in script.get_all_current(rev):
            config.print_stdout(rev.cmd_format(verbose))

        return []

    with EnvironmentContext(
        config,
        script,
        fn=display_version
    ):
        script.run_env()


def stamp(config, revision, sql=False, tag=None):
    """'stamp' the revision table with the given revision; don't
    run any migrations."""

    script = ScriptDirectory.from_config(config)

    starting_rev = None
    if ":" in revision:
        if not sql:
            raise util.CommandError("Range revision not allowed")
        starting_rev, revision = revision.split(':', 2)

    def do_stamp(rev, context):
        return script._stamp_revs(revision, rev)

    with EnvironmentContext(
        config,
        script,
        fn=do_stamp,
        as_sql=sql,
        destination_rev=revision,
        starting_rev=starting_rev,
        tag=tag
    ):
        script.run_env()


def edit(config, rev):
    """Edit revision script(s) using $EDITOR"""

    script = ScriptDirectory.from_config(config)

    if rev == "current":
        def edit_current(rev, context):
            if not rev:
                raise util.CommandError("No current revisions")
            for sc in script.get_revisions(rev):
                util.edit(sc.path)
            return []
        with EnvironmentContext(
            config,
            script,
            fn=edit_current
        ):
            script.run_env()
    else:
        revs = script.get_revisions(rev)
        if not revs:
            raise util.CommandError(
                "No revision files indicated by symbol '%s'" % rev)
        for sc in revs:
            util.edit(sc.path)

