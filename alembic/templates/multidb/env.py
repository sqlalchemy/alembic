USE_TWOPHASE = False

from alembic import context
from sqlalchemy import engine_from_config
import re
import sys

import logging
logging.fileConfig(options.config_file)

# gather section names referring to different 
# databases.
db_names = options.get_main_option('databases')

# set aside if we need engines or just URLs to do this.
need_engine = context.requires_connection()

# load up SQLAlchemy engines or URLs.
engines = {}
for name in re.split(r',\s*', db_names):
    engines[name] = rec = {}
    if need_engine:
        rec['engine'] = engine_from_config(context.config.get_section(name),
                                prefix='sqlalchemy.')
    else:
        rec['url'] = context.config.get_section_option(name, "sqlalchemy.url")

# for the --sql use case, run migrations for each URL into
# individual files.
if not need_engine:
    for name, rec in engines.items():
        file_ = "%s.sql" % name
        sys.stderr.write("Writing output to %s\n" % file_)
        context.configure(
                    url=rec['url'],
                    output_buffer=file(file_, 'w')
                )
        context.run_migrations(engine=name)

# for the direct-to-DB use case, start a transaction on all
# engines, then run all migrations, then commit all transactions.
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