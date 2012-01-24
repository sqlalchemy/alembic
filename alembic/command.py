from alembic.script import ScriptDirectory
from alembic import util, ddl, autogenerate as autogen, environment
import os
import functools

def list_templates(config):
    """List available templates"""

    print "Available templates:\n"
    for tempname in os.listdir(config.get_template_directory()):
        readme = os.path.join(
                        config.get_template_directory(), 
                        tempname, 
                        'README')
        synopsis = open(readme).next()
        print "%s - %s" % (tempname, synopsis)

    print "\nTemplates are used via the 'init' command, e.g.:"
    print "\n  alembic init --template pylons ./scripts"

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
        if file_ == 'alembic.ini.mako':
            config_file = os.path.abspath(config.config_file_name)
            if os.access(config_file, os.F_OK):
                util.msg("File %s already exists, skipping" % config_file)
            else:
                script.generate_template(
                    os.path.join(template_dir, file_),
                    config_file,
                    script_location=directory
                )
        else:
            output_file = os.path.join(directory, file_)
            script.copy_file(
                os.path.join(template_dir, file_), 
                output_file
            )

    util.msg("Please edit configuration/connection/logging "\
            "settings in %r before proceeding." % config_file)

def revision(config, message=None, autogenerate=False):
    """Create a new revision file."""

    script = ScriptDirectory.from_config(config)
    template_args = {}
    imports = set()
    if autogenerate:
        util.requires_07("autogenerate")
        def retrieve_migrations(rev, context):
            if script._get_rev(rev) is not script._get_rev("head"):
                raise util.CommandError("Target database is not up to date.")
            autogen.produce_migration_diffs(context, template_args, imports)
            return []

        with environment.configure(
            config,
            script,
            fn = retrieve_migrations
        ):
            script.run_env()
    script.generate_rev(util.rev_id(), message, **template_args)


def upgrade(config, revision, sql=False, tag=None):
    """Upgrade to a later version."""

    script = ScriptDirectory.from_config(config)

    starting_rev = None
    if ":" in revision:
        if not sql:
            raise util.CommandError("Range revision not allowed")
        starting_rev, revision = revision.split(':', 2)
    with environment.configure(
        config,
        script,
        fn = functools.partial(script.upgrade_from, revision),
        as_sql = sql,
        starting_rev = starting_rev,
        destination_rev = revision,
        tag = tag
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

    with environment.configure(
        config,
        script,
        fn = functools.partial(script.downgrade_to, revision),
        as_sql = sql,
        starting_rev = starting_rev,
        destination_rev = revision,
        tag = tag
    ):
        script.run_env()

def history(config):
    """List changeset scripts in chronological order."""

    script = ScriptDirectory.from_config(config)
    for sc in script.walk_revisions():
        if sc.is_head:
            print
        print sc

def branches(config):
    """Show current un-spliced branch points"""
    script = ScriptDirectory.from_config(config)
    for sc in script.walk_revisions():
        if sc.is_branch_point:
            print sc
            for rev in sc.nextrev:
                print "%s -> %s" % (
                    " " * len(str(sc.down_revision)),
                    script._get_rev(rev)
                )

def current(config):
    """Display the current revision for each database."""

    script = ScriptDirectory.from_config(config)
    def display_version(rev, context):
        print "Current revision for %s: %s" % (
                            util.obfuscate_url_pw(
                                context.connection.engine.url),
                            script._get_rev(rev))
        return []

    with environment.configure(
        config,
        script,
        fn = display_version
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
        dest = script._get_rev(revision)
        if dest is not None:
            dest = dest.revision
        context._update_current_rev(current, dest)
        return []
    with environment.configure(
        config, 
        script,
        fn = do_stamp,
        as_sql = sql,
        destination_rev = revision,
        tag = tag
    ) as env:
        script.run_env()

def splice(config, parent, child):
    """'splice' two branches, creating a new revision file.
    
    this command isn't implemented right now.
    
    """
    raise NotImplementedError()


