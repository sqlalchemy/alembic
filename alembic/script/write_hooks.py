import subprocess
import sys

from .. import util
from ..util import compat


_registry = {}


def register(name):
    """A function decorator that will register that function as a write hook.

    See the documentation linked below for an example.

    .. versionadded:: 1.2.0

    .. seealso::

        :ref:`post_write_hooks_custom`


    """

    def decorate(fn):
        _registry[name] = fn

    return decorate


def _invoke(name, revision, options):
    """Invokes the formatter registered for the given name.

    :param name: The name of a formatter in the registry
    :param revision: A :class:`.MigrationRevision` instance
    :param options: A dict containing kwargs passed to the
        specified formatter.
    :raises: :class:`alembic.util.CommandError`
    """
    try:
        hook = _registry[name]
    except KeyError:
        compat.raise_from_cause(
            util.CommandError("No formatter with name '%s' registered" % name)
        )
    else:
        return hook(revision, options)


def _run_hooks(path, hook_config):
    """Invoke hooks for a generated revision.

    """

    from .base import _split_on_space_comma

    names = _split_on_space_comma.split(hook_config.get("hooks", ""))

    for name in names:
        if not name:
            continue
        opts = {
            key[len(name) + 1 :]: hook_config[key]
            for key in hook_config
            if key.startswith(name + ".")
        }
        opts["_hook_name"] = name
        try:
            type_ = opts["type"]
        except KeyError:
            compat.raise_from_cause(
                util.CommandError(
                    "Key %s.type is required for post write hook %r"
                    % (name, name)
                )
            )
        else:
            util.status(
                'Running post write hook "%s"' % name,
                _invoke,
                type_,
                path,
                opts,
                newline=True,
            )


@register("console_scripts")
def console_scripts(path, options):
    import pkg_resources

    try:
        entrypoint_name = options["entrypoint"]
    except KeyError:
        compat.raise_from_cause(
            util.CommandError(
                "Key %s.entrypoint is required for post write hook %r"
                % (options["_hook_name"], options["_hook_name"])
            )
        )
    iter_ = pkg_resources.iter_entry_points("console_scripts", entrypoint_name)
    impl = next(iter_)
    options = options.get("options", "")
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import %s; %s()"
            % (impl.module_name, ".".join((impl.module_name,) + impl.attrs)),
            path,
        ]
        + options.split()
    )
