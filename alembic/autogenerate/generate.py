from .. import util
from . import api
from . import compose
from . import render
from ..operations import ops


class RevisionContext(object):
    def __init__(self, config, script_directory, command_args):
        self.config = config
        self.script_directory = script_directory
        self.command_args = command_args
        self.template_args = {
            'config': config  # Let templates use config for
                              # e.g. multiple databases
        }

    def _to_script(self, migration_script):
        template_args = {}
        for k, v in self.template_args.items():
            migration_script.template_args.setdefault(k, v)

        render._render_migration_script(
            migration_script.autogen_context, migration_script, template_args
        )

        return self.script_directory.generate_revision(
            migration_script.rev_id,
            migration_script.message,
            refresh=True,
            head=migration_script.head,
            splice=migration_script.splice,
            branch_labels=migration_script.branch_label,
            version_path=migration_script.version_path,
            **template_args)

    def run_autogenerate(self, rev, context):
        if self.command_args['sql']:
            raise util.CommandError(
                "Using --sql with --autogenerate does not make any sense")
        if set(self.script_directory.get_revisions(rev)) != \
                set(self.script_directory.get_revisions("heads")):
            raise util.CommandError("Target database is not up to date.")

        # TODO:
        """
        things = [
            MigrationScript(ops=[
                UpgradeOps(ops=[]),
                DowngradeOps(ops=[])
                ]),
            MigrationScript(ops=[
                UpgradeOps(ops=[]),
                DowngradeOps(ops=[])
                ]),
            MigrationScript(ops=[
                UpgradeOps(ops=[]),
                DowngradeOps(ops=[])
                ]),
        ]

        for thing in things:

        """

        autogen_context = api._autogen_context(context)

        diffs = []
        api._produce_net_changes(autogen_context, diffs)

        migration_script = self._default_revision()
        migration_script.autogen_context = autogen_context

        compose._to_migration_script(autogen_context, migration_script, diffs)

        self.generated_revisions = [migration_script]

        # DO THE HOOK HERE!!

    def run_no_autogenerate(self, rev, context):
        self.generated_revisions = [
            self._default_revision()
        ]

    def _default_revision(self):
        return ops.MigrationScript(
            rev_id=self.command_args['rev_id'] or util.rev_id(),
            message=self.command_args['message'],
            imports=set(),
            upgrade_ops=ops.UpgradeOps([]),
            downgrade_ops=ops.DowngradeOps([]),
            head=self.command_args['head'],
            splice=self.command_args['splice'],
            branch_label=self.command_args['branch_label'],
            version_path=self.command_args['version_path']
        )

    def generate_scripts(self):
        for generated_revision in self.generated_revisions:
            yield self._to_script(generated_revision)
