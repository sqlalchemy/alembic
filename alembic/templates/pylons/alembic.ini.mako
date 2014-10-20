# a Pylons configuration.

[alembic]
# path to migration scripts
script_location = ${script_location}

# template used to generate migration files
# file_template = %%(rev)s_%%(slug)s

# max length of characters to apply to the
# "slug" field
#truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

pylons_config_file = ./development.ini

# that's it !