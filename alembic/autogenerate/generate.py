from .. import util
from .api import _produce_migration_diffs


class GeneratedRevision(object):
    def __init__(self, revision_context):
        self.revision_context = revision_context
        self.template_args = {}
        self.imports = set()
        self.rev_id = revision_context.command_args['rev_id'] or util.rev_id()

        self.head = self.revision_context.command_args['head']
        self.splice = self.revision_context.command_args['splice']
        self.branch_label = \
            self.revision_context.command_args['branch_label']
        self.version_path = self.revision_context.command_args['version_path']

    def to_script(self):
        for k, v in self.revision_context.template_args.items():
            self.template_args.setdefault(k, v)

        return self.revision_context.script_directory.generate_revision(
            self.rev_id,
            self.revision_context.command_args['message'],
            refresh=True,
            head=self.head,
            splice=self.splice,
            branch_labels=self.branch_label,
            version_path=self.version_path,
            **self.template_args)


class RevisionContext(object):
    def __init__(self, config, script_directory, command_args):
        self.config = config
        self.script_directory = script_directory
        self.command_args = command_args
        self.template_args = {
            'config': config  # Let templates use config for
                              # e.g. multiple databases
        }
        self.generated_revisions = [
            GeneratedRevision(self)
        ]

    def run_autogenerate(self, rev, context):
        if self.command_args['sql']:
            raise util.CommandError(
                "Using --sql with --autogenerate does not make any sense")
        if set(self.script_directory.get_revisions(rev)) != \
                set(self.script_directory.get_revisions("heads")):
            raise util.CommandError("Target database is not up to date.")
        for generated_revision in self.generated_revisions:
            _produce_migration_diffs(
                context,
                generated_revision.template_args, generated_revision.imports)

    def run_no_autogenerate(self, rev, context):
        pass

    def generate_scripts(self):
        for generated_revision in self.generated_revisions:
            yield generated_revision.to_script()
