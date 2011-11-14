from alembic import context
from sqlalchemy import engine_from_config
from logging.config import fileConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Pyhton logging. 
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# Produce a SQLAlchemy engine using the key/values
# within the "alembic" section of the documentation,
# other otherwise what config_ini_section points to.
engine = engine_from_config(
            config.get_section(config.config_ini_section), prefix='sqlalchemy.')


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# if we're running in --sql mode, do everything connectionless.
if not context.requires_connection():
    context.configure(dialect_name=engine.name)
    context.run_migrations()

# otherwise we need to make a connection.
else:
    connection = engine.connect()
    context.configure(connection=connection, dialect_name=engine.name)

    trans = connection.begin()
    try:
        context.run_migrations()
        trans.commit()
    except:
        trans.rollback()
        raise