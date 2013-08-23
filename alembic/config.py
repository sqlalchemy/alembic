from argparse import ArgumentParser
from .compat import SafeConfigParser
import inspect
import os
import sys

from . import command, util, package_dir, compat

class Config(object):
    """Represent an Alembic configuration.

    Within an ``env.py`` script, this is available
    via the :attr:`.EnvironmentContext.config` attribute,
    which in turn is available at ``alembic.context``::

        from alembic import context

        some_param = context.config.get_main_option("my option")

    When invoking Alembic programatically, a new
    :class:`.Config` can be created by passing
    the name of an .ini file to the constructor::

        from alembic.config import Config
        alembic_cfg = Config("/path/to/yourapp/alembic.ini")

    With a :class:`.Config` object, you can then
    run Alembic commands programmatically using the directives
    in :mod:`alembic.command`.

    The :class:`.Config` object can also be constructed without
    a filename.   Values can be set programmatically, and
    new sections will be created as needed::

        from alembic.config import Config
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "myapp:migrations")
        alembic_cfg.set_main_option("url", "postgresql://foo/bar")
        alembic_cfg.set_section_option("mysection", "foo", "bar")

    :param file_: name of the .ini file to open.
    :param ini_section: name of the main Alembic section within the
     .ini file
    :param output_buffer: optional file-like input buffer which
     will be passed to the :class:`.MigrationContext` - used to redirect
     the output of "offline generation" when using Alembic programmatically.
    :param stdout: buffer where the "print" output of commands will be sent.
     Defaults to ``sys.stdout``.

     ..versionadded:: 0.4

    """
    def __init__(self, file_=None, ini_section='alembic', output_buffer=None,
                        stdout=sys.stdout, cmd_opts=None):
        """Construct a new :class:`.Config`

        """
        self.config_file_name = file_
        self.config_ini_section = ini_section
        self.output_buffer = output_buffer
        self.stdout = stdout
        self.cmd_opts = cmd_opts

    cmd_opts = None
    """The command-line options passed to the ``alembic`` script.

    Within an ``env.py`` script this can be accessed via the
    :attr:`.EnvironmentContext.config` attribute.

    .. versionadded:: 0.6.0

    .. seealso::

        :meth:`.EnvironmentContext.get_x_argument`

    """

    config_file_name = None
    """Filesystem path to the .ini file in use."""

    config_ini_section = None
    """Name of the config file section to read basic configuration
    from.  Defaults to ``alembic``, that is the ``[alembic]`` section
    of the .ini file.  This value is modified using the ``-n/--name``
    option to the Alembic runnier.

    """

    def print_stdout(self, text, *arg):
        """Render a message to standard out."""

        util.write_outstream(
                self.stdout,
                (compat.text_type(text) % arg),
                "\n"
        )

    @util.memoized_property
    def file_config(self):
        """Return the underlying :class:`ConfigParser` object.

        Direct access to the .ini file is available here,
        though the :meth:`.Config.get_section` and
        :meth:`.Config.get_main_option`
        methods provide a possibly simpler interface.

        """

        if self.config_file_name:
            here = os.path.abspath(os.path.dirname(self.config_file_name))
        else:
            here = ""
        file_config = SafeConfigParser({'here': here})
        if self.config_file_name:
            file_config.read([self.config_file_name])
        else:
            file_config.add_section(self.config_ini_section)
        return file_config

    def get_template_directory(self):
        """Return the directory where Alembic setup templates are found.

        This method is used by the alembic ``init`` and ``list_templates``
        commands.

        """
        return os.path.join(package_dir, 'templates')

    def get_section(self, name):
        """Return all the configuration options from a given .ini file section
        as a dictionary.

        """
        return dict(self.file_config.items(name))

    def set_main_option(self, name, value):
        """Set an option programmatically within the 'main' section.

        This overrides whatever was in the .ini file.

        """
        self.file_config.set(self.config_ini_section, name, value)

    def remove_main_option(self, name):
        self.file_config.remove_option(self.config_ini_section, name)

    def set_section_option(self, section, name, value):
        """Set an option programmatically within the given section.

        The section is created if it doesn't exist already.
        The value here will override whatever was in the .ini
        file.

        """
        if not self.file_config.has_section(section):
            self.file_config.add_section(section)
        self.file_config.set(section, name, value)

    def get_section_option(self, section, name, default=None):
        """Return an option from the given section of the .ini file.

        """
        if not self.file_config.has_section(section):
            raise util.CommandError("No config file %r found, or file has no "
                                "'[%s]' section" %
                                (self.config_file_name, section))
        if self.file_config.has_option(section, name):
            return self.file_config.get(section, name)
        else:
            return default

    def get_main_option(self, name, default=None):
        """Return an option from the 'main' section of the .ini file.

        This defaults to being a key from the ``[alembic]``
        section, unless the ``-n/--name`` flag were used to
        indicate a different section.

        """
        return self.get_section_option(self.config_ini_section, name, default)


class CommandLine(object):
    def __init__(self, prog=None):
        self._generate_args(prog)


    def _generate_args(self, prog):
        def add_options(parser, positional, kwargs):
            if 'template' in kwargs:
                parser.add_argument("-t", "--template",
                                default='generic',
                                type=str,
                                help="Setup template for use with 'init'")
            if 'message' in kwargs:
                parser.add_argument("-m", "--message",
                                type=str,
                                help="Message string to use with 'revision'")
            if 'sql' in kwargs:
                parser.add_argument("--sql",
                                action="store_true",
                                help="Don't emit SQL to database - dump to "
                                        "standard output/file instead")
            if 'tag' in kwargs:
                parser.add_argument("--tag",
                                type=str,
                                help="Arbitrary 'tag' name - can be used by "
                                "custom env.py scripts.")
            if 'autogenerate' in kwargs:
                parser.add_argument("--autogenerate",
                                action="store_true",
                                help="Populate revision script with candidate "
                                    "migration operations, based on comparison "
                                    "of database to model.")
            # "current" command
            if 'head_only' in kwargs:
                parser.add_argument("--head-only",
                                    action="store_true",
                                    help="Only show current version and "
                                    "whether or not this is the head revision.")

            if 'rev_range' in kwargs:
                parser.add_argument("-r", "--rev-range",
                                    action="store",
                                    help="Specify a revision range; "
                                    "format is [start]:[end]")


            positional_help = {
                'directory': "location of scripts directory",
                'revision': "revision identifier"
            }
            for arg in positional:
                subparser.add_argument(arg, help=positional_help.get(arg))

        parser = ArgumentParser(prog=prog)
        parser.add_argument("-c", "--config",
                            type=str,
                            default="alembic.ini",
                            help="Alternate config file")
        parser.add_argument("-n", "--name",
                            type=str,
                            default="alembic",
                            help="Name of section in .ini file to "
                                    "use for Alembic config")
        parser.add_argument("-x", action="append",
                            help="Additional arguments consumed by "
                            "custom env.py scripts, e.g. -x "
                            "setting1=somesetting -x setting2=somesetting")

        subparsers = parser.add_subparsers()

        for fn in [getattr(command, n) for n in dir(command)]:
            if inspect.isfunction(fn) and \
                fn.__name__[0] != '_' and \
                fn.__module__ == 'alembic.command':

                spec = inspect.getargspec(fn)
                if spec[3]:
                    positional = spec[0][1:-len(spec[3])]
                    kwarg = spec[0][-len(spec[3]):]
                else:
                    positional = spec[0][1:]
                    kwarg = []

                subparser = subparsers.add_parser(
                                    fn.__name__,
                                    help=fn.__doc__)
                add_options(subparser, positional, kwarg)
                subparser.set_defaults(cmd=(fn, positional, kwarg))
        self.parser = parser

    def run_cmd(self, config, options):
        fn, positional, kwarg = options.cmd

        try:
            fn(config,
                        *[getattr(options, k) for k in positional],
                        **dict((k, getattr(options, k)) for k in kwarg)
                    )
        except util.CommandError as e:
            util.err(str(e))

    def main(self, argv=None):
        options = self.parser.parse_args(argv)
        if not hasattr(options, "cmd"):
            # see http://bugs.python.org/issue9253, argparse
            # behavior changed incompatibly in py3.3
            self.parser.error("too few arguments")
        else:
            cfg = Config(file_=options.config,
                            ini_section=options.name, cmd_opts=options)
            self.run_cmd(cfg, options)

def main(argv=None, prog=None, **kwargs):
    """The console runner function for Alembic."""

    CommandLine(prog=prog).main(argv=argv)

if __name__ == '__main__':
    main()