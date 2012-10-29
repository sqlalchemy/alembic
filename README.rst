Alembic is a new database migrations tool, written by the author
of `SQLAlchemy <http://www.sqlalchemy.org>`_.  A migrations tool
offers the following functionality:

* Can emit ALTER statements to a database in order to change
  the structure of tables and other constructs
* Provides a system whereby "migration scripts" may be constructed;
  each script indicates a particular series of steps that can "upgrade" a
  target database to a new version, and optionally a series of steps that can
  "downgrade" similarly, doing the same steps in reverse.
* Allows the scripts to execute in some sequential manner.

The goals of Alembic are:

* Very open ended and transparent configuration and operation.   A new
  Alembic environment is generated from a set of templates which is selected
  among a set of options when setup first occurs. The templates then deposit a
  series of scripts that define fully how database connectivity is established
  and how migration scripts are invoked; the migration scripts themselves are
  generated from a template within that series of scripts. The scripts can
  then be further customized to define exactly how databases will be
  interacted with and what structure new migration files should take.
* Full support for transactional DDL.   The default scripts ensure that all
  migrations occur within a transaction - for those databases which support
  this (Postgresql, Microsoft SQL Server), migrations can be tested with no
  need to manually undo changes upon failure.
* Minimalist script construction.  Basic operations like renaming
  tables/columns, adding/removing columns, changing column attributes can be
  performed through one line commands like alter_column(), rename_table(),
  add_constraint(). There is no need to recreate full SQLAlchemy Table
  structures for simple operations like these - the functions themselves
  generate minimalist schema structures behind the scenes to achieve the given
  DDL sequence.
* "auto generation" of migrations. While real world migrations are far more
  complex than what can be automatically determined, Alembic can still
  eliminate the initial grunt work in generating new migration directives
  from an altered schema.  The ``--autogenerate`` feature will inspect the
  current status of a database using SQLAlchemy's schema inspection
  capabilities, compare it to the current state of the database model as
  specified in Python, and generate a series of "candidate" migrations,
  rendering them into a new migration script as Python directives. The
  developer then edits the new file, adding additional directives and data
  migrations as needed, to produce a finished migration. Table and column
  level changes can be detected, with constraints and indexes to follow as
  well.
* Full support for migrations generated as SQL scripts.   Those of us who
  work in corporate environments know that direct access to DDL commands on a
  production database is a rare privilege, and DBAs want textual SQL scripts.
  Alembic's usage model and commands are oriented towards being able to run a
  series of migrations into a textual output file as easily as it runs them
  directly to a database. Care must be taken in this mode to not invoke other
  operations that rely upon in-memory SELECTs of rows - Alembic tries to
  provide helper constructs like bulk_insert() to help with data-oriented
  operations that are compatible with script-based DDL.
* Non-linear versioning.   Scripts are given UUID identifiers similarly
  to a DVCS, and the linkage of one script to the next is achieved via markers
  within the scripts themselves. Through this open-ended mechanism, branches
  containing other migration scripts can be merged - the linkages can be
  manually edited within the script files to create the new sequence.
* Provide a library of ALTER constructs that can be used by any SQLAlchemy
  application. The DDL constructs build upon SQLAlchemy's own DDLElement base
  and can be used standalone by any application or script.
* Don't break our necks over SQLite's inability to ALTER things.   SQLite
  has almost no support for table or column alteration, and this is likely
  intentional.   Alembic's design
  is kept simple by not contorting its core API around these limitations,
  understanding that SQLite is simply not intended to support schema
  changes.   While Alembic's architecture can support SQLite's workarounds, and
  we will support these features provided someone takes the initiative
  to implement and test, until the SQLite developers decide
  to provide a fully working version of ALTER, it's still vastly preferable
  to use Alembic, or any migrations tool, with databases that
  are designed to work under the assumption of in-place schema migrations
  taking place.

Documentation and status of Alembic is at http://readthedocs.org/docs/alembic/.

