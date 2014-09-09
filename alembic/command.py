import os

from .script import ScriptDirectory
from .environment import EnvironmentContext
from . import util, autogenerate as autogen


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
    config.print_stdout("\n  alembic init --template pylons ./scripts")


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


def revision(config, message=None, autogenerate=False, sql=False):
    """Create a new revision file."""

    script = ScriptDirectory.from_config(config)
    template_args = {
        'config': config  # Let templates use config for
                          # e.g. multiple databases
    }
    imports = set()

    environment = util.asbool(
        config.get_main_option("revision_environment")
    )

    if autogenerate:
        environment = True

        def retrieve_migrations(rev, context):
            if script.get_revision(rev) is not script.get_revision("head"):
                raise util.CommandError("Target database is not up to date.")
            autogen._produce_migration_diffs(context, template_args, imports)
            return []
    elif environment:
        def retrieve_migrations(rev, context):
            return []

    if environment:
        with EnvironmentContext(
            config,
            script,
            fn=retrieve_migrations,
            as_sql=sql,
            template_args=template_args,
        ):
            script.run_env()
    return script.generate_revision(util.rev_id(), message, refresh=True,
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


def history(config, rev_range=None):
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
                head=head or "head"):
            if sc.is_head:
                config.print_stdout("")
            config.print_stdout(sc.log_entry)

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


def branches(config):
    """Show current un-spliced branch points"""
    script = ScriptDirectory.from_config(config)
    for sc in script.walk_revisions():
        if sc.is_branch_point:
            config.print_stdout(sc)
            for rev in sc.nextrev:
                config.print_stdout("%s -> %s",
                                    " " * len(str(sc.down_revision)),
                                    script.get_revision(rev)
                                    )


def current(config, head_only=False):
    """Display the current revision for each database."""

    script = ScriptDirectory.from_config(config)

    def display_version(rev, context):
        rev = script.get_revision(rev)

        if head_only:
            config.print_stdout("%s%s" % (
                rev.revision if rev else None,
                " (head)" if rev and rev.is_head else ""))

        else:
            config.print_stdout("Current revision for %s: %s",
                                util.obfuscate_url_pw(
                                    context.connection.engine.url),
                                rev)
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

    def do_stamp(rev, context):
        if sql:
            current = False
        else:
            current = context._current_rev()
        dest = script.get_revision(revision)
        if dest is not None:
            dest = dest.revision
        context._update_current_rev(current, dest)
        return []
    with EnvironmentContext(
        config,
        script,
        fn=do_stamp,
        as_sql=sql,
        destination_rev=revision,
        tag=tag
    ):
        script.run_env()


def splice(config, parent, child):
    """'splice' two branches, creating a new revision file.

    this command isn't implemented right now.

    """
    raise NotImplementedError()
