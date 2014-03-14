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

pylons_config_file = ./development.ini

# that's it !