from .. import util
from .api import _render_migration_diffs
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

        # TODO: this would somehow be streamed out
        # from autogenerate as part of run_autogenerate
        # and run_no_autogenerate
        self.generated_revisions = [
            ops.MigrationScript(
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
        ]
        # not sure if template_args should be on the MigrationScript
        # or if this represents a rendering of a MigrationScript and is
        # separate, or something
        self.generated_revisions[0].template_args = {}

    def _to_script(self, migration_script):
        for k, v in self.template_args.items():
            migration_script.template_args.setdefault(k, v)

        return self.script_directory.generate_revision(
            migration_script.rev_id,
            migration_script.message,
            refresh=True,
            head=migration_script.head,
            splice=migration_script.splice,
            branch_labels=migration_script.branch_label,
            version_path=migration_script.version_path,
            **migration_script.template_args)

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
        # TODO: need to separate out generation of scripts and ops
        # directives vs. rendering
        for generated_revision in self.generated_revisions:
            _render_migration_diffs(
                context,
                generated_revision.template_args, generated_revision.imports)

    def run_no_autogenerate(self, rev, context):
        pass

    def generate_scripts(self):
        for generated_revision in self.generated_revisions:
            yield self._to_script(generated_revision)
