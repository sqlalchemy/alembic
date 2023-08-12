.. _batch_migrations:

Running "Batch" Migrations for SQLite and Other Databases
=========================================================

The SQLite database presents a challenge to migration tools
in that it has almost no support for the ALTER statement which
relational schema migrations rely upon.  The rationale for this stems from
philosophical and architectural concerns within SQLite, and they are unlikely
to be changed.

Migration tools are instead expected to produce copies of SQLite tables that
correspond to the new structure, transfer the data from the existing
table to the new one, then drop the old table.  For our purposes here
we'll call this **"move and copy"** workflow, and in order to accommodate it
in a way that is reasonably predictable, while also remaining compatible
with other databases, Alembic provides the **batch** operations context.

Within this context, a relational table is named, and then a series of
mutation operations to that table alone are specified within
the block.  When the context is complete, a process begins whereby the
"move and copy" procedure begins; the existing table structure is reflected
from the database, a new version of this table is created with the given
changes, data is copied from the
old table to the new table using "INSERT from SELECT", and finally the old
table is dropped and the new one renamed to the original name.

The :meth:`.Operations.batch_alter_table` method provides the gateway to this
process::

    with op.batch_alter_table("some_table") as batch_op:
        batch_op.add_column(Column('foo', Integer))
        batch_op.drop_column('bar')

When the above directives are invoked within a migration script, on a
SQLite backend we would see SQL like:

.. sourcecode:: sql

    CREATE TABLE _alembic_batch_temp (
      id INTEGER NOT NULL,
      foo INTEGER,
      PRIMARY KEY (id)
    );
    INSERT INTO _alembic_batch_temp (id) SELECT some_table.id FROM some_table;
    DROP TABLE some_table;
    ALTER TABLE _alembic_batch_temp RENAME TO some_table;

On other backends, we'd see the usual ``ALTER`` statements done as though
there were no batch directive - the batch context by default only does
the "move and copy" process if SQLite is in use, and if there are
migration directives other than :meth:`.Operations.add_column` present,
which is the one kind of column-level ALTER statement that SQLite supports.
:meth:`.Operations.batch_alter_table` can be configured
to run "move and copy" unconditionally in all cases, including on databases
other than SQLite; more on this is below.

.. _batch_controlling_table_reflection:

Controlling Table Reflection
----------------------------

The :class:`~sqlalchemy.schema.Table` object that is reflected when
"move and copy" proceeds is performed using the standard ``autoload=True``
approach.  This call can be affected using the
:paramref:`~.Operations.batch_alter_table.reflect_args` and
:paramref:`~.Operations.batch_alter_table.reflect_kwargs` arguments.
For example, to override a :class:`~sqlalchemy.schema.Column` within
the reflection process such that a :class:`~sqlalchemy.types.Boolean`
object is reflected with the ``create_constraint`` flag set to ``False``::

    with self.op.batch_alter_table(
        "bar",
        reflect_args=[Column('flag', Boolean(create_constraint=False))]
    ) as batch_op:
        batch_op.alter_column(
            'flag', new_column_name='bflag', existing_type=Boolean)

Another use case, add a listener to the :class:`~sqlalchemy.schema.Table`
as it is reflected so that special logic can be applied to columns or
types, using the :meth:`~sqlalchemy.events.DDLEvents.column_reflect` event::

    def listen_for_reflect(inspector, table, column_info):
        "correct an ENUM type"
        if column_info['name'] == 'my_enum':
            column_info['type'] = Enum('a', 'b', 'c')

    with self.op.batch_alter_table(
        "bar",
        reflect_kwargs=dict(
            listeners=[
                ('column_reflect', listen_for_reflect)
            ]
        )
    ) as batch_op:
        batch_op.alter_column(
            'flag', new_column_name='bflag', existing_type=Boolean)

The reflection process may also be bypassed entirely by sending a
pre-fabricated :class:`~sqlalchemy.schema.Table` object; see
:ref:`batch_offline_mode` for an example.

.. _sqlite_batch_constraints:

Dealing with Constraints
------------------------

There are a variety of issues when using "batch" mode with constraints,
such as FOREIGN KEY, CHECK and UNIQUE constraints.  This section
will attempt to detail many of these scenarios.

.. _dropping_sqlite_foreign_keys:

Dropping Unnamed or Named Foreign Key Constraints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SQLite, unlike any other database, allows constraints to exist in the
database that have no identifying name.  On all other backends, the
target database will always generate some kind of name, if one is not
given.

The challenge this represents is that an unnamed constraint can't
by itself be targeted by the :meth:`.BatchOperations.drop_constraint` method.
An unnamed FOREIGN KEY constraint is implicit whenever the
:class:`~sqlalchemy.schema.ForeignKey`
or :class:`~sqlalchemy.schema.ForeignKeyConstraint` objects are used without
passing them a name.  Only on SQLite will these constraints remain entirely
unnamed when they are created on the target database; an automatically generated
name will be assigned in the case of all other database backends.

Within the scope of batch mode, this presents the issue that the
:meth:`.BatchOperations.drop_constraint` method requires a constraint name
in order to target the correct constraint.

In order to overcome this, the :meth:`.Operations.batch_alter_table` method supports a
:paramref:`~.Operations.batch_alter_table.naming_convention` argument, so that
all reflected constraints, including foreign keys that are unnamed may be
given a name, as described in :ref:`autogen_naming_conventions`. 
Usage is as follows::

    naming_convention = {
        "fk":
        "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    with self.op.batch_alter_table(
            "bar", naming_convention=naming_convention) as batch_op:
        batch_op.drop_constraint(
            "fk_bar_foo_id_foo", type_="foreignkey")

Note that the naming convention feature requires at least
**SQLAlchemy 0.9.4** for support.

.. _batch_schematype_constraints:

Changing the Type of Boolean, Enum and other implicit CHECK datatypes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The SQLAlchemy types :class:`~sqlalchemy.types.Boolean` and
:class:`~sqlalchemy.types.Enum` are part of a category of types known as
"schema" types; this style of type creates other structures along with the
type itself, most commonly (but not always) a CHECK constraint.

Alembic handles dropping and creating the CHECK constraints here automatically,
including in the case of batch mode.  When changing the type of an existing
column, what's necessary is that the existing type be specified fully::

  with self.op.batch_alter_table("some_table") as batch_op:
      batch_op.alter_column(
          'q', type_=Integer,
          existing_type=Boolean(create_constraint=True, constraint_name="ck1"))

When dropping a column that includes a named CHECK constraint, as of Alembic
1.7 this named constraint must also be provided using a similar form, as there
is no ability for Alembic to otherwise link this reflected CHECK constraint as
belonging to a particular column::

    with self.op.batch_alter_table("some_table") as batch_op:
        batch_op.drop_column(
            'q',
            existing_type=Boolean(create_constraint=True, constraint_name="ck1"))
        )

.. versionchanged:: 1.7  The :meth:`.BatchOperations.drop_column` operation can
   accept an ``existing_type`` directive where a "schema type" such as
   :class:`~sqlalchemy.types.Boolean` and :class:`~sqlalchemy.types.Enum` may
   be specified such that an associated named constraint can be removed.

.. _batch_check_constraints:

Including CHECK constraints
^^^^^^^^^^^^^^^^^^^^^^^^^^^

As of Alembic 1.7, **named** CHECK constraints are automatically included
in batch mode, as modern SQLAlchemy versions are capable of reflecting these
constraints like any other constraint.

Note that when dropping or renaming a column that is mentioned in a named
CHECK constraint, this CHECK constraint must be explicitly dropped first,
as Alembic has no means of linking a reflected CHECK constraint to that
column.  Supposing column ``q`` of ``some_table`` were mentioned in a CHECK
constraint named ``ck1``.  In order to drop this column, we have to drop
the check constraint also::

    with self.op.batch_alter_table("some_table") as batch_op:
        batch_op.drop_constraint("ck1", type_="check")
        batch_op.drop_column('q')

.. versionchanged:: 1.7  Named CHECK constraints participate in batch mode
   in the same way as any other kind of constraint. This requires that column
   drops or renames now include explicit directives to drop an existing named
   constraint which refers to this column, as it will otherwise not be
   automatically detected as being associated with that particular column.

   Unnamed CHECK constraints continue to be silently omitted from the table
   recreate operation.

For **unnamed** CHECK constraints, these are still not automatically included
as part of the batch process.  Note that this limitation **includes** the CHECK
constraints generated by the
:class:`~sqlalchemy.types.Boolean` or :class:`~sqlalchemy.types.Enum`
datatypes, which up through SQLAlchemy 1.3 would generate CHECK constraints
automatically and cannot be tracked to the reflected table, assuming they are
generated in an unnamed way.

Unnamed constraints can be stated explicitly if they are to be included in the
recreated table::

    with op.batch_alter_table("some_table", table_args=[
          CheckConstraint('x > 5')
      ]) as batch_op:
        batch_op.add_column(Column('foo', Integer))
        batch_op.drop_column('bar')

The above step needs only be taken for CHECK constraints that are explicitly stated
as part of the table definition.

For CHECK constraints that are generated by datatypes such as
:class:`~sqlalchemy.types.Boolean` or :class:`~sqlalchemy.types.Enum`, the type
objects themselves **must be named** in order for their CHECK constraints to be
included in the batch process.   Boolean and Enum datatypes that do not
have the ``.name`` attribute set will **not** have CHECK constraints
regenerated.  This name can be set by specifying the ``.name`` parameter
or by using a named Python ``Enum`` object as the source of enumeration.

Dealing with Referencing Foreign Keys
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is important to note that batch table operations **do not work** with
foreign keys that enforce referential integrity.  This because the
target table is dropped; if foreign keys refer to it, this will raise
an error.   On SQLite, whether or not foreign keys actually enforce is
controlled by the ``PRAGMA FOREIGN KEYS`` pragma; this pragma, if in use,
must be disabled when the workflow mode proceeds.   When the operation is
complete, the batch-migrated table will have the same name
that it started with, so those referring foreign keys will again
refer to this table.

A special case is dealing with self-referring foreign keys.  Here,
Alembic takes a special step of recreating the self-referring foreign key
as referring to the original table name, rather than at the "temp" table,
so that like in the case of other foreign key constraints, when the table
is renamed to its original name, the foreign key
again references the correct table.   This operation only works when
referential integrity is disabled, consistent with the same requirement
for referring foreign keys from other tables.

When SQLite's ``PRAGMA FOREIGN KEYS`` mode is turned on, it does provide
the service that foreign key constraints, including self-referential, will
automatically be modified to point to their table across table renames,
however this mode prevents the target table from being dropped as is required
by a batch migration.  Therefore it may be necessary to manipulate the
``PRAGMA FOREIGN KEYS`` setting if a migration seeks to rename a table vs.
batch migrate it.

.. _batch_offline_mode:

Working in Offline Mode
-----------------------

In the preceding sections, we've seen how much of an emphasis the
"move and copy" process has on using reflection in order to know the
structure of the table that is to be copied.  This means that in the typical
case, "online" mode, where a live database connection is present so that
:meth:`.Operations.batch_alter_table` can reflect the table from the
database, is required; the ``--sql`` flag **cannot** be used without extra
steps.

To support offline mode, the system must work without table reflection
present, which means the full table as it intends to be created must be
passed to :meth:`.Operations.batch_alter_table` using
:paramref:`~.Operations.batch_alter_table.copy_from`::

    meta = MetaData()
    some_table = Table(
        'some_table', meta,
        Column('id', Integer, primary_key=True),
        Column('bar', String(50))
    )

    with op.batch_alter_table("some_table", copy_from=some_table) as batch_op:
        batch_op.add_column(Column('foo', Integer))
        batch_op.drop_column('bar')

The above use pattern is pretty tedious and quite far off from Alembic's
preferred style of working; however, if one needs to do SQLite-compatible
"move and copy" migrations and need them to generate flat SQL files in
"offline" mode, there's not much alternative.


Batch mode with Autogenerate
----------------------------

The syntax of batch mode is essentially that :meth:`.Operations.batch_alter_table`
is used to enter a batch block, and the returned :class:`.BatchOperations` context
works just like the regular :class:`.Operations` context, except that
the "table name" and "schema name" arguments are omitted.

To support rendering of migration commands in batch mode for autogenerate,
configure the :paramref:`.EnvironmentContext.configure.render_as_batch`
flag in ``env.py``::

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True
    )

Autogenerate will now generate along the lines of::

    def upgrade():
        ### commands auto generated by Alembic - please adjust! ###
        with op.batch_alter_table('address', schema=None) as batch_op:
            batch_op.add_column(sa.Column('street', sa.String(length=50), nullable=True))

This mode is safe to use in all cases, as the :meth:`.Operations.batch_alter_table`
directive by default only takes place for SQLite; other backends will
behave just as they normally do in the absence of the batch directives.

Note that autogenerate support does not include "offline" mode, where
the :paramref:`.Operations.batch_alter_table.copy_from` parameter is used.
The table definition here would need to be entered into migration files
manually if this is needed.

Batch mode with databases other than SQLite
--------------------------------------------

There's an odd use case some shops have, where the "move and copy" style
of migration is useful in some cases for databases that do already support
ALTER.   There's some cases where an ALTER operation may block access to the
table for a long time, which might not be acceptable.  "move and copy" can
be made to work on other backends, though with a few extra caveats.

The batch mode directive will run the "recreate" system regardless of
backend if the flag ``recreate='always'`` is passed::

    with op.batch_alter_table("some_table", recreate='always') as batch_op:
        batch_op.add_column(Column('foo', Integer))

The issues that arise in this mode are mostly to do with constraints.
Databases such as Postgresql and MySQL with InnoDB will enforce referential
integrity (e.g. via foreign keys) in all cases.   Unlike SQLite, it's not
as simple to turn off referential integrity across the board (nor would it
be desirable).    Since a new table is replacing the old one, existing
foreign key constraints which refer to the target table will need to be
unconditionally dropped before the batch operation, and re-created to refer
to the new table afterwards.  Batch mode currently does not provide any
automation for this.

The Postgresql database and possibly others also have the behavior such
that when the new table is created, a naming conflict occurs with the
named constraints of the new table, in that they match those of the old
table, and on Postgresql, these names need to be unique across all tables.
The Postgresql dialect will therefore emit a "DROP CONSTRAINT" directive
for all constraints on the old table before the new one is created; this is
"safe" in case of a failed operation because Postgresql also supports
transactional DDL.

Note that also as is the case with SQLite, CHECK constraints need to be
moved over between old and new table manually using the
:paramref:`.Operations.batch_alter_table.table_args` parameter.
