USE_TWOPHASE = False

from alembic import options, context
from sqlalchemy import engine_from_config
import re
import sys

import logging
logging.fileConfig(options.config_file)

db_names = options.get_main_option('databases')
engines = {}
for name in re.split(r',\s*', db_names):
    engines[name] = rec = {}
    rec['engine'] = engine = \
                engine_from_config(options.get_section(name),
                                prefix='sqlalchemy.')


if not context.requires_connection():
    for name, rec in engines.items():
        # Write output to individual per-engine files.
        file_ = "%s.sql" % name
        sys.stderr.write("Writing output to %s\n" % file_)
        context.configure(
                    dialect_name=rec['engine'].name,
                    output_buffer=file(file_, 'w')
                )
        context.run_migrations(engine=name)
else:
    for name, rec in engines.items():
        engine = rec['engine']
        rec['connection'] = conn = engine.connect()

        if USE_TWOPHASE:
            rec['transaction'] = conn.begin_twophase()
        else:
            rec['transaction'] = conn.begin()

    try:
        for name, rec in engines.items():
            context.configure(
                        connection=rec['connection'],
                        dialect_name=rec['engine'].name
                    )
            context.execute("--running migrations for engine %s" % name)
            context.run_migrations(engine=name)

        if USE_TWOPHASE:
            for rec in engines.values():
                rec['transaction'].prepare()

        for rec in engines.values():
            rec['transaction'].commit()
    except:
        for rec in engines.values():
            rec['transaction'].rollback()
        raise