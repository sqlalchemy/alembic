
==========
Changelog
==========

.. changelog::
    :version: 0.8.8

    .. change::
       :tags: autogenerate

       The imports in the default script.py.mako are now at the top
       so that flake8 editors don't complain by default.  PR courtesy
       Guilherme Mansur.

    .. change::
      :tags: feature, operations, postgresql
      :tickets: 292

      Added support for the USING clause to the ALTER COLUMN operation
      for Postgresql.  Support is via the
      :paramref:`.op.alter_column.postgresql_using`
      parameter.  Pull request courtesy Frazer McLean.

    .. change:
      :tags: feature, autogenerate

      Autogenerate with type comparison enabled will pick up on the timezone
      setting changing between DateTime types.   Pull request courtesy
      David Szotten.

.. changelog::
    :version: 0.8.7
    :released: July 26, 2016

    .. change::
      :tags: bug, versioning
      :tickets: 336

      Fixed bug where upgrading to the head of a branch which is already
      present would fail, only if that head were also the dependency
      of a different branch that is also upgraded, as the revision system
      would see this as trying to go in the wrong direction.   The check
      here has been refined to distinguish between same-branch revisions
      out of order vs. movement along sibling branches.

    .. change::
      :tags: bug, versioning
      :tickets: 379

      Adjusted the version traversal on downgrade
      such that we can downgrade to a version that is a dependency for
      a version in a different branch, *without* needing to remove that
      dependent version as well.  Previously, the target version would be
      seen as a "merge point" for it's normal up-revision as well as the
      dependency.  This integrates with the changes for :ticket:`377`
      and :ticket:`378` to improve treatment of branches with dependencies
      overall.

    .. change::
      :tags: bug, versioning
      :tickets: 377

      Fixed bug where a downgrade to a version that is also a dependency
      to a different branch would fail, as the system attempted to treat
      this as an "unmerge" of a merge point, when in fact it doesn't have
      the other side of the merge point available for update.

    .. change::
      :tags: bug, versioning
      :tickets: 378

      Fixed bug where the "alembic current" command wouldn't show a revision
      as a current head if it were also a dependency of a version in a
      different branch that's also applied.   Extra logic is added to
      extract "implied" versions of different branches from the top-level
      versions listed in the alembic_version table.

    .. change::
      :tags: bug, versioning

      Fixed bug where a repr() or str() of a Script object would fail
      if the script had multiple dependencies.

    .. change::
      :tags: bug, autogenerate

      Fixed bug in autogen where if the DB connection sends the default
      schema as "None", this "None" would be removed from the list of
      schemas to check if include_schemas were set.  This could possibly
      impact using include_schemas with SQLite.

    .. change::
      :tags: bug, batch

      Small adjustment made to the batch handling for reflected CHECK
      constraints to accommodate for SQLAlchemy 1.1 now reflecting these.
      Batch mode still does not support CHECK constraints from the reflected
      table as these can't be easily differentiated from the ones created
      by types such as Boolean.

.. changelog::
    :version: 0.8.6
    :released: April 14, 2016

    .. change::
      :tags: bug, commands
      :tickets: 367

      Errors which occur within the Mako render step are now intercepted
      and raised as CommandErrors like other failure cases; the Mako
      exception itself is written using template-line formatting to
      a temporary file which is named in the exception message.

    .. change::
      :tags: bug, postgresql
      :tickets: 365

      Added a fix to Postgresql server default comparison which first checks
      if the text of the default is identical to the original, before attempting
      to actually run the default.  This accomodates for default-generation
      functions that generate a new value each time such as a uuid function.

    .. change::
      :tags: bug, batch
      :tickets: 361
      :pullreq: bitbucket:55

      Fixed bug introduced by the fix for :ticket:`338` in version 0.8.4
      where a server default could no longer be dropped in batch mode.
      Pull request courtesy Martin Domke.

    .. change::
      :tags: bug, batch, mssql
      :pullreq: bitbucket:53

      Fixed bug where SQL Server arguments for drop_column() would not
      be propagated when running under a batch block.  Pull request
      courtesy Michal Petrucha.

.. changelog::
    :version: 0.8.5
    :released: March 9, 2016

    .. change::
      :tags: bug, autogenerate
      :tickets: 335
      :pullreq: bitbucket:49

      Fixed bug where the columns rendered in a ``PrimaryKeyConstraint``
      in autogenerate would inappropriately render the "key" of the
      column, not the name.  Pull request courtesy Jesse Dhillon.

    .. change::
      :tags: bug, batch
      :tickets: 354

      Repaired batch migration support for "schema" types which generate
      constraints, in particular the ``Boolean`` datatype which generates
      a CHECK constraint.  Previously, an alter column operation with this
      type would fail to correctly accommodate for the CHECK constraint
      on change both from and to this type.  In the former case the operation
      would fail entirely, in the latter, the CHECK constraint would
      not get generated.  Both of these issues are repaired.

    .. change::
      :tags: bug, mysql
      :tickets: 355

      Changing a schema type such as ``Boolean`` to a non-schema type would
      emit a drop constraint operation which emits ``NotImplementedError`` for
      the MySQL dialect.  This drop constraint operation is now skipped when
      the constraint originates from a schema type.

.. changelog::
    :version: 0.8.4
    :released: December 15, 2015

    .. change::
      :tags: feature, versioning
      :pullreq: bitbucket:51

      A major improvement to the hash id generation function, which for some
      reason used an awkward arithmetic formula against uuid4() that produced
      values that tended to start with the digits 1-4.  Replaced with a
      simple substring approach which provides an even distribution.  Pull
      request courtesy Antti Haapala.

    .. change::
      :tags: feature, autogenerate
      :pullreq: github:20

      Added an autogenerate renderer for the :class:`.ExecuteSQLOp` operation
      object; only renders if given a plain SQL string, otherwise raises
      NotImplementedError.  Can be of help with custom autogenerate
      sequences that includes straight SQL execution.  Pull request courtesy
      Jacob Magnusson.

    .. change::
      :tags: bug, batch
      :tickets: 345

      Batch mode generates a FOREIGN KEY constraint that is self-referential
      using the ultimate table name, rather than ``_alembic_batch_temp``.
      When the table is renamed from ``_alembic_batch_temp`` back to the
      original name, the FK now points to the right name.  This
      will **not** work if referential integrity is being enforced (eg. SQLite
      "PRAGMA FOREIGN_KEYS=ON") since the original table is dropped and
      the new table then renamed to that name, however this is now consistent
      with how foreign key constraints on **other** tables already operate
      with batch mode; these don't support batch mode if referential integrity
      is enabled in any case.

    .. change::
      :tags: bug, autogenerate
      :tickets: 341

      Added a type-level comparator that distinguishes :class:`.Integer`,
      :class:`.BigInteger`, and :class:`.SmallInteger` types and
      dialect-specific types; these all have "Integer" affinity so previously
      all compared as the same.

    .. change::
      :tags: bug, batch
      :tickets: 338

      Fixed bug where the ``server_default`` parameter of ``alter_column()``
      would not function correctly in batch mode.

    .. change::
      :tags: bug, autogenerate
      :tickets: 337

      Adjusted the rendering for index expressions such that a :class:`.Column`
      object present in the source :class:`.Index` will not be rendered
      as table-qualified; e.g. the column name will be rendered alone.
      Table-qualified names here were failing on systems such as Postgresql.

.. changelog::
    :version: 0.8.3
    :released: October 16, 2015

    .. change::
      :tags: bug, autogenerate
      :tickets: 332

      Fixed an 0.8 regression whereby the "imports" dictionary member of
      the autogen context was removed; this collection is documented in the
      "render custom type" documentation as a place to add new imports.
      The member is now known as
      :attr:`.AutogenContext.imports` and the documentation is repaired.

    .. change::
      :tags: bug, batch
      :tickets: 333

      Fixed bug in batch mode where a table that had pre-existing indexes
      would create the same index on the new table with the same name,
      which on SQLite produces a naming conflict as index names are in a
      global namespace on that backend.   Batch mode now defers the production
      of both existing and new indexes until after the entire table transfer
      operation is complete, which also means those indexes no longer take
      effect during the INSERT from SELECT section as well; the indexes
      are applied in a single step afterwards.

    .. change::
      :tags: bug, tests
      :pullreq: bitbucket:47

      Added "pytest-xdist" as a tox dependency, so that the -n flag
      in the test command works if this is not already installed.
      Pull request courtesy Julien Danjou.

    .. change::
      :tags: bug, autogenerate, postgresql
      :tickets: 324

      Fixed issue in PG server default comparison where model-side defaults
      configured with Python unicode literals would leak the "u" character
      from a ``repr()`` into the SQL used for comparison, creating an invalid
      SQL expression, as the server-side comparison feature in PG currently
      repurposes the autogenerate Python rendering feature to get a quoted
      version of a plain string default.


.. changelog::
    :version: 0.8.2
    :released: August 25, 2015

    .. change::
      :tags: bug, autogenerate
      :tickets: 321

      Added workaround in new foreign key option detection feature for
      MySQL's consideration of the "RESTRICT" option being the default,
      for which no value is reported from the database; the MySQL impl now
      corrects for when the model reports RESTRICT but the database reports
      nothing.   A similar rule is in the default FK comparison to accommodate
      for the default "NO ACTION" setting being present in the model but not
      necessarily reported by the database, or vice versa.

.. changelog::
    :version: 0.8.1
    :released: August 22, 2015

    .. change::
      :tags: feature, autogenerate

      A custom :paramref:`.EnvironmentContext.configure.process_revision_directives`
      hook can now generate op directives within the :class:`.UpgradeOps`
      and :class:`.DowngradeOps` containers that will be generated as Python
      code even when the ``--autogenerate`` flag is False; provided that
      ``revision_environment=True``, the full render operation will be run
      even in "offline" mode.

    .. change::
      :tags: bug, autogenerate

      Repaired the render operation for the :class:`.ops.AlterColumnOp` object
      to succeed when the "existing_type" field was not present.

    .. change::
      :tags: bug, autogenerate
      :tickets: 318

      Fixed a regression 0.8 whereby the "multidb" environment template
      failed to produce independent migration script segments for the
      output template.  This was due to the reorganization of the script
      rendering system for 0.8.  To accommodate this change, the
      :class:`.MigrationScript` structure will in the case of multiple
      calls to :meth:`.MigrationContext.run_migrations` produce lists
      for the :attr:`.MigrationScript.upgrade_ops` and
      :attr:`.MigrationScript.downgrade_ops` attributes; each :class:`.UpgradeOps`
      and :class:`.DowngradeOps` instance keeps track of its own
      ``upgrade_token`` and ``downgrade_token``, and each are rendered
      individually.

      .. seealso::

        :ref:`autogen_customizing_multiengine_revision` - additional detail
        on the workings of the
        :paramref:`.EnvironmentContext.configure.process_revision_directives`
        parameter when multiple calls to :meth:`.MigrationContext.run_migrations`
        are made.


    .. change::
      :tags: feature, autogenerate
      :tickets: 317

      Implemented support for autogenerate detection of changes in the
      ``ondelete``, ``onupdate``, ``initially`` and ``deferrable``
      attributes of :class:`.ForeignKeyConstraint` objects on
      SQLAlchemy backends that support these on reflection
      (as of SQLAlchemy 1.0.8 currently Postgresql for all four,
      MySQL for ``ondelete`` and  ``onupdate`` only).   A constraint object
      that modifies these values will be reported as a "diff" and come out
      as a drop/create of the constraint with the modified values.
      The fields are ignored for backends which don't reflect these
      attributes (as of SQLA 1.0.8 this includes SQLite, Oracle, SQL Server,
      others).

.. changelog::
    :version: 0.8.0
    :released: August 12, 2015

    .. change::
      :tags: bug, batch
      :tickets: 315

      Fixed bug in batch mode where the ``batch_op.create_foreign_key()``
      directive would be incorrectly rendered with the source table and
      schema names in the argument list.

    .. change::
      :tags: feature, commands
      :pullreq: bitbucket:46

      Added new command ``alembic edit``.  This command takes the same
      arguments as ``alembic show``, however runs the target script
      file within $EDITOR.  Makes use of the ``python-editor`` library
      in order to facilitate the handling of $EDITOR with reasonable
      default behaviors across platforms.  Pull request courtesy
      Michel Albert.

    .. change::
      :tags: feature, commands
      :tickets: 311

      Added new multiple-capable argument ``--depends-on`` to the
      ``alembic revision`` command, allowing ``depends_on`` to be
      established at the command line level rather than having to edit
      the file after the fact. ``depends_on`` identifiers may also be
      specified as branch names at the command line or directly within
      the migration file. The values may be specified as partial
      revision numbers from the command line which will be resolved to
      full revision numbers in the output file.

    .. change::
      :tags: change, operations

      A range of positional argument names have been changed to be
      clearer and more consistent across methods within the
      :class:`.Operations` namespace.   The most prevalent form of name change
      is that the descriptive names ``constraint_name`` and ``table_name``
      are now used where previously the name ``name`` would be used.
      This is in support of the newly modularized and extensible system of
      operation objects in :mod:`alembic.operations.ops`.
      An argument translation layer is in place
      across the ``alembic.op`` namespace that will ensure that named
      argument calling styles that use the old names will continue to
      function by transparently translating to the new names,
      also emitting a warning.   This, along with the fact that these
      arguments are positional in any case and aren't normally
      passed with an explicit name, should ensure that the
      overwhelming majority of applications should be unaffected by this
      change.   The *only* applications that are impacted are those that:

      1. use the :class:`.Operations` object directly in some way, rather
         than calling upon the ``alembic.op`` namespace, and

      2. invoke the methods on :class:`.Operations` using named keyword
         arguments for positional arguments like ``table_name``,
         ``constraint_name``, etc., which commonly were named ``name``
         as of 0.7.6.

      3. any application that is using named keyword arguments in place
         of positional argument for the recently added
         :class:`.BatchOperations` object may also be affected.

      The naming changes are documented as "versionchanged" for 0.8.0:

      * :meth:`.BatchOperations.create_check_constraint`
      * :meth:`.BatchOperations.create_foreign_key`
      * :meth:`.BatchOperations.create_index`
      * :meth:`.BatchOperations.create_unique_constraint`
      * :meth:`.BatchOperations.drop_constraint`
      * :meth:`.BatchOperations.drop_index`
      * :meth:`.Operations.create_check_constraint`
      * :meth:`.Operations.create_foreign_key`
      * :meth:`.Operations.create_primary_key`
      * :meth:`.Operations.create_index`
      * :meth:`.Operations.create_table`
      * :meth:`.Operations.create_unique_constraint`
      * :meth:`.Operations.drop_constraint`
      * :meth:`.Operations.drop_index`
      * :meth:`.Operations.drop_table`


    .. change::
      :tags: feature, tests

      The default test runner via "python setup.py test" is now py.test.
      nose still works via run_tests.py.

    .. change::
      :tags: feature, operations
      :tickets: 302

      The internal system for Alembic operations has been reworked to now
      build upon an extensible system of operation objects.  New operations
      can be added to the ``op.`` namespace, including that they are
      available in custom autogenerate schemes.

      .. seealso::

          :ref:`operation_plugins`

    .. change::
      :tags: feature, autogenerate
      :tickets: 301, 306

      The internal system for autogenerate been reworked to build upon
      the extensible system of operation objects present in
      :ticket:`302`.  As part of this change, autogenerate now produces
      a full object graph representing a list of migration scripts to
      be written as well as operation objects that will render all the
      Python code within them; a new hook
      :paramref:`.EnvironmentContext.configure.process_revision_directives`
      allows end-user code to fully customize what autogenerate will do,
      including not just full manipulation of the Python steps to take
      but also what file or files will be written and where.  Additionally,
      autogenerate is now extensible as far as database objects compared
      and rendered into scripts; any new operation directive can also be
      registered into a series of hooks that allow custom database/model
      comparison functions to run as well as to render new operation
      directives into autogenerate scripts.

      .. seealso::

        :ref:`alembic.autogenerate.toplevel`

    .. change::
      :tags: bug, versioning
      :tickets: 314

      Fixed bug where in the erroneous case that alembic_version contains
      duplicate revisions, some commands would fail to process the
      version history correctly and end up with a KeyError.   The fix
      allows the versioning logic to proceed, however a clear error is
      emitted later when attempting to update the alembic_version table.

.. changelog::
    :version: 0.7.7
    :released: July 22, 2015

    .. change::
      :tags: bug, versioning
      :tickets: 310

      Fixed critical issue where a complex series of branches/merges would
      bog down the iteration algorithm working over redundant nodes for
      millions of cycles.   An internal adjustment has been
      made so that duplicate nodes are skipped within this iteration.

    .. change::
      :tags: feature, batch
      :tickets: 305

      Implemented support for :meth:`.BatchOperations.create_primary_key`
      and :meth:`.BatchOperations.create_check_constraint`. Additionally,
      table keyword arguments are copied from the original reflected table,
      such as the "mysql_engine" keyword argument.

    .. change::
      :tags: bug, environment
      :tickets: 300

      The :meth:`.MigrationContext.stamp` method, added as part of the
      versioning refactor in 0.7 as a more granular version of
      :func:`.command.stamp`, now includes the "create the alembic_version
      table if not present" step in the same way as the command version,
      which was previously omitted.

    .. change::
      :tags: bug, autogenerate
      :tickets: 298

      Fixed bug where foreign key options including "onupdate",
      "ondelete" would not render within the ``op.create_foreign_key()``
      directive, even though they render within a full
      ``ForeignKeyConstraint`` directive.

    .. change::
      :tags: bug, tests

      Repaired warnings that occur when running unit tests against
      SQLAlchemy 1.0.5 or greater involving the "legacy_schema_aliasing"
      flag.

.. changelog::
    :version: 0.7.6
    :released: May 5, 2015

    .. change::
      :tags: feature, versioning
      :tickets: 297

      Fixed bug where the case of multiple mergepoints that all
      have the identical set of ancestor revisions would fail to be
      upgradable, producing an assertion failure.   Merge points were
      previously assumed to always require at least an UPDATE in
      alembic_revision from one of the previous revs to the new one,
      however in this case, if one of the mergepoints has already
      been reached, the remaining mergepoints have no row to UPDATE therefore
      they must do an INSERT of their target version.

    .. change::
      :tags: feature, autogenerate
      :tickets: 296

      Added support for type comparison functions to be not just per
      environment, but also present on the custom types themselves, by
      supplying a method ``compare_against_backend``.
      Added a new documentation section :ref:`compare_types` describing
      type comparison fully.

    .. change::
      :tags: feature, operations
      :tickets: 255

      Added a new option
      :paramref:`.EnvironmentContext.configure.literal_binds`, which
      will pass the ``literal_binds`` flag into the compilation of SQL
      constructs when using "offline" mode.  This has the effect that
      SQL objects like inserts, updates, deletes as well as textual
      statements sent using ``text()`` will be compiled such that the dialect
      will attempt to render literal values "inline" automatically.
      Only a subset of types is typically supported; the
      :meth:`.Operations.inline_literal` construct remains as the construct
      used to force a specific literal representation of a value.
      The :paramref:`.EnvironmentContext.configure.literal_binds` flag
      is added to the "offline" section of the ``env.py`` files generated
      in new environments.

    .. change::
      :tags: bug, batch
      :tickets: 289

      Fully implemented the
      :paramref:`~.Operations.batch_alter_table.copy_from` parameter for
      batch mode, which previously was not functioning.  This allows
      "batch mode" to be usable in conjunction with ``--sql``.

    .. change::
      :tags: bug, batch
      :tickets: 287

      Repaired support for the :meth:`.BatchOperations.create_index`
      directive, which was mis-named internally such that the operation
      within a batch context could not proceed.   The create index
      operation will proceed as part of a larger "batch table recreate"
      operation only if
      :paramref:`~.Operations.batch_alter_table.recreate` is set to
      "always", or if the batch operation includes other instructions that
      require a table recreate.


.. changelog::
    :version: 0.7.5
    :released: March 19, 2015

    .. change::
      :tags: bug, autogenerate
      :tickets: 266
      :pullreq: bitbucket:39

      The ``--autogenerate`` option is not valid when used in conjunction
      with "offline" mode, e.g. ``--sql``.  This now raises a ``CommandError``,
      rather than failing more deeply later on.  Pull request courtesy
      Johannes Erdfelt.

    .. change::
      :tags: bug, operations, mssql
      :tickets: 284

      Fixed bug where the mssql DROP COLUMN directive failed to include
      modifiers such as "schema" when emitting the DDL.

    .. change::
      :tags: bug, autogenerate, postgresql
      :tickets: 282

      Postgresql "functional" indexes are necessarily skipped from the
      autogenerate process, as the SQLAlchemy backend currently does not
      support reflection of these structures.   A warning is emitted
      both from the SQLAlchemy backend as well as from the Alembic
      backend for Postgresql when such an index is detected.

    .. change::
      :tags: bug, autogenerate, mysql
      :tickets: 276

      Fixed bug where MySQL backend would report dropped unique indexes
      and/or constraints as both at the same time.  This is because
      MySQL doesn't actually have a "unique constraint" construct that
      reports differently than a "unique index", so it is present in both
      lists.  The net effect though is that the MySQL backend will report
      a dropped unique index/constraint as an index in cases where the object
      was first created as a unique constraint, if no other information
      is available to make the decision.  This differs from other backends
      like Postgresql which can report on unique constraints and
      unique indexes separately.

    .. change::
      :tags: bug, commands
      :tickets: 269

      Fixed bug where using a partial revision identifier as the
      "starting revision" in ``--sql`` mode in a downgrade operation
      would fail to resolve properly.

      As a side effect of this change, the
      :meth:`.EnvironmentContext.get_starting_revision_argument`
      method will return the "starting" revision in its originally-
      given "partial" form in all cases, whereas previously when
      running within the :meth:`.command.stamp` command, it would have
      been resolved to a full number before passing it to the
      :class:`.EnvironmentContext`.  The resolution of this value to
      a real revision number has basically been moved to a more fundamental
      level within the offline migration process.

    .. change::
      :tags: feature, commands

      Added a new feature :attr:`.Config.attributes`, to help with the use
      case of sharing state such as engines and connections on the outside
      with a series of Alembic API calls; also added a new cookbook section
      to describe this simple but pretty important use case.

      .. seealso::

          :ref:`connection_sharing`

    .. change::
      :tags: feature, environment

      The format of the default ``env.py`` script has been refined a bit;
      it now uses context managers not only for the scope of the transaction,
      but also for connectivity from the starting engine.  The engine is also
      now called a "connectable" in support of the use case of an external
      connection being passed in.

    .. change::
      :tags: feature, versioning
      :tickets: 267

      Added support for "alembic stamp" to work when given "heads" as an
      argument, when multiple heads are present.

.. changelog::
    :version: 0.7.4
    :released: January 12, 2015

    .. change::
      :tags: bug, autogenerate, postgresql
      :tickets: 241
      :pullreq: bitbucket:37

      Repaired issue where a server default specified without ``text()``
      that represented a numeric or floating point (e.g. with decimal places)
      value would fail in the Postgresql-specific check for "compare server
      default"; as PG accepts the value with quotes in the table specification,
      it's still valid.  Pull request courtesy Dimitris Theodorou.

    .. change::
      :tags: bug, autogenerate
      :tickets: 259

      The rendering of a :class:`~sqlalchemy.schema.ForeignKeyConstraint`
      will now ensure that the names of the source and target columns are
      the database-side name of each column, and not the value of the
      ``.key`` attribute as may be set only on the Python side.
      This is because Alembic generates the DDL for constraints
      as standalone objects without the need to actually refer to an in-Python
      :class:`~sqlalchemy.schema.Table` object, so there's no step that
      would resolve these Python-only key names to database column names.

    .. change::
      :tags: bug, autogenerate
      :tickets: 260

      Fixed bug in foreign key autogenerate where if the in-Python table
      used custom column keys (e.g. using the ``key='foo'`` kwarg to
      ``Column``), the comparison of existing foreign keys to those specified
      in the metadata would fail, as the reflected table would not have
      these keys available which to match up.  Foreign key comparison for
      autogenerate now ensures it's looking at the database-side names
      of the columns in all cases; this matches the same functionality
      within unique constraints and indexes.

    .. change::
      :tags: bug, autogenerate
      :tickets: 261
      :pullreq: github:17

      Fixed issue in autogenerate type rendering where types that belong
      to modules that have the name "sqlalchemy" in them would be mistaken
      as being part of the ``sqlalchemy.`` namespace.  Pull req courtesy
      Bartosz Burclaf.

.. changelog::
    :version: 0.7.3
    :released: December 30, 2014

    .. change::
      :tags: bug, versioning
      :tickets: 258

      Fixed regression in new versioning system where upgrade / history
      operation would fail on AttributeError if no version files were
      present at all.

.. changelog::
    :version: 0.7.2
    :released: December 18, 2014

    .. change::
      :tags: bug, sqlite, autogenerate

      Adjusted the SQLite backend regarding autogen of unique constraints
      to work fully with the current SQLAlchemy 1.0, which now will report
      on UNIQUE constraints that have no name.

    .. change::
      :tags: bug, batch
      :tickets: 254

      Fixed bug in batch where if the target table contained multiple
      foreign keys to the same target table, the batch mechanics would
      fail with a "table already exists" error.  Thanks for the help
      on this from Lucas Kahlert.

    .. change::
      :tags: bug, mysql
      :tickets: 251
      :pullreq: bitbucket:35

      Fixed an issue where the MySQL routine to skip foreign-key-implicit
      indexes would also catch unnamed unique indexes, as they would be
      named after the column and look like the FK indexes.  Pull request
      courtesy Johannes Erdfelt.

    .. change::
      :tags: bug, mssql, oracle
      :tickets: 253

      Repaired a regression in both the MSSQL and Oracle dialects whereby
      the overridden ``_exec()`` method failed to return a value, as is
      needed now in the 0.7 series.

.. changelog::
    :version: 0.7.1
    :released: December 3, 2014

    .. change::
      :tags: bug, batch

      The ``render_as_batch`` flag was inadvertently hardcoded to ``True``,
      so all autogenerates were spitting out batch mode...this has been
      fixed so that batch mode again is only when selected in env.py.

    .. change::
      :tags: feature, autogenerate
      :tickets: 178
      :pullreq: bitbucket:32

      Support for autogenerate of FOREIGN KEY constraints has been added.
      These are delivered within the autogenerate process in the same
      manner as UNIQUE constraints, including ``include_object`` support.
      Big thanks to Ann Kamyshnikova for doing the heavy lifting here.

    .. change::
      :tags: feature, batch

      Added :paramref:`~.Operations.batch_alter_table.naming_convention`
      argument to :meth:`.Operations.batch_alter_table`, as this is necessary
      in order to drop foreign key constraints; these are often unnamed
      on the target database, and in the case that they are named, SQLAlchemy
      is as of the 0.9 series not including these names yet.

      .. seealso::

        :ref:`dropping_sqlite_foreign_keys`

    .. change::
      :tags: bug, batch
      :pullreq: bitbucket:34

      Fixed bug where the "source_schema" argument was not correctly passed
      when calling :meth:`.BatchOperations.create_foreign_key`.  Pull
      request courtesy Malte Marquarding.

    .. change::
      :tags: bug, batch
      :tickets: 249

      Repaired the inspection, copying and rendering of CHECK constraints
      and so-called "schema" types such as Boolean, Enum within the batch
      copy system; the CHECK constraint will not be "doubled" when the table is
      copied, and additionally the inspection of the CHECK constraint for
      its member columns will no longer fail with an attribute error.

    .. change::
      :tags: feature, batch

      Added two new arguments
      :paramref:`.Operations.batch_alter_table.reflect_args`
      and :paramref:`.Operations.batch_alter_table.reflect_kwargs`, so that
      arguments may be passed directly to suit the
      :class:`~.sqlalchemy.schema.Table`
      object that will be reflected.

      .. seealso::

        :ref:`batch_controlling_table_reflection`

.. changelog::
    :version: 0.7.0
    :released: November 24, 2014

    .. change::
      :tags: feature, versioning
      :tickets: 167

      The "multiple heads / branches" feature has now landed.  This is
      by far the most significant change Alembic has seen since its inception;
      while the workflow of most commands hasn't changed, and the format
      of version files and the ``alembic_version`` table are unchanged as well,
      a new suite of features opens up in the case where multiple version
      files refer to the same parent, or to the "base".  Merging of
      branches, operating across distinct named heads, and multiple
      independent bases are now all supported.   The feature incurs radical
      changes to the internals of versioning and traversal, and should be
      treated as "beta mode" for the next several subsequent releases
      within 0.7.

      .. seealso::

          :ref:`branches`

    .. change::
      :tags: feature, versioning
      :tickets: 124

      In conjunction with support for multiple independent bases, the
      specific version directories are now also configurable to include
      multiple, user-defined directories.   When multiple directories exist,
      the creation of a revision file with no down revision requires
      that the starting directory is indicated; the creation of subsequent
      revisions along that lineage will then automatically use that
      directory for new files.

      .. seealso::

          :ref:`multiple_version_directories`

    .. change::
      :tags: feature, operations, sqlite
      :tickets: 21

      Added "move and copy" workflow, where a table to be altered is copied to
      a new one with the new structure and the old one dropped, is now
      implemented for SQLite as well as all database backends in general
      using the new :meth:`.Operations.batch_alter_table` system.   This
      directive provides a table-specific operations context which gathers
      column- and constraint-level mutations specific to that table, and
      at the end of the context creates a new table combining the structure
      of the old one with the given changes, copies data from old table to new,
      and finally drops the old table,
      renaming the new one to the existing name.  This is required for
      fully featured SQLite migrations, as SQLite has very little support for the
      traditional ALTER directive.   The batch directive
      is intended to produce code that is still compatible with other databases,
      in that the "move and copy" process only occurs for SQLite by default,
      while still providing some level of sanity to SQLite's
      requirement by allowing multiple table mutation operations to
      proceed within one "move and copy" as well as providing explicit
      control over when this operation actually occurs.  The "move and copy"
      feature may be optionally applied to other backends as well, however
      dealing with referential integrity constraints from other tables must
      still be handled explicitly.

      .. seealso::

          :ref:`batch_migrations`

    .. change::
      :tags: feature, commands

      Relative revision identifiers as used with ``alembic upgrade``,
      ``alembic downgrade`` and ``alembic history`` can be combined with
      specific revisions as well, e.g. ``alembic upgrade ae10+3``, to produce
      a migration target relative to the given exact version.

    .. change::
      :tags: bug, commands
      :tickets: 248

      The ``alembic revision`` command accepts the ``--sql`` option to
      suit some very obscure use case where the ``revision_environment``
      flag is set up, so that ``env.py`` is run when ``alembic revision``
      is run even though autogenerate isn't specified.   As this flag is
      otherwise confusing, error messages are now raised if
      ``alembic revision`` is invoked with both ``--sql`` and
      ``--autogenerate`` or with ``--sql`` without
      ``revision_environment`` being set.

    .. change::
      :tags: bug, autogenerate, postgresql
      :tickets: 247

      Added a rule for Postgresql to not render a "drop unique" and "drop index"
      given the same name; for now it is assumed that the "index" is the
      implicit one Postgreql generates.   Future integration with
      new SQLAlchemy 1.0 features will improve this to be more
      resilient.

    .. change::
      :tags: bug, autogenerate
      :tickets: 247

      A change in the ordering when columns and constraints are dropped;
      autogenerate will now place the "drop constraint" calls *before*
      the "drop column" calls, so that columns involved in those constraints
      still exist when the constraint is dropped.

    .. change::
      :tags: feature, commands

      New commands added: ``alembic show``, ``alembic heads`` and
      ``alembic merge``.  Also, a new option ``--verbose`` has been
      added to  several informational commands, such as ``alembic history``,
      ``alembic current``, ``alembic branches``, and ``alembic heads``.
      ``alembic revision`` also contains several new options used
      within the new branch management system.    The output of commands has
      been altered in many cases to support new fields and attributes;
      the ``history`` command in particular now returns it's "verbose" output
      only if ``--verbose`` is sent; without this flag it reverts to it's
      older behavior of short line items (which was never changed in the docs).

    .. change::
      :tags: changed, commands

      The ``--head_only`` option to the ``alembic current`` command is
      deprecated; the ``current`` command now lists just the version numbers
      alone by default; use ``--verbose`` to get at additional output.

    .. change::
      :tags: feature, config
      :pullreq: bitbucket:33

      Added new argument :paramref:`.Config.config_args`, allows a dictionary
      of replacement variables to be passed which will serve as substitution
      values when an API-produced :class:`.Config` consumes the ``.ini``
      file.  Pull request courtesy Noufal Ibrahim.

    .. change::
      :tags: bug, oracle
      :tickets: 245

      The Oracle dialect sets "transactional DDL" to False by default,
      as Oracle does not support transactional DDL.

    .. change::
      :tags: bug, autogenerate
      :tickets: 243

      Fixed a variety of issues surrounding rendering of Python code that
      contains unicode literals.  The first is that the "quoted_name" construct
      that SQLAlchemy uses to represent table and column names as well
      as schema names does not ``repr()`` correctly on Py2K when the value
      contains unicode characters; therefore an explicit stringification is
      added to these.  Additionally, SQL expressions such as server defaults
      were not being generated in a unicode-safe fashion leading to decode
      errors if server defaults contained non-ascii characters.

    .. change::
      :tags: bug, operations
      :tickets: 174
      :pullreq: bitbucket:29

      The :meth:`.Operations.add_column` directive will now additionally emit
      the appropriate ``CREATE INDEX`` statement if the
      :class:`~sqlalchemy.schema.Column` object specifies ``index=True``.
      Pull request courtesy David Szotten.

    .. change::
      :tags: feature, operations
      :tickets: 205

      The :class:`~sqlalchemy.schema.Table` object is now returned when
      the :meth:`.Operations.create_table` method is used.  This ``Table``
      is suitable for use in subsequent SQL operations, in particular
      the :meth:`.Operations.bulk_insert` operation.

    .. change::
      :tags: feature, autogenerate
      :tickets: 203

      Indexes and unique constraints are now included in the
      :paramref:`.EnvironmentContext.configure.include_object` hook.
      Indexes are sent with type ``"index"`` and unique constraints with
      type ``"unique_constraint"``.

    .. change::
      :tags: bug, autogenerate
      :tickets: 219

      Bound parameters are now resolved as "literal" values within the
      SQL expression inside of a CheckConstraint(), when rendering the SQL
      as a text string; supported for SQLAlchemy 0.8.0 and forward.

    .. change::
      :tags: bug, autogenerate
      :tickets: 199

      Added a workaround for SQLAlchemy issue #3023 (fixed in 0.9.5) where
      a column that's part of an explicit PrimaryKeyConstraint would not
      have its "nullable" flag set to False, thus producing a false
      autogenerate.  Also added a related correction to MySQL which will
      correct for MySQL's implicit server default of '0' when a NULL integer
      column is turned into a primary key column.

    .. change::
      :tags: bug, autogenerate, mysql
      :tickets: 240

      Repaired issue related to the fix for #208 and others; a composite
      foreign key reported by MySQL would cause a KeyError as Alembic
      attempted to remove MySQL's implicitly generated indexes from the
      autogenerate list.

    .. change::
      :tags: bug, autogenerate
      :tickets: 28

      If the "alembic_version" table is present in the target metadata,
      autogenerate will skip this also.  Pull request courtesy
      Dj Gilcrease.

    .. change::
      :tags: bug, autogenerate
      :tickets: 77

      The :paramref:`.EnvironmentContext.configure.version_table`
      and :paramref:`.EnvironmentContext.configure.version_table_schema`
      arguments are now honored during the autogenerate process, such that
      these names will be used as the "skip" names on both the database
      reflection and target metadata sides.

    .. change::
      :tags: changed, autogenerate
      :tickets: 229

      The default value of the
      :paramref:`.EnvironmentContext.configure.user_module_prefix`
      parameter is **no longer the same as the SQLAlchemy prefix**.
      When omitted, user-defined types will now use the ``__module__``
      attribute of the type class itself when rendering in an
      autogenerated module.

    .. change::
      :tags: bug, templates
      :tickets: 234

      Revision files are now written out using the ``'wb'`` modifier to
      ``open()``, since Mako reads the templates with ``'rb'``, thus preventing
      CRs from being doubled up as has been observed on windows.  The encoding
      of the output now defaults to 'utf-8', which can be configured using
      a newly added config file parameter ``output_encoding``.

    .. change::
      :tags: bug, operations
      :tickets: 230

      Added support for use of the :class:`~sqlalchemy.sql.elements.quoted_name`
      construct when using the ``schema`` argument within operations.  This
      allows a name containing a dot to be fully quoted, as well as to
      provide configurable quoting on a per-name basis.

    .. change::
      :tags: bug, autogenerate, postgresql
      :tickets: 73

      Added a routine by which the Postgresql Alembic dialect inspects
      the server default of INTEGER/BIGINT columns as they are reflected
      during autogenerate for the pattern ``nextval(<name>...)`` containing
      a potential sequence name, then queries ``pg_catalog`` to see if this
      sequence is "owned" by the column being reflected; if so, it assumes
      this is a SERIAL or BIGSERIAL column and the server default is
      omitted from the column reflection as well as any kind of
      server_default comparison or rendering, along with an INFO message
      in the logs indicating this has taken place. This allows SERIAL/BIGSERIAL
      columns to keep the SEQUENCE from being unnecessarily present within
      the autogenerate operation.

    .. change::
      :tags: bug, autogenerate
      :tickets: 197, 64, 196

      The system by which autogenerate renders expressions within
      a :class:`~sqlalchemy.schema.Index`, the ``server_default``
      of :class:`~sqlalchemy.schema.Column`, and the
      ``existing_server_default`` of
      :meth:`.Operations.alter_column` has been overhauled to anticipate
      arbitrary SQLAlchemy SQL constructs, such as ``func.somefunction()``,
      ``cast()``, ``desc()``, and others.   The system does not, as might
      be preferred, render the full-blown Python expression as originally
      created within the application's source code, as this would be exceedingly
      complex and difficult.  Instead, it renders the SQL expression against
      the target backend that's subject to the autogenerate, and then
      renders that SQL inside of a :func:`~sqlalchemy.sql.expression.text`
      construct as a literal SQL string.  This approach still has the
      downside that the rendered SQL construct may not be backend-agnostic
      in all cases, so there is still a need for manual intervention in that
      small number of cases, but overall the majority of cases should work
      correctly now.  Big thanks to Carlos Rivera for pull requests and
      support on this.

    .. change::
      :tags: feature

      SQLAlchemy's testing infrastructure is now used to run tests.
      This system supports both nose and pytest and opens the way
      for Alembic testing to support any number of backends, parallel
      testing, and 3rd party dialect testing.

    .. change::
      :tags: changed, compatibility

      Minimum SQLAlchemy version is now 0.7.6, however at least
      0.8.4 is strongly recommended.  The overhaul of the test suite
      allows for fully passing tests on all SQLAlchemy versions
      from 0.7.6 on forward.

    .. change::
      :tags: bug, operations

      The "match" keyword is not sent to :class:`.ForeignKeyConstraint`
      by :meth:`.Operations.create_foreign_key` when SQLAlchemy 0.7 is in use;
      this keyword was added to SQLAlchemy as of 0.8.0.

.. changelog::
    :version: 0.6.7
    :released: September 9, 2014

    .. change::
      :tags: bug, mssql
      :pullreq: bitbucket:26

      Fixed bug in MSSQL dialect where "rename table" wasn't using
      ``sp_rename()`` as is required on SQL Server.  Pull request courtesy
      Łukasz Bołdys.

    .. change::
      :tags: feature
      :tickets: 222

      Added support for functional indexes when using the
      :meth:`.Operations.create_index` directive.   Within the list of columns,
      the SQLAlchemy ``text()`` construct can be sent, embedding a literal
      SQL expression; the :meth:`.Operations.create_index` will perform some hackery
      behind the scenes to get the :class:`.Index` construct to cooperate.
      This works around some current limitations in :class:`.Index`
      which should be resolved on the SQLAlchemy side at some point.

.. changelog::
    :version: 0.6.6
    :released: August 7, 2014

    .. change::
      :tags: bug
      :tickets: 95
      :pullreq: bitbucket:24

      A file named ``__init__.py`` in the ``versions/`` directory is now
      ignored by Alembic when the collection of version files is retrieved.
      Pull request courtesy Michael Floering.

    .. change::
      :tags: bug
      :pullreq: bitbucket:23

      Fixed Py3K bug where an attempt would be made to sort None against
      string values when autogenerate would detect tables across multiple
      schemas, including the default schema.  Pull request courtesy
      paradoxxxzero.

    .. change::
      :tags: bug
      :pullreq: github:15

      Autogenerate render will render the arguments within a Table construct
      using ``*[...]`` when the number of columns/elements is greater than
      255.  Pull request courtesy Ryan P. Kelly.

    .. change::
      :tags: bug
      :pullreq: github:14

      Fixed bug where foreign key constraints would fail to render in
      autogenerate when a schema name was present.  Pull request courtesy
      Andreas Zeidler.

    .. change::
      :tags: bug
      :tickets: 212

      Some deep-in-the-weeds fixes to try to get "server default" comparison
      working better across platforms and expressions, in particular on
      the Postgresql backend, mostly dealing with quoting/not quoting of various
      expressions at the appropriate time and on a per-backend basis.
      Repaired and tested support for such defaults as Postgresql interval
      and array defaults.

    .. change::
      :tags: enhancement
      :tickets: 209

      When a run of Alembic command line fails due to ``CommandError``,
      the output now prefixes the string with ``"FAILED:"``, and the error
      is also written to the log output using ``log.error()``.

    .. change::
      :tags: bug
      :tickets: 208

      Liberalized even more the check for MySQL indexes that shouldn't be
      counted in autogenerate as "drops"; this time it's been reported
      that an implicitly created index might be named the same as a composite
      foreign key constraint, and not the actual columns, so we now skip those
      when detected as well.

    .. change::
      :tags: feature
      :pullreq: github:10

      Added a new accessor :attr:`.MigrationContext.config`, when used
      in conjunction with a :class:`.EnvironmentContext` and
      :class:`.Config`, this config will be returned.  Patch
      courtesy Marc Abramowitz.

.. changelog::
    :version: 0.6.5
    :released: May 3, 2014

    .. change::
      :tags: bug, autogenerate, mysql
      :tickets: 202

      This releases' "autogenerate index detection" bug, when a MySQL table
      includes an Index with the same name as a column, autogenerate reported
      it as an "add" even though its not; this is because we ignore reflected
      indexes of this nature due to MySQL creating them implicitly.  Indexes
      that are named the same as a column are now ignored on
      MySQL if we see that the backend is reporting that it already exists;
      this indicates that we can still detect additions of these indexes
      but not drops, as we cannot distinguish a backend index same-named
      as the column as one that is user generated or mysql-generated.

    .. change::
      :tags: feature, environment
      :tickets: 201

      Added new feature :paramref:`.EnvironmentContext.configure.transaction_per_migration`,
      which when True causes the BEGIN/COMMIT pair to incur for each migration
      individually, rather than for the whole series of migrations.  This is
      to assist with some database directives that need to be within individual
      transactions, without the need to disable transactional DDL entirely.

    .. change::
      :tags: bug, autogenerate
      :tickets: 200

      Fixed bug where the ``include_object()`` filter would not receive
      the original :class:`.Column` object when evaluating a database-only
      column to be dropped; the object would not include the parent
      :class:`.Table` nor other aspects of the column that are important
      for generating the "downgrade" case where the column is recreated.

    .. change::
      :tags: bug, environment
      :tickets: 195

      Fixed bug where :meth:`.EnvironmentContext.get_x_argument`
      would fail if the :class:`.Config` in use didn't actually
      originate from a command line call.

    .. change::
      :tags: bug, autogenerate
      :tickets: 194

      Fixed another bug regarding naming conventions, continuing
      from :ticket:`183`, where add_index()
      drop_index() directives would not correctly render the ``f()``
      construct when the index contained a convention-driven name.

.. changelog::
    :version: 0.6.4
    :released: March 28, 2014

    .. change::
      :tags: bug, mssql
      :tickets: 186

      Added quoting to the table name when the special EXEC is run to
      drop any existing server defaults or constraints when the
      :paramref:`.drop_column.mssql_drop_check` or
      :paramref:`.drop_column.mssql_drop_default`
      arguments are used.

    .. change::
      :tags: bug, mysql
      :tickets: 103

      Added/fixed support for MySQL "SET DEFAULT" / "DROP DEFAULT" phrases,
      which will now be rendered if only the server default is changing
      or being dropped (e.g. specify None to alter_column() to indicate
      "DROP DEFAULT").  Also added support for rendering MODIFY rather than
      CHANGE when the column name isn't changing.

    .. change::
      :tags: bug
      :tickets: 190

      Added support for the ``initially``, ``match`` keyword arguments
      as well as dialect-specific keyword arguments to
      :meth:`.Operations.create_foreign_key`.

      :tags: feature
      :tickets: 163

      Altered the support for "sourceless" migration files (e.g. only
      .pyc or .pyo present) so that the flag "sourceless=true" needs to
      be in alembic.ini for this behavior to take effect.

    .. change::
      :tags: bug, mssql
      :tickets: 185

      The feature that keeps on giving, index/unique constraint autogenerate
      detection, has even more fixes, this time to accommodate database dialects
      that both don't yet report on unique constraints, but the backend
      does report unique constraints as indexes.   The logic
      Alembic uses to distinguish between "this is an index!" vs.
      "this is a unique constraint that is also reported as an index!" has now
      been further enhanced to not produce unwanted migrations when the dialect
      is observed to not yet implement get_unique_constraints() (e.g. mssql).
      Note that such a backend will no longer report index drops for unique
      indexes, as these cannot be distinguished from an unreported unique
      index.

    .. change::
      :tags: bug
      :tickets: 183

      Extensive changes have been made to more fully support SQLAlchemy's new
      naming conventions feature.  Note that while SQLAlchemy has added this
      feature as of 0.9.2, some additional fixes in 0.9.4 are needed to
      resolve some of the issues:

      1. The :class:`.Operations` object now takes into account the naming
         conventions that are present on the :class:`.MetaData` object that's
         associated using :paramref:`~.EnvironmentContext.configure.target_metadata`.
         When :class:`.Operations` renders a constraint directive like
         ``ADD CONSTRAINT``, it now will make use of this naming convention
         when it produces its own temporary :class:`.MetaData` object.

      2. Note however that the autogenerate feature in most cases generates
         constraints like foreign keys and unique constraints with the
         final names intact; the only exception are the constraints implicit
         with a schema-type like Boolean or Enum.  In most of these cases,
         the naming convention feature will not take effect for these constraints
         and will instead use the given name as is, with one exception....

      3. Naming conventions which use the ``"%(constraint_name)s"`` token, that
         is, produce a new name that uses the original name as a component,
         will still be pulled into the naming convention converter and be
         converted.  The problem arises when autogenerate renders a constraint
         with it's already-generated name present in the migration file's source
         code, the name will be doubled up at render time due to the combination
         of #1 and #2.  So to work around this, autogenerate now renders these
         already-tokenized names using the new :meth:`.Operations.f` component.
         This component is only generated if **SQLAlchemy 0.9.4** or greater
         is in use.

      Therefore it is highly recommended that an upgrade to Alembic 0.6.4
      be accompanied by an upgrade of SQLAlchemy 0.9.4, if the new naming
      conventions feature is used.

      .. seealso::

          :ref:`autogen_naming_conventions`

    .. change::
      :tags: bug
      :tickets: 160

      Suppressed IOErrors which can raise when program output pipe
      is closed under a program like ``head``; however this only
      works on Python 2.  On Python 3, there is not yet a known way to
      suppress the BrokenPipeError warnings without prematurely terminating
      the program via signals.

    .. change::
      :tags: bug
      :tickets: 179

      Fixed bug where :meth:`.Operations.bulk_insert` would not function
      properly when :meth:`.Operations.inline_literal` values were used,
      either in --sql or non-sql mode.    The values will now render
      directly in --sql mode.  For compatibility with "online" mode,
      a new flag :paramref:`~.Operations.bulk_insert.multiinsert`
      can be set to False which will cause each parameter set to be
      compiled and executed with individual INSERT statements.

    .. change::
      :tags: bug, py3k
      :tickets: 175

      Fixed a failure of the system that allows "legacy keyword arguments"
      to be understood, which arose as of a change in Python 3.4 regarding
      decorators.  A workaround is applied that allows the code to work
      across Python 3 versions.

    .. change::
      :tags: feature
      :pullreq: bitbucket:20

      The :func:`.command.revision` command now returns the :class:`.Script`
      object corresponding to the newly generated revision.  From this
      structure, one can get the revision id, the module documentation,
      and everything else, for use in scripts that call upon this command.
      Pull request courtesy Robbie Coomber.

.. changelog::
    :version: 0.6.3
    :released: February 2, 2014

    .. change::
      :tags: bug
      :tickets: 172

      Added a workaround for when we call ``fcntl.ioctl()`` to get at
      ``TERMWIDTH``; if the function returns zero, as is reported to occur
      in some pseudo-ttys, the message wrapping system is disabled in the
      same way as if ``ioctl()`` failed.

    .. change::
      :tags: feature
      :tickets: 171

      Added new argument
      :paramref:`.EnvironmentContext.configure.user_module_prefix`.
      This prefix is applied when autogenerate renders a user-defined type,
      which here is defined as any type that is from a module outside of the
      ``sqlalchemy.`` hierarchy.   This prefix defaults to ``None``, in
      which case the :paramref:`.EnvironmentContext.configure.sqlalchemy_module_prefix`
      is used, thus preserving the current behavior.

    .. change::
      :tags: bug
      :tickets: 170

      Added support for autogenerate covering the use case where :class:`.Table`
      objects specified in the metadata have an explicit ``schema`` attribute
      whose name matches that of the connection's default schema
      (e.g. "public" for Postgresql).  Previously, it was assumed that "schema"
      was ``None`` when it matched the "default" schema, now the comparison
      adjusts for this.

    .. change::
      :tags: bug
      :pullreq: github:9

      The :func:`.compare_metadata` public API function now takes into
      account the settings for
      :paramref:`.EnvironmentContext.configure.include_object`,
      :paramref:`.EnvironmentContext.configure.include_symbol`,
      and :paramref:`.EnvironmentContext.configure.include_schemas`, in the
      same way that the ``--autogenerate`` command does.  Pull
      request courtesy Roman Podoliaka.

    .. change::
      :tags: bug
      :tickets: 168

      Calling :func:`.bulk_insert` with an empty list will not emit any
      commands on the current connection.  This was already the case with
      ``--sql`` mode, so is now the case with "online" mode.

    .. change::
      :tags: bug
      :pullreq: bitbucket:17

     Enabled schema support for index and unique constraint autodetection;
     previously these were non-functional and could in some cases lead to
     attribute errors.  Pull request courtesy Dimitris Theodorou.

    .. change::
      :tags: bug
      :tickets: 164

     More fixes to index autodetection; indexes created with expressions
     like DESC or functional indexes will no longer cause AttributeError
     exceptions when attempting to compare the columns.

    .. change::
      :tags: feature
      :tickets: 163

     The :class:`.ScriptDirectory` system that loads migration files
     from a  ``versions/`` directory now supports so-called
     "sourceless" operation,  where the ``.py`` files are not present
     and instead ``.pyc`` or ``.pyo`` files are directly present where
     the ``.py`` files should be.  Note that while Python 3.3 has a
     new system of locating ``.pyc``/``.pyo`` files within a directory
     called ``__pycache__`` (e.g. PEP-3147), PEP-3147 maintains
     support for the "source-less imports" use case, where the
     ``.pyc``/``.pyo`` are in present in the "old" location, e.g. next
     to the ``.py`` file; this is the usage that's supported even when
     running Python3.3.


.. changelog::
    :version: 0.6.2
    :released: Fri Dec 27 2013

    .. change::
      :tags: bug

      Autogenerate for ``op.create_table()`` will not include a
      ``PrimaryKeyConstraint()`` that has no columns.

    .. change::
      :tags: bug

      Fixed bug in the not-internally-used :meth:`.ScriptDirectory.get_base`
      method which would fail if called on an empty versions directory.

    .. change::
      :tags: bug
      :tickets: 157

      An almost-rewrite of the new unique constraint/index autogenerate
      detection, to accommodate a variety of issues.  The emphasis is on
      not generating false positives for those cases where no net change
      is present, as these errors are the ones that impact all autogenerate
      runs:

        * Fixed an issue with unique constraint autogenerate detection where
          a named ``UniqueConstraint`` on both sides with column changes would
          render with the "add" operation before the "drop", requiring the
          user to reverse the order manually.

        * Corrected for MySQL's apparent addition of an implicit index
          for a foreign key column, so that it doesn't show up as "removed".
          This required that the index/constraint autogen system query the
          dialect-specific implementation for special exceptions.

        * reworked the "dedupe" logic to accommodate MySQL's bi-directional
          duplication of unique indexes as unique constraints, and unique
          constraints as unique indexes.  Postgresql's slightly different
          logic of duplicating unique constraints into unique indexes
          continues to be accommodated as well.  Note that a unique index
          or unique constraint removal on a backend that duplicates these may
          show up as a distinct "remove_constraint()" / "remove_index()" pair,
          which may need to be corrected in the post-autogenerate if multiple
          backends are being supported.

        * added another dialect-specific exception to the SQLite backend
          when dealing with unnamed unique constraints, as the backend can't
          currently report on constraints that were made with this technique,
          hence they'd come out as "added" on every run.

        * the ``op.create_table()`` directive will be auto-generated with
          the ``UniqueConstraint`` objects inline, but will not double them
          up with a separate ``create_unique_constraint()`` call, which may
          have been occurring.  Indexes still get rendered as distinct
          ``op.create_index()`` calls even when the corresponding table was
          created in the same script.

        * the inline ``UniqueConstraint`` within ``op.create_table()`` includes
          all the options like ``deferrable``, ``initially``, etc.  Previously
          these weren't rendering.

    .. change::
      :tags: feature, mssql

      Added new argument ``mssql_drop_foreign_key`` to
      :meth:`.Operations.drop_column`.  Like ``mssql_drop_default``
      and ``mssql_drop_check``, will do an inline lookup for a
      single foreign key which applies to this column, and drop it.
      For a column with more than one FK, you'd still need to explicitly
      use :meth:`.Operations.drop_constraint` given the name,
      even though only MSSQL has this limitation in the first place.

    .. change::
      :tags: bug, mssql
      :pullreq: bitbucket:13

      The MSSQL backend will add the batch separator (e.g. ``"GO"``)
      in ``--sql`` mode after the final ``COMMIT`` statement, to ensure
      that statement is also processed in batch mode.  Courtesy
      Derek Harland.

.. changelog::
    :version: 0.6.1
    :released: Wed Nov 27 2013

    .. change::
      :tags: bug, mysql
      :tickets: 152

      Fixed bug where :func:`.op.alter_column` in the MySQL dialect
      would fail to apply quotes to column names that had mixed casing
      or spaces.

    .. change::
      :tags: feature
      :pullreq: bitbucket:12

      Expanded the size of the "slug" generated by "revision" to 40
      characters, which is also configurable by new field
      ``truncate_slug_length``; and also split on the word rather than the
      character; courtesy Frozenball.

    .. change::
      :tags: bug
      :tickets: 135

      Fixed the output wrapping for Alembic message output, so that
      we either get the terminal width for "pretty printing" with
      indentation, or if not we just output the text as is; in any
      case the text won't be wrapped too short.

    .. change::
      :tags: bug
      :pullreq: bitbucket:9

      Fixes to Py3k in-place compatibity regarding output encoding and related;
      the use of the new io.* package introduced some incompatibilities on Py2k.
      These should be resolved, due to the introduction of new adapter types
      for translating from io.* to Py2k file types, StringIO types.
      Thanks to Javier Santacruz for help with this.

    .. change::
      :tags: bug
      :tickets: 145

      Fixed py3k bug where the wrong form of ``next()`` was being called
      when using the list_templates command.  Courtesy Chris Wilkes.

    .. change::
      :tags: feature
      :tickets: 107

      Support for autogeneration detection and rendering of indexes and
      unique constraints has been added.  The logic goes through some effort
      in order to differentiate between true unique constraints and
      unique indexes, where there are some quirks on backends like Postgresql.
      The effort here in producing the feature and tests is courtesy of IJL.

    .. change::
      :tags: bug

      Fixed bug introduced by new ``include_object`` argument where the
      inspected column would be misinterpreted when using a user-defined
      type comparison function, causing a KeyError or similar expression-related
      error.  Fix courtesy Maarten van Schaik.

    .. change::
      :tags: bug

      Added the "deferrable" keyword argument to :func:`.op.create_foreign_key`
      so that ``DEFERRABLE`` constraint generation is supported; courtesy
      Pedro Romano.

    .. change::
      :tags: bug
      :tickets: 137

      Ensured that strings going to stdout go through an encode/decode phase,
      so that any non-ASCII characters get to the output stream correctly
      in both Py2k and Py3k.   Also added source encoding detection using
      Mako's parse_encoding() routine in Py2k so that the __doc__ of a
      non-ascii revision file can be treated as unicode in Py2k.

.. changelog::
    :version: 0.6.0
    :released: Fri July 19 2013

    .. change::
      :tags: feature
      :tickets: 101

      Added new kw argument to :meth:`.EnvironmentContext.configure`
      ``include_object``.  This is a more flexible version of the
      ``include_symbol`` argument which allows filtering of columns as well as tables
      from the autogenerate process,
      and in the future will also work for types, constraints and
      other constructs.  The fully constructed schema object is passed,
      including its name and type as well as a flag indicating if the object
      is from the local application metadata or is reflected.

    .. change::
      :tags: feature

      The output of the ``alembic history`` command is now
      expanded to show information about each change on multiple
      lines, including the full top message,
      resembling the formatting of git log.

    .. change::
      :tags: feature

      Added :attr:`alembic.config.Config.cmd_opts` attribute,
      allows access to the ``argparse`` options passed to the
      ``alembic`` runner.

    .. change::
      :tags: feature
      :tickets: 120

      Added new command line argument ``-x``, allows extra arguments
      to be appended to the command line which can be consumed
      within an ``env.py`` script by looking at
      ``context.config.cmd_opts.x``, or more simply a new
      method :meth:`.EnvironmentContext.get_x_argument`.

    .. change::
      :tags: bug
      :tickets: 125

      Added support for options like "name" etc. to be rendered
      within CHECK constraints in autogenerate.  Courtesy
      Sok Ann Yap.

    .. change::
      :tags: misc

      Source repository has been moved from Mercurial to Git.

    .. change::
      :tags: bug

      Repaired autogenerate rendering of ForeignKeyConstraint
      to include use_alter argument, if present.

    .. change::
      :tags: feature

      Added ``-r`` argument to ``alembic history`` command,
      allows specification of ``[start]:[end]`` to view
      a slice of history.  Accepts revision numbers, symbols
      "base", "head", a new symbol "current" representing the
      current migration, as well as relative ranges for one
      side at a time (i.e. ``-r-5:head``, ``-rcurrent:+3``).
      Courtesy Atsushi Odagiri for this feature.

    .. change::
      :tags: feature
      :tickets: 55

      Source base is now in-place for Python 2.6 through
      3.3, without the need for 2to3.   Support for Python 2.5
      and below has been dropped.   Huge thanks to
      Hong Minhee for all the effort on this!

.. changelog::
    :version: 0.5.0
    :released: Thu Apr 4 2013

    .. note::

      Alembic 0.5.0 now requires at least
      version 0.7.3 of SQLAlchemy to run properly.
      Support for 0.6 has been dropped.

    .. change::
        :tags: feature
        :tickets: 76

      Added ``version_table_schema`` argument
      to :meth:`.EnvironmentContext.configure`,
      complements the ``version_table`` argument to
      set an optional remote schema for the version
      table.  Courtesy Christian Blume.

    .. change::
        :tags: bug, postgresql
        :tickets: 32

      Fixed format of RENAME for table that includes
      schema with Postgresql; the schema name shouldn't
      be in the "TO" field.

    .. change::
        :tags: feature
        :tickets: 90

      Added ``output_encoding`` option to
      :meth:`.EnvironmentContext.configure`,
      used with ``--sql`` mode to apply an encoding
      to the output stream.

    .. change::
        :tags: feature
        :tickets: 93

      Added :meth:`.Operations.create_primary_key`
      operation, will genenerate an ADD CONSTRAINT
      for a primary key.

    .. change::
        :tags: bug, mssql
        :tickets: 109

      Fixed bug whereby double quoting would be applied
      to target column name during an ``sp_rename``
      operation.

    .. change::
        :tags: bug, sqlite, mysql
        :tickets: 112

      transactional_ddl flag for SQLite, MySQL dialects
      set to False.  MySQL doesn't support it,
      SQLite does but current pysqlite driver does not.

    .. change::
        :tags: feature
        :tickets: 115

      upgrade and downgrade commands will list the
      first line of the docstring out next to the
      version number.  Courtesy Hong Minhee.

    .. change::
        :tags: feature

      Added --head-only option to "alembic current",
      will print current version plus the symbol
      "(head)" if this version is the head or not.
      Courtesy Charles-Axel Dein.

    .. change::
        :tags: bug
        :tickets: 110

      Autogenerate will render additional table keyword
      arguments like "mysql_engine" and others within
      op.create_table().

    .. change::
        :tags: feature
        :tickets: 108

      The rendering of any construct during autogenerate
      can be customized, in particular to allow special rendering
      for user-defined column, constraint subclasses, using new
      ``render_item`` argument to
      :meth:`.EnvironmentContext.configure`.

    .. change::
        :tags: bug

      Fixed bug whereby create_index()
      would include in the constraint columns that
      are added to all Table objects using events,
      externally to the generation of the constraint.
      This is the same issue that was fixed for unique
      constraints in version 0.3.2.

    .. change::
        :tags: bug

      Worked around a backwards-incompatible regression in Python3.3
      regarding argparse; running "alembic" with no arguments
      now yields an informative error in py3.3 as with all previous versions.
      Courtesy Andrey Antukh.

    .. change::
        :tags: change

      SQLAlchemy 0.6 is no longer supported by Alembic - minimum version is 0.7.3,
      full support is as of 0.7.9.

    .. change::
        :tags: bug
        :tickets: 104

      A host of argument name changes within migration
      operations for consistency.  Keyword arguments
      will continue to work on the old name for backwards compatibility,
      however required positional arguments will not:

        :meth:`.Operations.alter_column` - ``name`` -> ``new_column_name`` - old
        name will work for backwards compatibility.

        :meth:`.Operations.create_index` - ``tablename`` -> ``table_name`` -
        argument is positional.

        :meth:`.Operations.drop_index` - ``tablename`` -> ``table_name`` - old
        name will work for backwards compatibility.

        :meth:`.Operations.drop_constraint` - ``tablename`` -> ``table_name`` -
        argument is positional.

        :meth:`.Operations.drop_constraint` - ``type`` -> ``type_`` - old
        name will work for backwards compatibility

.. changelog::
    :version: 0.4.2
    :released: Fri Jan 11 2013

    .. change::
        :tags: bug, autogenerate
        :tickets: 99

      Fixed bug where autogenerate would fail if a Column
      to be added to a table made use of the ".key" paramter.

    .. change::
        :tags: bug, sqlite
        :tickets: 98

      The "implicit" constraint generated by a
      type such as Boolean or Enum will not generate an
      ALTER statement when run on SQlite, which does not
      support ALTER for the purpose of adding/removing
      constraints separate from the column def itself.
      While SQLite supports adding a CHECK constraint
      at the column level, SQLAlchemy would need modification
      to support this.
      A warning is emitted indicating this
      constraint cannot be added in this scenario.

    .. change::
        :tags: bug
        :tickets: 96

      Added a workaround to setup.py to prevent
      "NoneType" error from occuring when
      "setup.py test" is run.

    .. change::
        :tags: bug
        :tickets: 96

      Added an append_constraint() step to each
      condition within
      test_autogenerate:AutogenRenderTest.test_render_fk_constraint_kwarg
      if the SQLAlchemy version is less than 0.8, as ForeignKeyConstraint
      does not auto-append prior to 0.8.

    .. change::
        :tags: feature
        :tickets: 96

      Added a README.unittests with instructions for running the test
      suite fully.

.. changelog::
    :version: 0.4.1
    :released: Sun Dec 9 2012

    .. change::
        :tags: bug
        :tickets: 92

      Added support for autogenerate render of
      ForeignKeyConstraint options onupdate,
      ondelete, initially, and deferred.

    .. change::
        :tags: bug
        :tickets: 94

      Autogenerate will include "autoincrement=False"
      in the rendered table metadata
      if this flag was set to false on the source
      :class:`.Column` object.

    .. change::
        :tags: feature
        :tickets: 66

      Explicit error message describing the case
      when downgrade --sql is used without specifying
      specific start/end versions.

    .. change::
        :tags: bug
        :tickets: 81

      Removed erroneous "emit_events" attribute
      from operations.create_table() documentation.

    .. change::
        :tags: bug
        :tickets:

      Fixed the minute component in file_template
      which returned the month part of the create date.

.. changelog::
    :version: 0.4.0
    :released: Mon Oct 01 2012

    .. change::
        :tags: feature
        :tickets: 33

      Support for tables in alternate schemas
      has been added fully to all operations, as well as to
      the autogenerate feature.  When using autogenerate,
      specifying the flag include_schemas=True to
      Environment.configure() will also cause autogenerate
      to scan all schemas located by Inspector.get_schema_names(),
      which is supported by *some* (but not all)
      SQLAlchemy dialects including Postgresql.
      *Enormous* thanks to Bruno Binet for a huge effort
      in implementing as well as writing tests. .

    .. change::
        :tags: feature
        :tickets: 70

      The command line runner has been organized
      into a reusable CommandLine object, so that other
      front-ends can re-use the argument parsing built
      in.

    .. change::
        :tags: feature
        :tickets: 43

      Added "stdout" option to Config, provides
      control over where the "print" output of commands like
      "history", "init", "current" etc. are sent.

    .. change::
        :tags: bug
        :tickets: 71

      Fixed the "multidb" template which was badly out
      of date.   It now generates revision files using
      the configuration to determine the different
      upgrade_<xyz>() methods needed as well, instead of
      needing to hardcode these.  Huge thanks to
      BryceLohr for doing the heavy lifting here.

    .. change::
        :tags: bug
        :tickets: 72

      Fixed the regexp that was checking for .py files
      in the version directory to allow any .py file through.
      Previously it was doing some kind of defensive checking,
      probably from some early notions of how this directory
      works, that was prohibiting various filename patterns
      such as those which begin with numbers.

    .. change::
        :tags: bug
        :tickets:

      Fixed MySQL rendering for server_default which
      didn't work if the server_default was a generated
      SQL expression.  Courtesy Moriyoshi Koizumi.

    .. change::
        :tags: feature
        :tickets:

      Added support for alteration of MySQL
      columns that have AUTO_INCREMENT, as well as enabling
      this flag.  Courtesy Moriyoshi Koizumi.




.. changelog::
    :version: 0.3.6
    :released: Wed Aug 15 2012

    .. change::
        :tags: feature
        :tickets: 27

      Added include_symbol option to
      EnvironmentContext.configure(),
      specifies a callable which will include/exclude tables
      in their entirety from the autogeneration process
      based on name.

    .. change::
        :tags: feature
        :tickets: 59

      Added year, month, day, hour, minute, second
      variables to file_template.

    .. change::
        :tags: feature
        :tickets:

      Added 'primary' to the list of constraint types
      recognized for MySQL drop_constraint().

    .. change::
        :tags: feature
        :tickets:

      Added --sql argument to the "revision" command,
      for the use case where the "revision_environment"
      config option is being used but SQL access isn't
      desired.

    .. change::
        :tags: bug
        :tickets:

      Repaired create_foreign_key() for
      self-referential foreign keys, which weren't working
      at all.

    .. change::
        :tags: bug
        :tickets: 63

      'alembic' command reports an informative
      error message when the configuration is missing
      the 'script_directory' key.

    .. change::
        :tags: bug
        :tickets: 62

      Fixes made to the constraints created/dropped
      alongside so-called "schema" types such as
      Boolean and Enum.  The create/drop constraint logic
      does not kick in when using a dialect that doesn't
      use constraints for these types, such as postgresql,
      even when existing_type is specified to
      alter_column().  Additionally, the constraints
      are not affected if existing_type is passed but
      type\_ is not, i.e. there's no net change
      in type.

    .. change::
        :tags: bug
        :tickets: 66

      Improved error message when specifiying
      non-ordered revision identifiers to cover
      the case when the "higher" rev is None,
      improved message overall.

.. changelog::
    :version: 0.3.5
    :released: Sun Jul 08 2012

    .. change::
        :tags: bug
        :tickets: 31

      Fixed issue whereby reflected server defaults
      wouldn't be quoted correctly; uses repr() now.

    .. change::
        :tags: bug
        :tickets: 58

      Fixed issue whereby when autogenerate would
      render create_table() on the upgrade side for a
      table that has a Boolean type, an unnecessary
      CheckConstraint() would be generated.

    .. change::
        :tags: feature
        :tickets:

      Implemented SQL rendering for
      CheckConstraint() within autogenerate upgrade,
      including for literal SQL as well as SQL Expression
      Language expressions.

.. changelog::
    :version: 0.3.4
    :released: Sat Jun 02 2012

    .. change::
        :tags: bug
        :tickets:

      Fixed command-line bug introduced by the
      "revision_environment" feature.

.. changelog::
    :version: 0.3.3
    :released: Sat Jun 02 2012

    .. change::
        :tags: feature
        :tickets:

      New config argument
      "revision_environment=true", causes env.py to
      be run unconditionally when the "revision" command
      is run, to support script.py.mako templates with
      dependencies on custom "template_args".

    .. change::
        :tags: feature
        :tickets:

      Added "template_args" option to configure()
      so that an env.py can add additional arguments
      to the template context when running the
      "revision" command.  This requires either --autogenerate
      or the configuration directive "revision_environment=true".

    .. change::
        :tags: bug
        :tickets: 44

      Added "type" argument to op.drop_constraint(),
      and implemented full constraint drop support for
      MySQL.  CHECK and undefined raise an error.
      MySQL needs the constraint type
      in order to emit a DROP CONSTRAINT.

    .. change::
        :tags: feature
        :tickets: 34

      Added version_table argument to
      EnvironmentContext.configure(), allowing for the
      configuration of the version table name.

    .. change::
        :tags: feature
        :tickets:

      Added support for "relative" migration
      identifiers, i.e. "alembic upgrade +2",
      "alembic downgrade -1".  Courtesy
      Atsushi Odagiri for this feature.

    .. change::
        :tags: bug
        :tickets: 49

      Fixed bug whereby directories inside of
      the template directories, such as __pycache__
      on Pypy, would mistakenly be interpreted as
      files which are part of the template.

.. changelog::
    :version: 0.3.2
    :released: Mon Apr 30 2012

    .. change::
        :tags: feature
        :tickets: 40

      Basic support for Oracle added,
      courtesy shgoh.

    .. change::
        :tags: feature
        :tickets:

      Added support for UniqueConstraint
      in autogenerate, courtesy Atsushi Odagiri

    .. change::
        :tags: bug
        :tickets:

      Fixed support of schema-qualified
      ForeignKey target in column alter operations,
      courtesy Alexander Kolov.

    .. change::
        :tags: bug
        :tickets:

      Fixed bug whereby create_unique_constraint()
      would include in the constraint columns that
      are added to all Table objects using events,
      externally to the generation of the constraint.

.. changelog::
    :version: 0.3.1
    :released: Sat Apr 07 2012

    .. change::
        :tags: bug
        :tickets: 41

      bulk_insert() fixes:

        1. bulk_insert() operation was
           not working most likely since the 0.2 series
           when used with an engine.
        2. Repaired bulk_insert() to complete when
           used against a lower-case-t table and executing
           with only one set of parameters, working
           around SQLAlchemy bug #2461 in this regard.
        3. bulk_insert() uses "inline=True" so that phrases
           like RETURNING and such don't get invoked for
           single-row bulk inserts.
        4. bulk_insert() will check that you're passing
           a list of dictionaries in, raises TypeError
           if not detected.

.. changelog::
    :version: 0.3.0
    :released: Thu Apr 05 2012

    .. change::
        :tags: general
        :tickets:

      The focus of 0.3 is to clean up
      and more fully document the public API of Alembic,
      including better accessors on the MigrationContext
      and ScriptDirectory objects.  Methods that are
      not considered to be public on these objects have
      been underscored, and methods which should be public
      have been cleaned up and documented, including:

        MigrationContext.get_current_revision()
        ScriptDirectory.iterate_revisions()
        ScriptDirectory.get_current_head()
        ScriptDirectory.get_heads()
        ScriptDirectory.get_base()
        ScriptDirectory.generate_revision()

    .. change::
        :tags: feature
        :tickets:

      Added a bit of autogenerate to the
      public API in the form of the function
      alembic.autogenerate.compare_metadata.




.. changelog::
    :version: 0.2.2
    :released: Mon Mar 12 2012

    .. change::
        :tags: feature
        :tickets:

      Informative error message when op.XYZ
      directives are invoked at module import time.

    .. change::
        :tags: bug
        :tickets: 35

      Fixed inappropriate direct call to
      util.err() and therefore sys.exit()
      when Config failed to locate the
      config file within library usage.

    .. change::
        :tags: bug
        :tickets:

      Autogenerate will emit CREATE TABLE
      and DROP TABLE directives according to
      foreign key dependency order.

    .. change::
        :tags: bug
        :tickets:

      implement 'tablename' parameter on
      drop_index() as this is needed by some
      backends.

    .. change::
        :tags: feature
        :tickets:

      Added execution_options parameter
      to op.execute(), will call execution_options()
      on the Connection before executing.

      The immediate use case here is to allow
      access to the new no_parameters option
      in SQLAlchemy 0.7.6, which allows
      some DBAPIs (psycopg2, MySQLdb) to allow
      percent signs straight through without
      escaping, thus providing cross-compatible
      operation with DBAPI execution and
      static script generation.

    .. change::
        :tags: bug
        :tickets:

      setup.py won't install argparse if on
      Python 2.7/3.2

    .. change::
        :tags: feature
        :tickets: 29

      script_location can be interpreted
      by pkg_resources.resource_filename(), if
      it is a non-absolute URI that contains
      colons.   This scheme is the same
      one used by Pyramid.

    .. change::
        :tags: feature
        :tickets:

      added missing support for
      onupdate/ondelete flags for
      ForeignKeyConstraint, courtesy Giacomo Bagnoli

    .. change::
        :tags: bug
        :tickets: 30

      fixed a regression regarding an autogenerate
      error message, as well as various glitches
      in the Pylons sample template.  The Pylons sample
      template requires that you tell it where to
      get the Engine from now.  courtesy
      Marcin Kuzminski

    .. change::
        :tags: bug
        :tickets:

      drop_index() ensures a dummy column
      is added when it calls "Index", as SQLAlchemy
      0.7.6 will warn on index with no column names.

.. changelog::
    :version: 0.2.1
    :released: Tue Jan 31 2012

    .. change::
        :tags: bug
        :tickets: 26

      Fixed the generation of CHECK constraint,
      regression from 0.2.0

.. changelog::
    :version: 0.2.0
    :released: Mon Jan 30 2012

    .. change::
        :tags: feature
        :tickets: 19

      API rearrangement allows everything
      Alembic does to be represented by contextual
      objects, including EnvironmentContext,
      MigrationContext, and Operations.   Other
      libraries and applications can now use
      things like "alembic.op" without relying
      upon global configuration variables.
      The rearrangement was done such that
      existing migrations should be OK,
      as long as they use the pattern
      of "from alembic import context" and
      "from alembic import op", as these
      are now contextual objects, not modules.

    .. change::
        :tags: feature
        :tickets: 24

      The naming of revision files can
      now be customized to be some combination
      of "rev id" and "slug", the latter of which
      is based on the revision message.
      By default, the pattern "<rev>_<slug>"
      is used for new files.   New script files
      should include the "revision" variable
      for this to work, which is part of
      the newer script.py.mako scripts.

    .. change::
        :tags: bug
        :tickets: 25

      env.py templates call
      connection.close() to better support
      programmatic usage of commands; use
      NullPool in conjunction with create_engine()
      as well so that no connection resources
      remain afterwards.

    .. change::
        :tags: bug
        :tickets: 22

      fix the config.main() function to honor
      the arguments passed, remove no longer used
      "scripts/alembic" as setuptools creates this
      for us.

    .. change::
        :tags: bug
        :tickets:

      Fixed alteration of column type on
      MSSQL to not include the keyword "TYPE".

    .. change::
        :tags: feature
        :tickets: 23

      Can create alembic.config.Config
      with no filename, use set_main_option()
      to add values.  Also added set_section_option()
      which will add sections.




.. changelog::
    :version: 0.1.1
    :released: Wed Jan 04 2012

    .. change::
        :tags: bug
        :tickets:

      Clean up file write operations so that
      file handles are closed.

    .. change::
        :tags: feature
        :tickets:

      PyPy is supported.

    .. change::
        :tags: feature
        :tickets:

      Python 2.5 is supported, needs
      __future__.with_statement

    .. change::
        :tags: bug
        :tickets:

      Fix autogenerate so that "pass" is
      generated between the two comments
      if no net migrations were present.

    .. change::
        :tags: bug
        :tickets: 16

      Fix autogenerate bug that prevented
      correct reflection of a foreign-key
      referenced table in the list of "to remove".

    .. change::
        :tags: bug
        :tickets: 17

      Fix bug where create_table() didn't
      handle self-referential foreign key
      correctly

    .. change::
        :tags: bug
        :tickets: 18

      Default prefix for autogenerate
      directives is "op.", matching the
      mako templates.

    .. change::
        :tags: feature
        :tickets: 18

      Add alembic_module_prefix argument
      to configure() to complement
      sqlalchemy_module_prefix.

    .. change::
        :tags: bug
        :tickets: 14

      fix quotes not being rendered in
      ForeignKeConstraint during
      autogenerate

.. changelog::
    :version: 0.1.0
    :released: Wed Nov 30 2011

    .. change::
        :tags:
        :tickets:

      Initial release.  Status of features:

    .. change::
        :tags:
        :tickets:

      Alembic is used in at least one production
      environment, but should still be considered
      ALPHA LEVEL SOFTWARE as of this release,
      particularly in that many features are expected
      to be missing / unimplemented.   Major API
      changes are not anticipated but for the moment
      nothing should be assumed.

      The author asks that you *please* report all
      issues, missing features, workarounds etc.
      to the bugtracker, at
      https://bitbucket.org/zzzeek/alembic/issues/new .

    .. change::
        :tags:
        :tickets:

      Python 3 is supported and has been tested.

    .. change::
        :tags:
        :tickets:

      The "Pylons" and "MultiDB" environment templates
      have not been directly tested - these should be
      considered to be samples to be modified as
      needed.   Multiple database support itself
      is well tested, however.

    .. change::
        :tags:
        :tickets:

      Postgresql and MS SQL Server environments
      have been tested for several weeks in a production
      environment.  In particular, some involved workarounds
      were implemented to allow fully-automated dropping
      of default- or constraint-holding columns with
      SQL Server.

    .. change::
        :tags:
        :tickets:

      MySQL support has also been implemented to a
      basic degree, including MySQL's awkward style
      of modifying columns being accommodated.

    .. change::
        :tags:
        :tickets:

      Other database environments not included among
      those three have *not* been tested, *at all*.  This
      includes Firebird, Oracle, Sybase.   Adding
      support for these backends should be
      straightforward.  Please report all missing/
      incorrect behaviors to the bugtracker! Patches
      are welcome here but are optional - please just
      indicate the exact format expected by the target
      database.

    .. change::
        :tags:
        :tickets:

      SQLite, as a backend, has almost no support for
      schema alterations to existing databases.  The author
      would strongly recommend that SQLite not be used in
      a migration context - just dump your SQLite database
      into an intermediary format, then dump it back
      into a new schema.  For dev environments, the
      dev installer should be building the whole DB from
      scratch.  Or just use Postgresql, which is a much
      better database for non-trivial schemas.
      Requests for full ALTER support on SQLite should be
      reported to SQLite's bug tracker at
      http://www.sqlite.org/src/wiki?name=Bug+Reports,
      as Alembic will not be implementing the
      "rename the table to a temptable then copy the
      data into a new table" workaround.
      Note that Alembic will at some point offer an
      extensible API so that you can implement commands
      like this yourself.

    .. change::
        :tags:
        :tickets:

      Well-tested directives include add/drop table, add/drop
      column, including support for SQLAlchemy "schema"
      types which generate additional CHECK
      constraints, i.e. Boolean, Enum.  Other directives not
      included here have *not* been strongly tested
      in production, i.e. rename table, etc.

    .. change::
        :tags:
        :tickets:

      Both "online" and "offline" migrations, the latter
      being generated SQL scripts to hand off to a DBA,
      have been strongly production tested against
      Postgresql and SQL Server.

    .. change::
        :tags:
        :tickets:

      Modify column type, default status, nullable, is
      functional and tested across PG, MSSQL, MySQL,
      but not yet widely tested in production usage.

    .. change::
        :tags:
        :tickets:

      Many migrations are still outright missing, i.e.
      create/add sequences, etc.  As a workaround,
      execute() can be used for those which are missing,
      though posting of tickets for new features/missing
      behaviors is strongly encouraged.

    .. change::
        :tags:
        :tickets:

      Autogenerate feature is implemented and has been
      tested, though only a little bit in a production setting.
      In particular, detection of type and server
      default changes are optional and are off by default;
      they can also be customized by a callable.
      Both features work but can have surprises particularly
      the disparity between BIT/TINYINT and boolean,
      which hasn't yet been worked around, as well as
      format changes performed by the database on defaults
      when it reports back.  When enabled, the PG dialect
      will execute the two defaults to be compared to
      see if they are equivalent.  Other backends may
      need to do the same thing.

      The autogenerate feature only generates
      "candidate" commands which must be hand-tailored
      in any case, so is still a useful feature and
      is safe to use.  Please report missing/broken features
      of autogenerate!  This will be a great feature and
      will also improve SQLAlchemy's reflection services.

    .. change::
        :tags:
        :tickets:

      Support for non-ASCII table, column and constraint
      names is mostly nonexistent.   This is also a
      straightforward feature add as SQLAlchemy itself
      supports unicode identifiers; Alembic itself will
      likely need fixes to logging, column identification
      by key, etc. for full support here.
