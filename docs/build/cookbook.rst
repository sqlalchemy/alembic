========
Cookbook
========

A collection of "How-Tos", highlighting various ways to extend
Alembic.

.. note::

    This is a new section where we hope to start cataloguing various "how-tos"
    we come up with based on user requests.  It is often the case that users
    will request a feature only to learn that simple customization can
    provide the same thing.   There's only one recipe at the moment but
    we hope to get more soon!

.. _building_uptodate:

Building an Up to Date Database from Scratch
=============================================

There's a theory of database migrations that says that the revisions in existence for a database should be
able to go from an entirely blank schema to the finished product, and back again.   Alembic can roll
this way.   Though we think it's kind of overkill, considering that SQLAlchemy itself can emit
the full CREATE statements for any given model using :meth:`~sqlalchemy.schema.MetaData.create_all`.   If you check out
a copy of an application, running this will give you the entire database in one shot, without the need
to run through all those migration files, which are instead tailored towards applying incremental
changes to an existing database.

Alembic can integrate with a :meth:`~sqlalchemy.schema.MetaData.create_all` script quite easily.  After running the
create operation, tell Alembic to create a new version table, and to stamp it with the most recent
revision (i.e. ``head``)::

    # inside of a "create the database" script, first create
    # tables:
    my_metadata.create_all(engine)

    # then, load the Alembic configuration and generate the
    # version table, "stamping" it with the most recent rev:
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("/path/to/yourapp/alembic.ini")
    command.stamp(alembic_cfg, "head")

When this approach is used, the application can generate the database using normal SQLAlchemy
techniques instead of iterating through hundreds of migration scripts.   Now, the purpose of the
migration scripts is relegated just to movement between versions on out-of-date databases, not
*new* databases.    You can now remove old migration files that are no longer represented
on any existing environments.

To prune old migration files, simply delete the files.   Then, in the earliest, still-remaining
migration file, set ``down_revision`` to ``None``::

    # replace this:
    #down_revision = '290696571ad2'

    # with this:
    down_revision = None

That file now becomes the "base" of the migration series.

Conditional Migration Elements
==============================

This example features the basic idea of a common need, that of affecting
how a migration runs based on command line switches.

The technique to use here is simple; within a migration script, inspect
the :meth:`.EnvironmentContext.get_x_argument` collection for any additional,
user-defined parameters.  Then take action based on the presence of those
arguments.

To make it such that the logic to inspect these flags is easy to use and
modify, we modify our ``script.py.mako`` template to make this feature
available in all new revision files:

.. code-block:: mako

    """${message}

    Revision ID: ${up_revision}
    Revises: ${down_revision}
    Create Date: ${create_date}

    """

    # revision identifiers, used by Alembic.
    revision = ${repr(up_revision)}
    down_revision = ${repr(down_revision)}

    from alembic import op
    import sqlalchemy as sa
    ${imports if imports else ""}

    from alembic import context


    def upgrade():
        schema_upgrades()
        if context.get_x_argument(as_dictionary=True).get('data', None):
            data_upgrades()

    def downgrade():
        if context.get_x_argument(as_dictionary=True).get('data', None):
            data_downgrades()
        schema_downgrades()

    def schema_upgrades():
        """schema upgrade migrations go here."""
        ${upgrades if upgrades else "pass"}

    def schema_downgrades():
        """schema downgrade migrations go here."""
        ${downgrades if downgrades else "pass"}

    def data_upgrades():
        """Add any optional data upgrade migrations here!"""
        pass

    def data_downgrades():
        """Add any optional data downgrade migrations here!"""
        pass

Now, when we create a new migration file, the ``data_upgrades()`` and ``data_downgrades()``
placeholders will be available, where we can add optional data migrations::

    """rev one

    Revision ID: 3ba2b522d10d
    Revises: None
    Create Date: 2014-03-04 18:05:36.992867

    """

    # revision identifiers, used by Alembic.
    revision = '3ba2b522d10d'
    down_revision = None

    from alembic import op
    import sqlalchemy as sa
    from sqlalchemy import String, Column
    from sqlalchemy.sql import table, column

    from alembic import context

    def upgrade():
        schema_upgrades()
        if context.get_x_argument(as_dictionary=True).get('data', None):
            data_upgrades()

    def downgrade():
        if context.get_x_argument(as_dictionary=True).get('data', None):
            data_downgrades()
        schema_downgrades()

    def schema_upgrades():
        """schema upgrade migrations go here."""
        op.create_table("my_table", Column('data', String))

    def schema_downgrades():
        """schema downgrade migrations go here."""
        op.drop_table("my_table")

    def data_upgrades():
        """Add any optional data upgrade migrations here!"""

        my_table = table('my_table',
            column('data', String),
        )

        op.bulk_insert(my_table,
            [
                {'data': 'data 1'},
                {'data': 'data 2'},
                {'data': 'data 3'},
            ]
        )

    def data_downgrades():
        """Add any optional data downgrade migrations here!"""

        op.execute("delete from my_table")

To invoke our migrations with data included, we use the ``-x`` flag::

    alembic -x data=true upgrade head

The :meth:`.EnvironmentContext.get_x_argument` is an easy way to support
new commandline options within environment and migration scripts.

