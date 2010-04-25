from alembic import options, command

__version__ = '0.1alpha'



def main(argv):

    parser = options.get_option_parser()

    opt = options.Options(parser, argv)
    cmd = opt.get_command().replace('-', '_')
    if cmd not in dir(command):
        parser.error("no such command %r" % cmd)
    getattr(command, cmd)(opt)



