USE_TWOPHASE = False

from alembic import options, context
from sqlalchemy import engine_from_config
import re

import logging
logging.fileConfig(options.config_file)

db_names = options.get_main_option('databases')

engines = {}
for name in re.split(r',\s*', db_names):
    engines[name] = rec = {}
    rec['engine'] = engine = \
                engine_from_config(options.get_section(name), prefix='sqlalchemy.')
    rec['connection'] = conn = engine.connect()
    
    if USE_TWOPHASE:
        rec['transaction'] = conn.begin_twophase()
    else:
        rec['transaction'] = conn.begin()
    
try:
    for name, rec in engines.items():
        context.configure_connection(rec['connection'])
        context.run_migrations(engine=name)

    if USE_TWOPHASE:
        for rec in engines.values():
            rec['transaction'].prepare()
        
    for rec in engines.values():
        rec['transaction'].commit()
except:
    for rec in engines.values():
        rec['transaction'].rollback()
