
==========
Changelog
==========
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
