"""Pylons bootstrap environment.

Place 'pylons_config_file' into alembic.ini, and the application will 
be loaded from there.

"""
from alembic import options, context
from paste.deploy import loadapp
import logging

try:
    # if pylons app already in, don't create a new app
    from pylons import config
    config['__file__']
except:
    # can use config['__file__'] here, i.e. the Pylons
    # ini file, instead of alembic.ini
    config_file = options.get_main_option('pylons_config_file')
    config_file = options.config_file_name
    logging.config.fileConfig(config_file)
    wsgi_app = loadapp('config:%s' % config_file, relative_to='.')

# customize this section for non-standard engine configurations.
meta = __import__("%s.model.meta" % config['pylons.package']).model.meta

if not context.requires_connection():
    context.configure(
                dialect_name=meta.engine.name)
    context.run_migrations()
else:
    connection = meta.engine.connect()
    context.configure_connection(connection)
    trans = connection.begin()
    try:
        context.run_migrations()
        trans.commit()
    except:
        trans.rollback()
        raise