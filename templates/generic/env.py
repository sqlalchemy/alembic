from alembic import options, context
from sqlalchemy import engine_from_config
import logging

logging.fileConfig(options.config_file)

engine = engine_from_config(options.get_section('alembic'), prefix='sqlalchemy.')

connection = engine.connect()
context.configure_connection(connection)
trans = connection.begin()
try:
    context.run_migrations()
    trans.commit()
except:
    trans.rollback()
