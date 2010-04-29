"""Pylons bootstrap environment.

Place 'pylons_config_file' into alembic.ini, and the application will 
be loaded from there.

"""
from alembic import options, context
from paste.deploy import loadapp
from pylons import config
import logging

config_file = options.get_main_option('pylons_config_file')
logging.fileConfig(config_file)
wsgi_app = loadapp('config:%s' % config_file, relative_to='.')

# customize this section for non-standard engine configurations.
meta = __import__("%s.model.meta" % config['pylons.package']).model.meta

connection = meta.engine.connect()
context.configure_connection(connection)
trans = connection.begin()
try:
    context.run_migrations()
    trans.commit()
except:
    trans.rollback()
    raise