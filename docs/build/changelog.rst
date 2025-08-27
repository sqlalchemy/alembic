
==========
Changelog
==========

.. changelog::
    :version: 1.16.6
    :include_notes_from: unreleased

.. changelog::
    :version: 1.16.5
    :released: August 27, 2025

    .. change::
        :tags: bug, mysql
        :tickets: 1492

        Fixed Python-side autogenerate rendering of index expressions in MySQL
        dialect by aligning it with SQLAlchemy's MySQL index expression rules. Pull
        request courtesy david-fed.

    .. change::
        :tags: bug, config
        :tickets: 1709

        Fixed issue where new pyproject.toml config would fail to parse the integer
        value used for the ``truncate_slug_length`` parameter.  Pull request
        courtesy Luís Henrique Allebrandt Schunemann.

.. changelog::
    :version: 1.16.4
    :released: July 10, 2025

    .. change::
        :tags: bug, config
        :tickets: 1694

        Fixed issue in new ``pyproject.toml`` support where boolean values, such as
        those used for the ``recursive_version_locations`` and ``sourceless``
        configuration parameters, would not be accepted.


.. changelog::
    :version: 1.16.3
    :released: July 8, 2025

    .. change::
        :tags: bug, autogenerate
        :tickets: 1633

        Fixed the rendering of ``server_default=FetchedValue()`` to ensure it is
        preceded by the ``sa.`` prefix in the migration script. Pull request
        courtesy david-fed.

    .. change::
        :tags: usecase, commands
        :tickets: 1683

        Added new ``pyproject_async`` template, combining the new ``pyproject``
        template with the ``async`` template.  Pull request courtesy Alc-Alc.

    .. change::
        :tags: usecase, autogenerate
        :tickets: 1686

        Add "module" post-write hook. This hook type is almost identical to the
        console_scripts hook, except it's running ``python -m black`` instead of
        using black's ``console_script``. It is mainly useful for tools without
        console scripts (e.g. ruff), but has semantics closer to the
        console_scripts hook in that it finds the ruff module available to the
        running interpreter instead of finding an executable by path. Pull request
        courtesy Frazer McLean.

    .. change::
        :tags: bug, autogenerate
        :tickets: 1692

        Fixed autogenerate rendering bug which failed to render foreign key
        constraints local to a :class:`.CreateTableOp` object if it did not refer
        to a ``MetaData`` collection via a private constructor argument that would
        not ordinarily be passed in user-defined rewriter recipes, including ones
        in the Alembic cookbook section of the docs.


.. changelog::
    :version: 1.16.2
    :released: June 16, 2025

    .. change::
        :tags: bug, autogenerate
        :tickets: 1671

        Fixed issue where dialect-specific keyword arguments in ``dialect_kwargs``
        were not rendered when rendering the :meth:`.Operations.create_foreign_key`
        operation.   This prevented dialect-specific keywords from being rendered
        using custom :class:`.Rewriter` recipes that modify
        :class:`.ops.CreateForeignKeyOp`, similar to other issues such as
        :ticket:`1635`.  Pull request courtesy Justin Malin.

    .. change::
        :tags: bug, command
        :tickets: 1679

        Fixed rendering of ``pyproject.toml`` to include two newlines when
        appending content to an existing file.  Pull request courtesy Jonathan
        Vanasco.


.. changelog::
    :version: 1.16.1
    :released: May 21, 2025

    .. change::
        :tags: bug, command
        :tickets: 1660

        Fixed regression caused by the ``pathlib`` refactoring that removed the use
        of :meth:`.Config.get_template_directory` as the canonical source of
        templates; the method is still present however it no longer would be
        consulted for a custom config subclass, as was the case with flask-migrate.

    .. change::
        :tags: bug, command
        :tickets: 1659

        Fixed regression caused by the ``pathlib`` refactoring where the "missing
        template" error message failed to render the name of the template that
        could not be found.

.. changelog::
    :version: 1.16.0
    :released: May 21, 2025

    .. change::
        :tags: feature, environment
        :tickets: 1082

        Added optional :pep:`621` support to Alembic, allowing all source code
        related configuration (e.g. local file paths, post write hook
        configurations, etc) to be configured in the project's ``pyproject.toml``
        file.   A new init template ``pyproject`` is added which illustrates a
        basic :pep:`621` setup.

        Besides being better integrated with a Python project's existing source
        code configuration, the TOML format allows for more flexible structures,
        allowing configuration items like ``version_locations`` and
        ``prepend_sys_path`` to be configured as lists of path strings without the
        need for path separator characters used by ``ConfigParser`` format.   The
        feature continues to support the ``%(here)s`` token which can substitute
        the absolute parent directory of the ``pyproject.toml`` file when
        consumed.

        The :pep:`621` feature supports configuration values that are relevant to
        source code organization and generation only; it does not accommodate
        configuration of database connectivity or logging, which remain under the
        category of "deployment" configuration and continue to be part of
        ``alembic.ini``, or whatever configurational method is established by the
        ``env.py`` file.   Using the combination of ``pyproject.toml`` for source
        code configuration along with a custom database/logging configuration
        method established in ``env.py`` will allow the ``alembic.ini`` file to be
        omitted altogether.


        .. seealso::

            :ref:`using_pep_621`

    .. change::
        :tags: usecase, environment
        :tickets: 1330

        Added new option to the ConfigParser (e.g. ``alembic.ini``) configuration
        ``path_separator``, which supersedes the existing ``version_path_separator``
        option.  ``path_separator`` specifies the path separator character that
        will be recognized for both the ``version_locations`` option as well
        as the ``prepend_sys_path`` option, defaulting to ``os`` which indicates
        that the value of ``os.pathsep`` should be used.

        The new attribute applies necessary os-dependent path splitting to the
        ``prepend_sys_path`` option so that windows paths which contain drive
        letters with colons are not inadvertently split, whereas previously
        os-dependent path splitting were only available for the ``version_locations`` option.

        Existing installations that don't indicate ``path_separator``
        will continue to use the older behavior, where ``version_path_separator``
        may be configured for ``version_locations``, and ``prepend_sys_path``
        continues to be split on spaces/commas/colons.  A deprecation warning
        is emitted for these fallback scenarios.

        When using the new ``pyproject.toml`` configuration detailed at
        :ref:`using_pep_621`, the whole issue of "path separators" is sidestepped
        and parameters like ``path_separator`` are unnecessary, as the TOML based
        configuration configures version locations and sys path elements as
        lists.

        Pull request courtesy Mike Werezak.

    .. change::
        :tags: feature, commands
        :tickets: 1610

        Added new :meth:`.CommandLine.register_command` method to
        :class:`.CommandLine`, intended to facilitate adding custom commands to
        Alembic's command line tool with minimal code required; previously this
        logic was embedded internally and was not publicly accessible.  A new
        recipe demonstrating this use is added.   Pull request courtesy Mikhail
        Bulash.

        .. seealso::

            :ref:`custom_commandline`

    .. change::
        :tags: usecase, operations
        :tickets: 1626

        Added :paramref:`.Operations.add_column.if_not_exists` and
        :paramref:`.Operations.drop_column.if_exists` to render ``IF [NOT] EXISTS``
        for ``ADD COLUMN`` and ``DROP COLUMN`` operations, a feature available on
        some database backends such as PostgreSQL, MariaDB, as well as third party
        backends.  The parameters also support autogenerate rendering allowing them
        to be added to autogenerate scripts via a custom :class:`.Rewriter`.  Pull
        request courtesy of Louis-Amaury Chaib (@lachaib).

    .. change::
        :tags: bug, general
        :tickets: 1637

        The ``pyproject.toml`` file used by the Alembic project itself for its
        Python package configuration has been amended to use the updated :pep:`639`
        configuration for license, which eliminates loud deprecation warnings when
        building the package.   Note this necessarily bumps setuptools build
        requirement to 77.0.3.

    .. change::
        :tags: bug, environment
        :tickets: 1643

        Fixed issue where use of deprecated ``utcnow()`` function would generate
        warnings.  Has been replaced with ``now(UTC)``.  Pull request courtesy
        Jens Tröger.

    .. change::
        :tags: usecase, operations
        :tickets: 1650

        Added :paramref:`.Operations.drop_constraint.if_exists` parameter to
        :meth:`.Operations.drop_constraint` which will render ``DROP CONSTRAINT IF
        EXISTS``. The parameter also supports autogenerate rendering allowing it to
        be added to autogenerate scripts via a custom :class:`.Rewriter`.  Pull
        request courtesy Aaron Griffin.

    .. change::
        :tags: bug, autogenerate
        :tickets: 1656

        The :meth:`.Operations.execute` operation when rendered in autogenerate
        (which would necessarily be only when using a custom writer that embeds
        :class:`.ExecuteSQLOp`) now correctly takes into account the value
        configured in :paramref:`configure.alembic_module_prefix` when rendering
        the operation with its prefixing namespace; previously this was hardcoded
        to ``op.``. Pull request courtesy Avery Fischer.

    .. change::
        :tags: bug, autogenerate
        :tickets: 264

        The autogenerate process will now apply the :meth:`.Operations.f` modifier
        to the names of all constraints and indexes that are reflected from the
        target database when generating migrations, which has the effect that these
        names will not have any subsequent naming conventions applied to them when
        the migration operations proceed.  As reflected objects already include the
        exact name that's present in the database, these names should not be
        modified.   The fix repairs the issue when using custom naming conventions
        which feature the ``%(constraint_name)s`` token would cause names to be
        double-processed, leading to errors in migration runs.



    .. change::
        :tags: refactored, environment

        The command, config and script modules now rely on ``pathlib.Path`` for
        internal path manipulations, instead of ``os.path()`` operations.   This
        has some impact on both public and private (i.e. underscored) API functions:

        * Public API functions that accept parameters indicating file and directory
          paths as strings will continue to do so, but now will also accept
          ``os.PathLike`` objects as well.
        * Public API functions and accessors that return directory paths as strings
          such as :attr:`.ScriptDirectory.dir`, :attr:`.Config.config_file_name`
          will continue to do so.
        * Private API functions and accessors, i.e. all those that are prefixed
          with an underscore, that previously returned directory paths as
          strings may now return a Path object instead.

.. changelog::
    :version: 1.15.2
    :released: March 28, 2025

    .. change::
        :tags: bug, autogenerate
        :tickets: 1635

        Fixed issue where the "modified_name" of :class:`.AlterColumnOp` would not
        be considered when rendering op directives for autogenerate. While
        autogenerate cannot detect changes in column name, this would nonetheless
        impact approaches that made use of this attribute in rewriter recipes. Pull
        request courtesy lenvk.

.. changelog::
    :version: 1.15.1
    :released: March 4, 2025

    .. change::
        :tags: bug, installation
        :tickets: 1616

        Fixed an issue in the new :pep:`621` ``pyproject.toml`` layout that
        prevented Alembic's template files from being included in the ``.whl`` file
        in the distribution.

.. changelog::
    :version: 1.15.0
    :released: March 4, 2025  (yanked due to issue #1616)

    .. change::
        :tags: bug, environment
        :tickets: 1567

        Added a basic docstring to the migration template files so that the
        upgrade/downgrade methods pass the D103 linter check which requires a
        docstring for public functions.  Pull request courtesy Peter Cock.

    .. change::
        :tags: usecase, autogenerate
        :tickets: 1603

        Index autogenerate will now render labels for expressions
        that use them. This is useful when applying operator classes
        in PostgreSQL that can be keyed on the label name.

    .. change::
        :tags: bug, autogenerate
        :tickets: 1613

        Fixed autogenerate rendering bug where the ``deferrable`` element of
        ``UniqueConstraint``, a bool, were being stringified rather than repr'ed
        when generating Python code.

    .. change::
        :tags: changed, general

        Support for Python 3.8 is dropped as of Alembic 1.15.0; this version is
        now EOL so Python 3.9 or higher is required for Alembic 1.15.

    .. change::
        :tags: changed, general

        Support for SQLAlchemy 1.3, which was EOL as of 2021, is now dropped from
        Alembic as of version 1.15.0.   SQLAlchemy version 1.4 or greater is
        required for use with Alembic 1.15.0.

    .. change::
        :tags: usecase, autogenerate
        :tickets: 1597

        Add revision context to AutogenerateDiffsDetected so that command can be
        wrapped and diffs may be output in a different format. Pull request
        courtesy Louis-Amaury Chaib (@lachaib).

    .. change::
        :tags: changed, general

        Installation has been converted to use :pep:`621`, e.g. ``pyproject.toml``.

.. changelog::
    :version: 1.14.1
    :released: January 19, 2025

    .. change::
        :tags: bug, environment
        :tickets: 1556

        Added `tzdata` to `tz` extras, which is required on some platforms such as
        Windows.  Pull request courtesy Danipulok.

    .. change::
        :tags: usecase, sqlite
        :tickets: 1576

        Modified SQLite's dialect to render "ALTER TABLE <t> RENAME COLUMN" when
        :meth:`.Operations.alter_column` is used with a straight rename, supporting
        SQLite's recently added column rename feature.

    .. change::
        :tags: bug, autogenerate
        :tickets: 1585

        Fixed bug where autogen render of a "variant" type would fail to catch the
        variants if the leading type were a dialect-specific type, rather than a
        generic type.


.. changelog::
    :version: 1.14.0
    :released: November 4, 2024

    .. change::
        :tags: usecase, runtime
        :tickets: 1560

        Added a new hook to the :class:`.DefaultImpl`
        :meth:`.DefaultImpl.version_table_impl`.  This allows third party dialects
        to define the exact structure of the alembic_version table, to include use
        cases where the table requires special directives and/or additional columns
        so that it may function correctly on a particular backend.  This is not
        intended as a user-expansion hook, only a dialect implementation hook to
        produce a working alembic_version table. Pull request courtesy Maciek
        Bryński.

.. changelog::
    :version: 1.13.3
    :released: September 23, 2024

    .. change::
        :tags: usecase, autogenerate

        Render ``if_exists`` and ``if_not_exists`` parameters in
        :class:`.CreateTableOp`, :class:`.CreateIndexOp`, :class:`.DropTableOp` and
        :class:`.DropIndexOp` in an autogenerate context.  While Alembic does not
        set these parameters during an autogenerate run, they can be enabled using
        a custom :class:`.Rewriter` in the ``env.py`` file, where they will now be
        part of the rendered Python code in revision files.  Pull request courtesy
        of Louis-Amaury Chaib (@lachaib).

    .. change::
        :tags: usecase, environment
        :tickets: 1509

        Enhance ``version_locations`` parsing to handle paths containing newlines.

    .. change::
        :tags: usecase, operations
        :tickets: 1520

        Added support for :paramref:`.Operations.create_table.if_not_exists` and
        :paramref:`.Operations.drop_table.if_exists`, adding similar functionality
        to render IF [NOT] EXISTS for table operations in a similar way as with
        indexes. Pull request courtesy Aaron Griffin.


    .. change::
        :tags: change, general

        The pin for ``setuptools<69.3`` in ``pyproject.toml`` has been removed.
        This pin was to prevent a sudden change to :pep:`625` in setuptools from
        taking place which changes the file name of SQLAlchemy's source
        distribution on pypi to be an all lower case name, and the change was
        extended to all SQLAlchemy projects to prevent any further surprises.
        However, the presence of this pin is now holding back environments that
        otherwise want to use a newer setuptools, so we've decided to move forward
        with this change, with the assumption that build environments will have
        largely accommodated the setuptools change by now.




.. changelog::
    :version: 1.13.2
    :released: June 26, 2024

    .. change::
        :tags: bug, commands
        :tickets: 1384

        Fixed bug in alembic command stdout where long messages were not properly
        wrapping at the terminal width.   Pull request courtesy Saif Hakim.

    .. change::
        :tags: usecase, autogenerate
        :tickets: 1391

        Improve computed column compare function to support multi-line expressions.
        Pull request courtesy of Georg Wicke-Arndt.

    .. change::
        :tags: bug, execution
        :tickets: 1394

        Fixed internal issue where Alembic would call ``connection.execute()``
        sending an empty tuple to indicate "no params".  In SQLAlchemy 2.1 this
        case will be deprecated as "empty sequence" is ambiguous as to its intent.


    .. change::
        :tags: bug, tests
        :tickets: 1435

        Fixes to support pytest 8.1 for the test suite.

    .. change::
        :tags: bug, autogenerate, postgresql
        :tickets: 1479

        Fixed the detection of serial column in autogenerate with tables
        not under default schema on PostgreSQL

.. changelog::
    :version: 1.13.1
    :released: December 20, 2023

    .. change::
        :tags: bug, autogenerate
        :tickets: 1337

        Fixed :class:`.Rewriter` so that more than two instances could be chained
        together correctly, also allowing multiple ``process_revision_directives``
        callables to be chained.  Pull request courtesy zrotceh.


    .. change::
        :tags: bug, environment
        :tickets: 1369

        Fixed issue where the method :meth:`.EnvironmentContext.get_x_argument`
        using the :paramref:`.EnvironmentContext.get_x_argument.as_dictionary`
        parameter would fail if an argument key were passed on the command line as
        a name alone, that is, without an equal sign ``=`` or a value. Behavior is
        repaired where this condition is detected and will return a blank string
        for the given key, consistent with the behavior where the ``=`` sign is
        present and no value.  Pull request courtesy Iuri de Silvio.

    .. change::
        :tags: bug, autogenerate
        :tickets: 1370

        Fixed issue where the "unique" flag of an ``Index`` would not be maintained
        when generating downgrade migrations.  Pull request courtesy Iuri de
        Silvio.

    .. change::
        :tags: bug, versioning
        :tickets: 1373

        Fixed bug in versioning model where a downgrade across a revision with two
        down revisions with one down revision depending on the other, would produce
        an erroneous state in the alembic_version table, making upgrades impossible
        without manually repairing the table.  Thanks much to Saif Hakim for
        the great work on this.

    .. change::
        :tags: bug, typing
        :tickets: 1377

        Updated pep-484 typing to pass mypy "strict" mode, however including
        per-module qualifications for specific typing elements not yet complete.
        This allows us to catch specific typing issues that have been ongoing
        such as import symbols not properly exported.


.. changelog::
    :version: 1.13.0
    :released: December 1, 2023

    .. change::
        :tags: bug, commands
        :tickets: 1234

        Fixed issue where the ``alembic check`` command did not function correctly
        with upgrade structures that have multiple, top-level elements, as are
        generated from the "multi-env" environment template.  Pull request courtesy
        Neil Williams.

    .. change::
        :tags: usecase, operations
        :tickets: 1323

        Updated logic introduced in :ticket:`151` to allow ``if_exists`` and
        ``if_not_exists`` on index operations also on SQLAlchemy
        1.4 series. Previously this feature was mistakenly requiring
        the 2.0 series.

    .. change::
        :tags: usecase
        :tickets: 1339

        Replaced ``python-dateutil`` with the standard library module
        `zoneinfo <https://docs.python.org/3.11/library/zoneinfo.html#module-zoneinfo>`_.
        This module was added in Python 3.9, so previous version will been
        to install the backport of it, available by installing the ``backports.zoneinfo``
        library. The ``alembic[tz]`` option has been updated accordingly.

    .. change::
        :tags: installation, changed
        :tickets: 1359

        Alembic 1.13 now supports Python 3.8 and above.

    .. change::
        :tags: bug, autogenerate
        :tickets: 1361

        Fixed autogenerate issue where ``create_table_comment()`` and
        ``drop_table_comment()`` rendering in a batch table modify would include
        the "table" and "schema" arguments, which are not accepted in batch as
        these are already part of the top level block.

    .. change::
        :tags: bug, postgresql
        :tickets: 1321, 1327, 1356

        Additional fixes to PostgreSQL expression index compare feature.
        The compare now correctly accommodates casts and differences in
        spacing.
        Added detection logic for operation clauses inside the expression,
        skipping the compare of these expressions.
        To accommodate these changes the logic for the comparison of the
        indexes and unique constraints was moved to the dialect
        implementation, allowing greater flexibility.

.. changelog::
    :version: 1.12.1
    :released: October 26, 2023

    .. change::
        :tags: bug, autogenerate, regression
        :tickets: 1329

        Fixed regression caused by :ticket:`879` released in 1.7.0 where the
        ".info" dictionary of ``Table`` would not render in autogenerate create
        table statements.  This can be useful for custom create table DDL rendering
        schemes so it is restored.

    .. change::
        :tags: bug, typing
        :tickets: 1325

        Improved typing in the
        :paramref:`.EnvironmentContext.configure.process_revision_directives`
        callable to better indicate that the passed-in type is
        :class:`.MigrationScript`, not the :class:`.MigrationOperation` base class,
        and added typing to the example at :ref:`cookbook_no_empty_migrations` to
        illustrate.

    .. change::
        :tags: bug, operations
        :tickets: 1335

        Repaired :class:`.ExecuteSQLOp` so that it can participate in "diff"
        operations; while this object is typically not present in a reflected
        operation stream, custom hooks may be adding this construct where it needs
        to have the correct ``to_diff_tuple()`` method.  Pull request courtesy
        Sebastian Bayer.

    .. change::
        :tags: typing, bug
        :tickets: 1058, 1277

        Improved the ``op.execute()`` method to correctly accept the
        ``Executable`` type that is the same which is used in SQLAlchemy
        ``Connection.execute()``.  Pull request courtesy Mihail Milushev.

    .. change::
        :tags: typing, bug
        :tickets: 930

        Improve typing of the revision parameter in various command functions.

    .. change::
        :tags: typing, bug
        :tickets: 1266

        Properly type the :paramref:`.Operations.create_check_constraint.condition`
        parameter of :meth:`.Operations.create_check_constraint` to accept boolean
        expressions.

    .. change::
        :tags: bug, postgresql
        :tickets: 1322

        Fixed autogen render issue where expressions inside of indexes for PG need
        to be double-parenthesized, meaning a single parens must be present within
        the generated ``text()`` construct.

    .. change::
        :tags: usecase
        :tickets: 1304

        Alembic now accommodates for Sequence and Identity that support dialect kwargs.
        This is a change that will be added to SQLAlchemy v2.1.

.. changelog::
    :version: 1.12.0
    :released: August 31, 2023

    .. change::
        :tags: bug, operations
        :tickets: 1300

        Added support for ``op.drop_constraint()`` to support PostgreSQL
        ``ExcludeConstraint`` objects, as well as other constraint-like objects
        that may be present in third party dialects, by resolving the ``type_``
        parameter to be ``None`` for this case.   Autogenerate has also been
        enhanced to exclude the ``type_`` parameter from rendering within this
        command when  ``type_`` is ``None``.  Pull request courtesy David Hills.



    .. change::
        :tags: bug, commands
        :tickets: 1299

        Fixed issue where the ``revision_environment`` directive in ``alembic.ini``
        was ignored by the ``alembic merge`` command, leading to issues when other
        configurational elements depend upon ``env.py`` being invoked within the
        command.

    .. change::
        :tags: bug, autogenerate
        :tickets: 1302

        Fixed issue where the ``ForeignKeyConstraint.match`` parameter would not be
        rendered in autogenerated migrations.  Pull request courtesy Asib
        Kamalsada.


    .. change::
        :tags: usecase, autogenerate
        :tickets: 1248

        Change the default value of
        :paramref:`.EnvironmentContext.configure.compare_type` to ``True``.
        As Alembic's autogenerate for types was dramatically improved in
        version 1.4 released in 2020, the type comparison feature is now much
        more reliable so is now enabled by default.

    .. change::
        :tags: feature, autogenerate
        :tickets: 1275

        Added new feature to the "code formatter" function which allows standalone
        executable tools to be run against code, without going through the Python
        interpreter.  Known as the ``exec`` runner, it complements the existing
        ``console_scripts`` runner by allowing non-Python tools such as ``ruff`` to
        be used.   Pull request courtesy Mihail Milushev.

        .. seealso::

            :ref:`post_write_hooks_config`



.. changelog::
    :version: 1.11.3
    :released: August 16, 2023

    .. change::
        :tags: bug, autogenerate, postgresql
        :tickets: 1270

        Improved autogenerate compare of expression based indexes on PostgreSQL
        to produce fewer wrong detections.

    .. change::
        :tags: bug, autogenerate
        :tickets: 1291

        Fixed issue with ``NULLS NOT DISTINCT`` detection in postgresql that
        would keep detecting changes in the index or unique constraint.

    .. change::
        :tags: bug, commands
        :tickets: 1273

        Added ``encoding="locale"`` setting to the use of Python's
        ``ConfigParser.read()``, so that a warning is not generated when using the
        recently added Python feature ``PYTHONWARNDEFAULTENCODING`` specified in
        :pep:`597`. The encoding is passed as the ``"locale"`` string under Python
        3.10 and greater, which indicates that the system-level locale should be
        used, as was the case already here.  Pull request courtesy Kevin Kirsche.


.. changelog::
    :version: 1.11.2
    :released: August 4, 2023

    .. change::
        :tags: usecase, typing
        :tickets: 1253

        Added typing to the default script mako templates.

    .. change::
        :tags: usecase, autogenerate
        :tickets: 1248

        Added support in autogenerate for ``NULLS NOT DISTINCT`` in
        the PostgreSQL dialect.

    .. change::
        :tags: bug
        :tickets: 1261

        Fixed format string logged when running a post write hook
        Pull request curtesy of Mathieu Défosse.

    .. change::
        :tags: feature, operations
        :tickets: 151

        Added parameters if_exists and if_not_exists for index operations.
        Pull request courtesy of Max Adrian.

.. changelog::
    :version: 1.11.1
    :released: May 17, 2023

    .. change::
        :tags: bug, autogenerate, regression
        :tickets: 1243, 1245

        As Alembic 1.11.0 is considered a major release (Alembic does not use
        semver, nor does its parent project SQLAlchemy; this has been
        :ref:`clarified <versioning_scheme>` in the documentation), change
        :ticket:`1130` modified calling signatures for most operations to consider
        all optional keyword parameters to be keyword-only arguments, to match what
        was always documented and generated by autogenerate. However, two of these
        changes were identified as possibly problematic without a more formal
        deprecation warning being emitted which were the ``table_name`` parameter
        to :meth:`.Operations.drop_index`, which was generated positionally by
        autogenerate prior to version 0.6.3 released in 2014, and ``type_`` in
        :meth:`.Operations.drop_constraint` and
        :meth:`.BatchOperations.drop_constraint`, which was documented positionally
        in one example in the batch documentation.

        These two signatures have been
        restored to allow those particular parameters to be passed positionally. A
        future change will include formal deprecation paths (with warnings) for
        these arguments where they will again become keyword-only in a future
        "Significant Minor" release.

    .. change::
        :tags: bug, typing
        :tickets: 1246

        Fixed typing use of :class:`~sqlalchemy.schema.Column` and other
        generic SQLAlchemy classes.

    .. change::
        :tags: bug, typing, regression
        :tickets: 1244

        Restored the output type of :meth:`.Config.get_section` to include
        ``Dict[str, str]`` as a potential return type, which had been changed to
        immutable ``Mapping[str, str]``. When a section is returned and the default
        is not used, a mutable dictionary is returned.

.. changelog::
    :version: 1.11.0
    :released: May 15, 2023

    .. change::
        :tags: bug, batch
        :tickets: 1237

        Added placeholder classes for :class:`~.sqla.Computed` and
        :class:`~.sqla.Identity` when older 1.x SQLAlchemy versions are in use,
        namely prior to SQLAlchemy 1.3.11 when the :class:`~.sqla.Computed`
        construct was introduced. Previously these were set to None, however this
        could cause issues with certain codepaths that were using ``isinstance()``
        such as one within "batch mode".

    .. change::
        :tags: bug, batch
        :tickets: 1221

        Correctly pass previously ignored arguments ``insert_before`` and
        ``insert_after`` in ``batch_alter_column``

    .. change::
        :tags: change, py3k
        :tickets: 1130

        Argument signatures of Alembic operations now enforce keyword-only
        arguments as passed as keyword and not positionally, such as
        :paramref:`.Operations.create_table.schema`,
        :paramref:`.Operations.add_column.type_`, etc.

    .. change::
        :tags: bug, postgresql
        :tickets: 1230

        Fix autogenerate issue with PostgreSQL :class:`.ExcludeConstraint`
        that included sqlalchemy functions. The function text was previously
        rendered as a plain string without surrounding with ``text()``.

    .. change::
        :tags: bug, mysql, regression
        :tickets: 1240

        Fixed regression caused by :ticket:`1166` released in version 1.10.0 which
        caused MySQL unique constraints with multiple columns to not compare
        correctly within autogenerate, due to different sorting rules on unique
        constraints vs. indexes, which in MySQL are shared constructs.

    .. change::
        :tags: misc
        :tickets: 1220

        Update code snippets within docstrings to use ``black`` code formatting.
        Pull request courtesy of James Addison.

    .. change::
        :tags: bug, typing
        :tickets: 1093

        Updated stub generator script to also add stubs method definitions for the
        :class:`.Operations` class and the :class:`.BatchOperations` class obtained
        from :meth:`.Operations.batch_alter_table`. As part of this change, the
        class hierarchy of :class:`.Operations` and :class:`.BatchOperations` has
        been rearranged on top of a common base class :class:`.AbstractOperations`
        in order to type correctly, as :class:`.BatchOperations` uses different
        method signatures for operations than :class:`.Operations`.


    .. change::
        :tags: bug, typing

        Repaired the return signatures for :class:`.Operations` that mostly
        return ``None``, and were erroneously referring to ``Optional[Table]``
        in many cases.

    .. change::
        :tags: usecase, commands
        :tickets: 1109

        Added quiet option to the command line, using the ``-q/--quiet``
        option. This flag will prevent alembic from logging anything
        to stdout.

    .. change::
        :tags: bug, autogenerate
        :tickets: 1178

        Modified the autogenerate implementation for comparing "server default"
        values from user-defined metadata to not apply any quoting to the value
        before comparing it to the server-reported default, except for within
        dialect-specific routines as needed. This change will affect the format of
        the server default as passed to the
        :paramref:`.EnvironmentContext.configure.compare_server_default` hook, as
        well as for third party dialects that implement a custom
        ``compare_server_default`` hook in their alembic impl, to be passed "as is"
        and not including additional quoting.   Custom implementations which rely
        on this quoting should adjust their approach based on observed formatting.

    .. change::
        :tags: bug, api, autogenerate
        :tickets: 1235

        Fixed issue where :func:`.autogenerate.render_python_code` function did not
        provide a default value for the ``user_module_prefix`` variable, leading to
        ``NoneType`` errors when autogenerate structures included user-defined
        types. Added new parameter
        :paramref:`.autogenerate.render_python_code.user_module_prefix` to allow
        this to be set as well as to default to ``None``. Pull request courtesy
        tangkikodo.


    .. change::
        :tags: usecase, asyncio
        :tickets: 1231

        Added :meth:`.AbstractOperations.run_async` to the operation module to
        allow running async functions in the ``upgrade`` or ``downgrade`` migration
        function when running alembic using an async dialect. This function will
        receive as first argument an
        :class:`~sqlalchemy.ext.asyncio.AsyncConnection` sharing the transaction
        used in the migration context.

.. changelog::
    :version: 1.10.4
    :released: April 24, 2023

    .. change::
        :tags: postgresql, autogenerate, feature
        :tickets: 1213

        Added support for autogenerate comparison of indexes on PostgreSQL which
        include SQL sort option, such as ``ASC`` or ``NULLS FIRST``.
        The sort options are correctly detected only when defined using the
        sqlalchemy modifier functions, such as ``asc()`` or ``nulls_first()``,
        or the equivalent methods.
        Passing sort options inside the ``postgresql_ops`` dict is not supported.

    .. change::
        :tags: bug, operations
        :tickets: 1215

        Fixed issue where using a directive such as ``op.create_foreign_key()`` to
        create a self-referential constraint on a single table where the same
        column were present on both sides (e.g. within a composite foreign key)
        would produce an error under SQLAlchemy 2.0 and a warning under SQLAlchemy
        1.4 indicating that a duplicate column were being added to a table.

.. changelog::
    :version: 1.10.3
    :released: April 5, 2023

    .. change::
        :tags: bug, typing
        :tickets: 1191, 1201

        Fixed various typing issues observed with pyright, including issues
        involving the combination of :class:`.Function` and
        :meth:`.MigrationContext.begin_transaction`.

    .. change::
        :tags: bug, autogenerate
        :tickets: 1212

        Fixed error raised by alembic when running autogenerate after removing
        a function based index.

.. changelog::
    :version: 1.10.2
    :released: March 8, 2023

    .. change::
        :tags: bug, ops
        :tickets: 1196

        Fixed regression where Alembic would not run with older SQLAlchemy 1.3
        versions prior to 1.3.24 due to a missing symbol. Workarounds have been
        applied for older 1.3 versions.

.. changelog::
    :version: 1.10.1
    :released: March 6, 2023

    .. change::
        :tags: bug, postgresql
        :tickets: 1184

        Fixed issue regarding PostgreSQL :class:`.ExcludeConstraint`, where
        constraint elements which made use of :func:`.literal_column` could not be
        rendered for autogenerate. Additionally, using SQLAlchemy 2.0.5 or greater,
        :func:`.text()` constructs are also supported within PostgreSQL
        :class:`.ExcludeConstraint` objects for autogenerate render. Pull request
        courtesy Jan Katins.

    .. change::
        :tags: bug, batch, regression
        :tickets: 1195

        Fixed regression for 1.10.0 where :class:`.Constraint` objects were
        suddenly required to have non-None name fields when using batch mode, which
        was not previously a requirement.

.. changelog::
    :version: 1.10.0
    :released: March 5, 2023

    .. change::
        :tags: bug, autogenerate
        :tickets: 1166

        Fixed issue in index detection where autogenerate change detection would
        consider indexes with the same columns but with different order as equal,
        while in general they are not equivalent in how a database will use them.

    .. change::
        :tags: feature, revisioning
        :tickets: 760

        Recursive traversal of revision files in a particular revision directory is
        now supported, by indicating ``recursive_version_locations = true`` in
        alembic.ini. Pull request courtesy ostr00000.


    .. change::
        :tags: bug, autogenerate, sqlite
        :tickets: 1165

        Fixed issue where indexes on SQLite which include SQL expressions would not
        compare correctly, generating false positives under autogenerate. These
        indexes are now skipped, generating a warning, in the same way that
        expression-based indexes on PostgreSQL are skipped and generate warnings
        when SQLAlchemy 1.x installations are in use. Note that reflection of
        SQLite expression-based indexes continues to not yet be supported under
        SQLAlchemy 2.0, even though PostgreSQL expression-based indexes have now
        been implemented.



    .. change::
        :tags: bug, mssql
        :tickets: 1187

        Properly escape constraint name on SQL Server when dropping
        a column while specifying ``mssql_drop_default=True`` or
        ``mssql_drop_check=True`` or ``mssql_drop_foreign_key=True``.


    .. change::
        :tags: usecase, autogenerate, postgresql

        Added support for autogenerate comparison of indexes on PostgreSQL which
        include SQL expressions, when using SQLAlchemy 2.0; the previous warning
        that such indexes were skipped are removed when the new functionality
        is in use.  When using SQLAlchemy versions prior to the 2.0 series,
        the indexes continue to be skipped with a warning.

.. changelog::
    :version: 1.9.4
    :released: February 16, 2023

    .. change::
        :tags: bug, mssql
        :tickets: 1177

        Ongoing fixes for SQL Server server default comparisons under autogenerate,
        adjusting for SQL Server's collapsing of whitespace between SQL function
        arguments when reporting on a function-based server default, as well as its
        arbitrary addition of parenthesis within arguments; the approach has now
        been made more aggressive by stripping the two default strings to compare
        of all whitespace, parenthesis, and quoting characters.


    .. change::
        :tags: bug, postgresql

        Fixed PostgreSQL server default comparison to handle SQL expressions
        sent as ``text()`` constructs, such as ``text("substring('name', 1, 3)")``,
        which previously would raise errors when attempting to run a server-based
        comparison.



    .. change::
        :tags: bug, autogenerate
        :tickets: 1180

        Removed a mis-use of the
        :paramref:`.EnvironmentContext.configure.render_item` callable where the
        "server_default" renderer would be erroneously used within the server
        default comparison process, which is working against SQL expressions, not
        Python code.

    .. change::
        :tags: bug, commands

        Fixed regression introduced in 1.7.0 where the "config" object passed to
        the template context when running the :func:`.merge` command
        programmatically failed to be correctly populated. Pull request courtesy
        Brendan Gann.

.. changelog::
    :version: 1.9.3
    :released: February 7, 2023

    .. change::
        :tags: bug, autogenerate
        :tickets: 1167

        Fixed issue where rendering of user-defined types that then went onto use
        the ``.with_variant()`` method would fail to render, if using SQLAlchemy
        2.0's version of variants.


.. changelog::
    :version: 1.9.2
    :released: January 14, 2023

    .. change::
        :tags: bug, typing
        :tickets: 1146, 1147

        Fixed typing definitions for :meth:`.EnvironmentContext.get_x_argument`.

        Typing stubs are now generated for overloaded proxied methods such as
        :meth:`.EnvironmentContext.get_x_argument`.

    .. change::
        :tags: bug, autogenerate
        :tickets: 1152

        Fixed regression caused by :ticket:`1145` where the string transformations
        applied to server defaults caused expressions such as ``(getdate())`` to no
        longer compare as equivalent on SQL Server, others.

.. changelog::
    :version: 1.9.1
    :released: December 23, 2022

    .. change::
        :tags: bug, autogenerate
        :tickets: 1145

        Fixed issue where server default compare would not work for string defaults
        that contained backslashes, due to mis-rendering of these values when
        comparing their contents.


    .. change::
        :tags: bug, oracle

        Implemented basic server default comparison for the Oracle backend;
        previously, Oracle's formatting of reflected defaults prevented any
        matches from occurring.

    .. change::
        :tags: bug, sqlite

        Adjusted SQLite's compare server default implementation to better handle
        defaults with or without parens around them, from both the reflected and
        the local metadata side.

    .. change::
        :tags: bug, mssql

        Adjusted SQL Server's compare server default implementation to better
        handle defaults with or without parens around them, from both the reflected
        and the local metadata side.

.. changelog::
    :version: 1.9.0
    :released: December 15, 2022

    .. change::
        :tags: feature, commands
        :tickets: 724

        Added new Alembic command ``alembic check``. This performs the widely
        requested feature of running an "autogenerate" comparison between the
        current database and the :class:`.MetaData` that's currently set up for
        autogenerate, returning an error code if the two do not match, based on
        current autogenerate settings. Pull request courtesy Nathan Louie.

        .. seealso::

            :ref:`alembic_check`


    .. change::
        :tags: bug, tests

        Fixed issue in tox.ini file where changes in the tox 4.0 series to the
        format of "passenv" caused tox to not function correctly, in particular
        raising an error as of tox 4.0.6.

    .. change::
        :tags: bug, typing
        :tickets: 1110

        Fixed typing issue where :paramref:`.revision.process_revision_directives`
        was not fully typed; additionally ensured all ``Callable`` and ``Dict``
        arguments to :meth:`.EnvironmentContext.configure` include parameters in
        the typing declaration.

        Additionally updated the codebase for Mypy 0.990 compliance.

.. changelog::
    :version: 1.8.1
    :released: July 13, 2022

    .. change::
        :tags: bug, sqlite
        :tickets: 1065

        Fixed bug where the SQLite implementation of
        :meth:`.Operations.rename_table` would render an explicit schema name for
        both the old and new table name, which while is the standard ALTER syntax,
        is not accepted by SQLite's syntax which doesn't support a rename across
        schemas. In particular, the syntax issue would prevent batch mode from
        working for SQLite databases that made use of attached databases (which are
        treated as "schemas" in SQLAlchemy).

    .. change::
        :tags: bug, batch
        :tickets: 1021

        Added an error raise for the condition where
        :meth:`.Operations.batch_alter_table` is used in ``--sql`` mode, where the
        operation requires table reflection, as is the case when running against
        SQLite without giving it a fixed ``Table`` object. Previously the operation
        would fail with an internal error.   To get a "move and copy" batch
        operation as a SQL script without connecting to a database,
        a ``Table`` object should be passed to the
        :paramref:`.Operations.batch_alter_table.copy_from` parameter so that
        reflection may be skipped.

.. changelog::
    :version: 1.8.0
    :released: May 31, 2022

    .. change::
        :tags: feature, typing
        :tickets: 764

        :pep:`484` typing annotations have been added to the ``env.py`` and
        revision template files within migration templates. Pull request by Nikita
        Sobolev.

    .. change::
        :tags: usecase, operations
        :tickets: 1037

        The ``op.drop_table()`` operation directive will now trigger the
        ``before_drop()`` and ``after_drop()`` DDL event hooks at the table level,
        which is similar to how the ``before_create()`` and ``after_create()``
        hooks are triggered by the ``op.create_table()`` directive. Note that as
        ``op.drop_table()`` accepts only a table name and optional schema name, the
        ``Table`` object received by the event will not have any information within
        it other than the table name and schema name.

    .. change::
        :tags: installation, changed
        :tickets: 1025

        Alembic 1.8 now supports Python 3.7 and above.

    .. change::
        :tags: changed, environment
        :tickets: 987

        The "Pylons" environment template has been removed as of Alembic 1.8. This
        template was based on the very old pre-Pyramid Pylons web framework which
        has been long superseded by Pyramid.

    .. change::
        :tags: bug, revisioning
        :tickets: 1026

        Fixed issue where a downgrade using a relative revision would
        fail in case of multiple branches with a single effectively
        head due to interdependencies between revisions.

    .. change::
      :tags: usecase, commands
      :tickets: 1027

      Added new token ``epoch`` to the ``file_template`` option, which will
      populate the integer epoch as determined by ``int(create_date.timestamp())``.
      Pull request courtesy Caio Carvalho.

    .. change::
        :tags: bug, batch
        :tickets: 1034

        Fixed issue in batch mode where CREATE INDEX would not use a new column
        name in the case of a column rename.

.. changelog::
    :version: 1.7.7
    :released: March 14, 2022

    .. change::
        :tags: bug, operations
        :tickets: 1004

        Fixed issue where using :meth:`.Operations.create_table` in conjunction
        with a :class:`.CheckConstraint` that referred to table-bound
        :class:`.Column` objects rather than string expressions would be added to
        the parent table potentially multiple times, resulting in an incorrect DDL
        sequence. Pull request courtesy Nicolas CANIART.

    .. change::
        :tags: bug, environment
        :tickets: 986

        The ``logging.fileConfig()`` line in ``env.py`` templates, which is used
        to setup Python logging for the migration run, is now conditional on
        :attr:`.Config.config_file_name` not being ``None``.  Otherwise, the line
        is skipped as there is no default logging configuration present.


    .. change::
        :tags: bug, mssql
        :tickets: 977

        Fixed bug where an :meth:`.Operations.alter_column` operation would change
        a "NOT NULL" column to "NULL" by emitting an ALTER COLUMN statement that
        did not specify "NOT NULL". (In the absence of "NOT NULL" T-SQL was
        implicitly assuming "NULL"). An :meth:`.Operations.alter_column` operation
        that specifies :paramref:`.Operations.alter_column.type` should also
        specify include either :paramref:`.Operations.alter_column.nullable` or
        :paramref:`.Operations.alter_column.existing_nullable` to inform Alembic as
        to whether the emitted DDL should include "NULL" or "NOT NULL"; a warning
        is now emitted if this is missing under this scenario.

.. changelog::
    :version: 1.7.6
    :released: February 1, 2022

    .. change::
        :tags: bug, batch, regression
        :tickets: 982

        Fixed regression where usage of a ``with_variant()`` datatype in
        conjunction with the ``existing_type`` option of ``op.alter_column()``
        under batch mode would lead to an internal exception.

    .. change::
        :tags: usecase, commands
        :tickets: 964

        Add a new command ``alembic ensure_version``, which will ensure that the
        Alembic version table is present in the target database, but does not
        alter its contents.  Pull request courtesy Kai Mueller.

    .. change::
        :tags: bug, autogenerate

        Implemented support for recognizing and rendering SQLAlchemy "variant"
        types going forward into SQLAlchemy 2.0, where the architecture of
        "variant" datatypes will be changing.


    .. change::
        :tags: bug, mysql, autogenerate
        :tickets: 968

        Added a rule to the MySQL impl so that the translation between JSON /
        LONGTEXT is accommodated by autogenerate, treating LONGTEXT from the server
        as equivalent to an existing JSON in the model.

    .. change::
        :tags: mssql

        Removed a warning raised by SQLAlchemy when dropping constraints
        on MSSQL regarding statement caching.

.. changelog::
    :version: 1.7.5
    :released: November 11, 2021

    .. change::
        :tags: bug, tests

        Adjustments to the test suite to accommodate for error message changes
        occurring as of SQLAlchemy 1.4.27.

.. changelog::
    :version: 1.7.4
    :released: October 6, 2021

    .. change::
        :tags: bug, regression
        :tickets: 934

        Fixed a regression that prevented the use of post write hooks
        on python version lower than 3.9

    .. change::
        :tags: bug, environment
        :tickets: 944

        Fixed issue where the :meth:`.MigrationContext.autocommit_block` feature
        would fail to function when using a SQLAlchemy engine using 2.0 future
        mode.


.. changelog::
    :version: 1.7.3
    :released: September 17, 2021

    .. change::
        :tags: bug, mypy
        :tickets: 914

        Fixed type annotations for the "constraint_name" argument of operations
        ``create_primary_key()``, ``create_foreign_key()``.  Pull request courtesy
        TilmanK.


.. changelog::
    :version: 1.7.2
    :released: September 17, 2021

    .. change::
        :tags: bug, typing
        :tickets: 900

        Added missing attributes from context stubs.

    .. change::
        :tags: bug, mypy
        :tickets: 897

        Fixed an import in one of the .pyi files that was triggering an
        assertion error in some versions of mypy.

    .. change::
        :tags: bug, regression, ops
        :tickets: 920

        Fixed issue where registration of custom ops was prone to failure due to
        the registration process running ``exec()`` on generated code that as of
        the 1.7 series includes pep-484 annotations, which in the case of end user
        code would result in name resolution errors when the exec occurs. The logic
        in question has been altered so that the annotations are rendered as
        forward references so that the ``exec()`` can proceed.

.. changelog::
    :version: 1.7.1
    :released: August 30, 2021

    .. change::
        :tags: bug, installation
        :tickets: 893

        Corrected "universal wheel" directive in setup.cfg so that building a wheel
        does not target Python 2. The PyPi files index for 1.7.0 was corrected
        manually. Pull request courtesy layday.

    .. change::
        :tags: bug, pep484
        :tickets: 895

        Fixed issue in generated .pyi files where default values for ``Optional``
        arguments were missing, thereby causing mypy to consider them as required.


    .. change::
        :tags: bug, regression, batch
        :tickets: 896

        Fixed regression in batch mode due to :ticket:`883` where the "auto" mode
        of batch would fail to accommodate any additional migration directives
        beyond encountering an ``add_column()`` directive, due to a mis-application
        of the conditional logic that was added as part of this change, leading to
        "recreate" mode not being used in cases where it is required for SQLite
        such as for unique constraints.

.. changelog::
    :version: 1.7.0
    :released: August 30, 2021

    .. change::
        :tags: bug, operations
        :tickets: 879

        Fixed regression due to :ticket:`803` where the ``.info`` and ``.comment``
        attributes of ``Table`` would be lost inside of the :class:`.DropTableOp`
        class, which when "reversed" into a :class:`.CreateTableOp` would then have
        lost these elements. Pull request courtesy Nicolas CANIART.


    .. change::
        :tags: feature, environment
        :tickets: 842

        Enhance ``version_locations`` parsing to handle paths containing spaces.
        The new configuration option ``version_path_separator`` specifies the
        character to use when splitting the ``version_locations`` string. The
        default for new configurations is ``version_path_separator = os``,
        which will use ``os.pathsep`` (e.g., ``;`` on Windows).

    .. change::
        :tags: installation, changed

        Alembic 1.7 now supports Python 3.6 and above; support for prior versions
        including Python 2.7 has been dropped.

    .. change::
        :tags: bug, sqlite, batch
        :tickets: 883

        Batch "auto" mode will now select for "recreate" if the ``add_column()``
        operation is used on SQLite, and the column itself meets the criteria for
        SQLite where ADD COLUMN is not allowed, in this case a functional or
        parenthesized SQL expression or a ``Computed`` (i.e. generated) column.

    .. change::
        :tags: changed, installation
        :tickets: 674

        Make the ``python-dateutil`` library an optional dependency.
        This library is only required if the ``timezone`` option
        is used in the Alembic configuration.
        An extra require named ``tz`` is available with
        ``pip install alembic[tz]`` to install it.

    .. change::
        :tags: bug, commands
        :tickets: 856

        Re-implemented the ``python-editor`` dependency as a small internal
        function to avoid the need for external dependencies.

    .. change::
        :tags: usecase, batch
        :tickets: 884

        Named CHECK constraints are now supported by batch mode, and will
        automatically be part of the recreated table assuming they are named. They
        also can be explicitly dropped using ``op.drop_constraint()``. For
        "unnamed" CHECK constraints, these are still skipped as they cannot be
        distinguished from the CHECK constraints that are generated by the
        ``Boolean`` and ``Enum`` datatypes.

        Note that this change may require adjustments to migrations that drop or
        rename columns which feature an associated named check constraint, such
        that an additional ``op.drop_constraint()`` directive should be added for
        that named constraint as there will no longer be an associated column
        for it; for the ``Boolean`` and ``Enum`` datatypes, an ``existing_type``
        keyword may be passed to ``BatchOperations.drop_constraint`` as well.

        .. seealso::

          :ref:`batch_schematype_constraints`

          :ref:`batch_check_constraints`


    .. change::
        :tags: changed, installation
        :tickets: 885

        The dependency on ``pkg_resources`` which is part of ``setuptools`` has
        been removed, so there is no longer any runtime dependency on
        ``setuptools``. The functionality has been replaced with
        ``importlib.metadata`` and ``importlib.resources`` which are both part of
        Python std.lib, or via pypy dependency ``importlib-metadata`` for Python
        version < 3.8 and ``importlib-resources`` for Python version < 3.9
        (while importlib.resources was added to Python in 3.7, it did not include
        the "files" API until 3.9).

    .. change::
        :tags: feature, tests
        :tickets: 855

        Created a "test suite" similar to the one for SQLAlchemy, allowing
        developers of third-party dialects to test their code against a set of
        Alembic tests that have been specially selected to exercise
        back-end database operations. At the time of release,
        third-party dialects that have adopted the Alembic test suite to verify
        compatibility include
        `CockroachDB <https://pypi.org/project/sqlalchemy-cockroachdb/>`_ and
        `SAP ASE (Sybase) <https://pypi.org/project/sqlalchemy-sybase/>`_.

    .. change::
       :tags: bug, postgresql
       :tickets: 874

       Fixed issue where usage of the PostgreSQL ``postgresql_include`` option
       within a :meth:`.Operations.create_index` would raise a KeyError, as the
       additional column(s) need to be added to the table object used by the
       construct internally. The issue is equivalent to the SQL Server issue fixed
       in :ticket:`513`. Pull request courtesy Steven Bronson.

    .. change::
        :tags: feature, general

        pep-484 type annotations have been added throughout the library.
        Additionally, stub .pyi files have been added for the "dynamically"
        generated Alembic modules ``alembic.op`` and ``alembic.config``, which
        include complete function signatures and docstrings, so that the functions
        in these namespaces will have both IDE support (vscode, pycharm, etc) as
        well as support for typing tools like Mypy. The files themselves are
        statically generated from their source functions within the source tree.

.. changelog::
    :version: 1.6.5
    :released: May 27, 2021

    .. change::
        :tags: bug, autogenerate
        :tickets: 849

        Fixed issue where dialect-specific keyword arguments within the
        :class:`.DropIndex` operation directive would not render in the
        autogenerated Python code. As support was improved for adding dialect
        specific arguments to directives as part of :ticket:`803`, in particular
        arguments such as "postgresql_concurrently" which apply to the actual
        create/drop of the index, support was needed for these to render even in a
        drop index operation. Pull request courtesy Jet Zhou.

.. changelog::
    :version: 1.6.4
    :released: May 24, 2021

    .. change::
        :tags: bug, regression, op directives
        :tickets: 848

        Fixed regression caused by just fixed :ticket:`844` that scaled back the
        filter for ``unique=True/index=True`` too far such that these directives no
        longer worked for the ``op.create_table()`` op, this has been fixed.

.. changelog::
    :version: 1.6.3
    :released: May 21, 2021

    .. change::
        :tags: bug, regression, autogenerate
        :tickets: 844

        Fixed 1.6-series regression where ``UniqueConstraint`` and to a lesser
        extent ``Index`` objects would be doubled up in the generated model when
        the ``unique=True`` / ``index=True`` flags were used.

    .. change::
        :tags: bug, autogenerate
        :tickets: 839

        Fixed a bug where paths defined in post-write hook options
        would be wrongly escaped in non posix environment (Windows).

    .. change::
        :tags: bug, regression, versioning
        :tickets: 843

        Fixed regression where a revision file that contained its own down revision
        as a dependency would cause an endless loop in the traversal logic.

.. changelog::
    :version: 1.6.2
    :released: May 6, 2021

    .. change::
        :tags: bug, versioning, regression
        :tickets: 839

        Fixed additional regression nearly the same as that of :ticket:`838` just
        released in 1.6.1 but within a slightly different codepath, where "alembic
        downgrade head" (or equivalent) would fail instead of iterating no
        revisions.

.. changelog::
    :version: 1.6.1
    :released: May 6, 2021

    .. change::
        :tags: bug, versioning, regression
        :tickets: 838

        Fixed regression in new revisioning traversal where "alembic downgrade
        base" would fail if the database itself were clean and unversioned;
        additionally repairs the case where downgrade would fail if attempting
        to downgrade to the current head that is already present.

.. changelog::
    :version: 1.6.0
    :released: May 3, 2021

    .. change::
        :tags: bug, autogenerate
        :tickets: 803

        Refactored the implementation of :class:`.MigrateOperation` constructs such
        as :class:`.CreateIndexOp`, :class:`.CreateTableOp`, etc. so that they no
        longer rely upon maintaining a persistent version of each schema object
        internally; instead, the state variables of each operation object will be
        used to produce the corresponding construct when the operation is invoked.
        The rationale is so that environments which make use of
        operation-manipulation schemes such as those discussed in
        :ref:`autogen_rewriter` are better supported, allowing end-user code to
        manipulate the public attributes of these objects which will then be
        expressed in the final output, an example is
        ``some_create_index_op.kw["postgresql_concurrently"] = True``.

        Previously, these objects when generated from autogenerate would typically
        hold onto the original, reflected element internally without honoring the
        other state variables of each construct, preventing the public API from
        working.



    .. change::
        :tags: bug, environment
        :tickets: 829

        Fixed regression caused by the SQLAlchemy 1.4/2.0 compatibility switch
        where calling ``.rollback()`` or ``.commit()`` explicitly within the
        ``context.begin_transaction()`` context manager would cause it to fail when
        the block ended, as it did not expect that the transaction was manually
        closed.

    .. change::
        :tags: bug, autogenerate
        :tickets: 827

        Improved the rendering of ``op.add_column()`` operations when adding
        multiple columns to an existing table, so that the order of these
        statements matches the order in which the columns were declared in the
        application's table metadata. Previously the added columns were being
        sorted alphabetically.


    .. change::
        :tags: feature, autogenerate
        :tickets: 819

        Fix the documentation regarding the default command-line argument position of
        the revision script filename within the post-write hook arguments. Implement a
        ``REVISION_SCRIPT_FILENAME`` token, enabling the position to be changed. Switch
        from ``str.split()`` to ``shlex.split()`` for more robust command-line argument
        parsing.

    .. change::
        :tags: feature
        :tickets: 822

        Implement a ``.cwd`` (current working directory) suboption for post-write hooks
        (of type ``console_scripts``). This is useful for tools like pre-commit, which
        rely on the working directory to locate the necessary config files. Add
        pre-commit as an example to the documentation. Minor change: rename some variables
        from ticket #819 to improve readability.

    .. change::
        :tags: bug, versioning
        :tickets: 765, 464

        The algorithm used for calculating downgrades/upgrades/iterating
        revisions has been rewritten, to resolve ongoing issues of branches
        not being handled consistently particularly within downgrade operations,
        as well as for overall clarity and maintainability.  This change includes
        that a deprecation warning is emitted if an ambiguous command such
        as "downgrade -1" when multiple heads are present is given.

        In particular, the change implements a long-requested use case of allowing
        downgrades of a single branch to a branchpoint.

        Huge thanks to Simon Bowly for their impressive efforts in successfully
        tackling this very difficult problem.

    .. change::
        :tags: bug, batch
        :tickets: 799

        Added missing ``batch_op.create_table_comment()``,
        ``batch_op.drop_table_comment()`` directives to batch ops.

.. changelog::
    :version: 1.5.8
    :released: March 23, 2021

    .. change::
        :tags: bug, environment
        :tickets: 816

        Fixed regression caused by SQLAlchemy 1.4 where the "alembic current"
        command would fail due to changes in the ``URL`` object.


.. changelog::
    :version: 1.5.7
    :released: March 11, 2021

    .. change::
        :tags: bug, autogenerate
        :tickets: 813

        Adjusted the recently added
        :paramref:`.EnvironmentContext.configure.include_name` hook to accommodate
        for additional object types such as "views" that don't have a parent table,
        to support third party recipes and extensions. Pull request courtesy Oliver
        Rice.

.. changelog::
    :version: 1.5.6
    :released: March 5, 2021

    .. change::
        :tags: bug, mssql, operations
        :tickets: 812

        Fixed bug where the "existing_type" parameter, which the MSSQL dialect
        requires in order to change the nullability of a column in the absence of
        also changing the column type, would cause an ALTER COLUMN operation to
        incorrectly render a second ALTER statement without the nullability if a
        new type were also present, as the MSSQL-specific contract did not
        anticipate all three of "nullability", ``"type_"`` and "existing_type" being
        sent at the same time.


    .. change::
        :tags: template
        :ticket: 805

        Add async template to Alembic to bootstrap environments that use
        async DBAPI. Updated the cookbook to include a migration guide
        on how to adapt an existing environment for use with DBAPI drivers.

.. changelog::
    :version: 1.5.5
    :released: February 20, 2021

    .. change::
        :tags: bug

        Adjusted the use of SQLAlchemy's ".copy()" internals to use "._copy()"
        for version 1.4.0, as this method is being renamed.

    .. change::
        :tags: bug, environment
        :tickets: 797

        Added new config file option ``prepend_sys_path``, which is a series of
        paths that will be prepended to sys.path; the default value in newly
        generated alembic.ini files is ".".  This fixes a long-standing issue
        where for some reason running the alembic command line would not place the
        local "." path in sys.path, meaning an application locally present in "."
        and importable through normal channels, e.g. python interpreter, pytest,
        etc. would not be located by Alembic, even though the ``env.py`` file is
        loaded relative to the current path when ``alembic.ini`` contains a
        relative path. To enable for existing installations, add the option to the
        alembic.ini file as follows::

          # sys.path path, will be prepended to sys.path if present.
          # defaults to the current working directory.
          prepend_sys_path = .

        .. seealso::

            :ref:`installation` - updated documentation reflecting that local
            installation of the project is not necessary if running the Alembic cli
            from the local path.


.. changelog::
    :version: 1.5.4
    :released: February 3, 2021

    .. change::
        :tags: bug, versioning
        :tickets: 789

        Fixed bug in versioning model where a downgrade across a revision with a
        dependency on another branch, yet an ancestor is also dependent on that
        branch, would produce an erroneous state in the alembic_version table,
        making upgrades impossible without manually repairing the table.

.. changelog::
    :version: 1.5.3
    :released: January 29, 2021

    .. change::
        :tags: bug, autogenerate
        :tickets: 786

        Changed the default ordering of "CREATE" and "DROP" statements indexes and
        unique constraints within the autogenerate process, so that for example in
        an upgrade() operation, a particular index or constraint that is to be
        replaced such as for a casing convention change will not produce any naming
        conflicts. For foreign key constraint objects, this is already how
        constraints are ordered, and for table objects, users would normally want
        to use :meth:`.Operations.rename_table` in any case.

    .. change::
        :tags: bug, autogenerate, mssql
        :tickets: 787

        Fixed assorted autogenerate issues with SQL Server:

        * ignore default reflected identity on primary_key columns
        * improve server default comparison

    .. change::
        :tags: bug, mysql, autogenerate
        :tickets: 788

        Fixed issue where autogenerate rendering of ``op.alter_column()`` would
        fail to include MySQL ``existing_nullable=False`` if the column were part
        of a primary key constraint within the table metadata.

.. changelog::
    :version: 1.5.2
    :released: January 20, 2021

    .. change::
        :tags: bug, versioning, regression
        :tickets: 784

        Fixed regression where new "loop detection" feature introduced in
        :ticket:`757` produced false positives for revision names that have
        overlapping substrings between revision number and down revision and/or
        dependency, if the downrev/dependency were not in sequence form.

    .. change::
        :tags: bug, environment
        :tickets: 782

        Fixed regression where Alembic would fail to create a transaction properly
        if the :class:`sqlalchemy.engine.Connection` were a so-called "branched"
        connection, that is, one where the ``.connect()`` method had been called to
        create a "sub" connection.

.. changelog::
    :version: 1.5.1
    :released: January 19, 2021

    .. change::
        :tags: bug, installation, commands
        :tickets: 780

        Fixed installation issue where the "templates" directory was not being
        installed, preventing commands like "list_templates" and "init" from
        working.

.. changelog::
    :version: 1.5.0
    :released: January 18, 2021

    .. change::
        :tags: usecase, operations
        :tickets: 730

        Added support for rendering of "identity" elements on
        :class:`.Column` objects, supported in SQLAlchemy via
        the :class:`.Identity` element introduced in version 1.4.

        Adding columns with identity is supported on PostgreSQL,
        MSSQL and Oracle. Changing the identity options or removing
        it is supported only on PostgreSQL and Oracle.

    .. change::
        :tags: changed, environment

        To accommodate SQLAlchemy 1.4 and 2.0, the migration model now no longer
        assumes that the SQLAlchemy Connection will autocommit an individual
        operation.   This essentially means that for databases that use
        non-transactional DDL (pysqlite current driver behavior, MySQL), there is
        still a BEGIN/COMMIT block that will surround each individual migration.
        Databases that support transactional DDL should continue to have the
        same flow, either per migration or per-entire run, depending on the
        value of the :paramref:`.Environment.configure.transaction_per_migration`
        flag.


    .. change::
        :tags: changed, environment

        A :class:`.CommandError` is raised if a ``sqlalchemy.engine.Engine`` is
        passed to the :meth:`.MigrationContext.configure` method instead of a
        ``sqlalchemy.engine.Connection`` object.  Previously, this would be a
        warning only.

    .. change::
        :tags: bug, operations
        :tickets: 753

        Modified the ``add_column()`` operation such that the ``Column`` object in
        use is shallow copied to a new instance if that ``Column`` is already
        attached to a ``table()`` or ``Table``. This accommodates for the change
        made in SQLAlchemy issue #5618 which prohibits a ``Column`` from being
        associated with multiple ``table()`` objects. This resumes support for
        using a ``Column`` inside of an Alembic operation that already refers to a
        parent ``table()`` or ``Table`` as well as allows operation objects just
        autogenerated to work.

    .. change::
        :tags: feature, autogenerate
        :tickets: 650

        Added new hook :paramref:`.EnvironmentContext.configure.include_name`,
        which complements the
        :paramref:`.EnvironmentContext.configure.include_object` hook by providing
        a means of preventing objects of a certain name from being autogenerated
        **before** the SQLAlchemy reflection process takes place, and notably
        includes explicit support for passing each schema name when
        :paramref:`.EnvironmentContext.configure.include_schemas` is set to True.
        This is most important especially for environments that make use of
        :paramref:`.EnvironmentContext.configure.include_schemas` where schemas are
        actually databases (e.g. MySQL) in order to prevent reflection sweeps of
        the entire server.

        .. seealso::

            :ref:`autogenerate_include_hooks` - new documentation section

    .. change::
        :tags: removed, autogenerate

        The long deprecated
        :paramref:`.EnvironmentContext.configure.include_symbol` hook is removed.
        The  :paramref:`.EnvironmentContext.configure.include_object`
        and  :paramref:`.EnvironmentContext.configure.include_name`
        hooks both achieve the goals of this hook.


    .. change::
        :tags: bug, autogenerate
        :tickets: 721

        Added rendering for the ``Table.prefixes`` element to autogenerate so that
        the rendered Python code includes these directives. Pull request courtesy
        Rodrigo Ce Moretto.

    .. change::
        :tags: bug, batch
        :tickets: 761

        Added missing "create comment" feature for columns that are altered in
        batch migrations.


    .. change::
        :tags: changed
        :tickets: 748

        Alembic 1.5.0 now supports **Python 2.7 and Python 3.6 and above**, as well
        as **SQLAlchemy 1.3.0 and above**.  Support is removed for Python 3
        versions prior to 3.6 and SQLAlchemy versions prior to the 1.3 series.

    .. change::
        :tags: bug, batch
        :tickets: 773

        Made an adjustment to the PostgreSQL dialect to allow it to work more
        effectively in batch mode, where a datatype like Boolean or non-native Enum
        that may have embedded rules to generate CHECK constraints will be more
        correctly handled in that these constraints usually will not have been
        generated on the PostgreSQL backend; previously it would inadvertently
        assume they existed unconditionally in a special PG-only "drop constraint"
        step.


    .. change::
        :tags: feature, versioning
        :tickets: 757

        The revision tree is now checked for cycles and loops between revision
        files when the revision environment is loaded up.  Scenarios such as a
        revision pointing to itself, or a revision that can reach itself via a
        loop, are handled and will raise the :class:`.CycleDetected` exception when
        the environment is loaded (expressed from the Alembic commandline as a
        failure message and nonzero return code). Previously, these situations were
        silently ignored up front, and the behavior of revision traversal would
        either be silently incorrect, or would produce errors such as
        :class:`.RangeNotAncestorError`.  Pull request courtesy Koichiro Den.


    .. change::
        :tags: usecase, commands

        Add ``__main__.py`` file to alembic package to support invocation
        with ``python -m alembic``.

    .. change::
        :tags: removed, commands

        Removed deprecated ``--head_only`` option to the ``alembic current``
        command

    .. change::
        :tags: removed, operations

        Removed legacy parameter names from operations, these have been emitting
        warnings since version 0.8.  In the case that legacy version files have not
        yet been updated, these can be modified directly in order to maintain
        compatibility:

        * :meth:`.Operations.drop_constraint` - "type" (use ``"type_"``) and "name"
          (use "constraint_name")

        * :meth:`.Operations.create_primary_key` - "cols" (use "columns") and
          "name" (use "constraint_name")

        * :meth:`.Operations.create_unique_constraint` - "name" (use
          "constraint_name"), "source" (use "table_name") and "local_cols" (use
          "columns")

        * :meth:`.Operations.batch_create_unique_constraint` - "name" (use
          "constraint_name")

        * :meth:`.Operations.create_foreign_key` - "name" (use "constraint_name"),
          "source" (use "source_table"), "referent" (use "referent_table")

        * :meth:`.Operations.batch_create_foreign_key` - "name" (use
          "constraint_name"), "referent" (use "referent_table")

        * :meth:`.Operations.create_check_constraint` - "name" (use
          "constraint_name"), "source" (use "table_name")

        * :meth:`.Operations.batch_create_check_constraint` - "name" (use
          "constraint_name")

        * :meth:`.Operations.create_index` - "name" (use "index_name")

        * :meth:`.Operations.drop_index` - "name" (use "index_name"), "tablename"
          (use "table_name")

        * :meth:`.Operations.batch_drop_index` - "name" (use "index_name"),

        * :meth:`.Operations.create_table` - "name" (use "table_name")

        * :meth:`.Operations.drop_table` - "name" (use "table_name")

        * :meth:`.Operations.alter_column` - "name" (use "new_column_name")



.. changelog::
    :version: 1.4.3
    :released: September 11, 2020

    .. change::
        :tags: bug, sqlite, batch
        :tickets: 711

        Added support to drop named CHECK constraints that are specified as part of
        a column, rather than table wide.  Previously, only constraints associated
        with the table were considered.

    .. change::
        :tags: bug, ops, mysql
        :tickets: 736

        Fixed issue where the MySQL dialect would not correctly render the server
        default of a column in an alter operation, if the operation were
        programmatically generated from an autogenerate pass as it would not
        accommodate for the full structure of the DefaultClause construct.

    .. change::
        :tags: bug, sqlite, batch
        :tickets: 697

        Fixed issue where the CAST applied to a JSON column when copying a SQLite
        table during batch mode would cause the data to be lost, as SQLite's CAST
        with JSON appears to convert the data to the value "0". The CAST is now
        skipped in a dialect-specific manner, including for JSON columns on SQLite.
        Pull request courtesy Sebastián Ramírez.

    .. change::
        :tags: bug, commands
        :tickets: 694

        The ``alembic current`` command no longer creates an ``alembic_version``
        table in the database if one does not exist already, returning no version
        as the current version. This allows checking for migrations in parallel
        without introducing race conditions.  Pull request courtesy Nikolay
        Edigaryev.


    .. change::
        :tags: bug, batch

        Fixed issue where columns in a foreign-key referenced table would be
        replaced with null-type columns during a batch operation; while this did
        not generally have any side effects, it could theoretically impact a batch
        operation that also targets that table directly and also would interfere
        with future changes to the ``.append_column()`` method to disallow implicit
        replacement of columns.

    .. change::
       :tags: bug, mssql
       :tickets: 716

       Fixed issue where the ``mssql_drop_foreign_key=True`` flag on
       ``op.drop_column`` would lead to incorrect syntax error due to a typo in the
       SQL emitted, same typo was present in the test as well so it was not
       detected. Pull request courtesy Oleg Shigorin.

.. changelog::
    :version: 1.4.2
    :released: March 19, 2020

    .. change::
        :tags: usecase, autogenerate
        :tickets: 669

        Adjusted autogen comparison to accommodate for backends that support
        computed column reflection, dependent on SQLAlchemy version 1.3.16 or
        higher. This emits a warning if the SQL expression inside of a
        :class:`.Computed` value changes between the metadata and the database, as
        these expressions can't be changed without dropping and recreating the
        column.


    .. change::
        :tags: bug, tests
        :tickets: 668

        Fixed an issue that prevented the test suite from running with the
        recently released py.test 5.4.0.


    .. change::
        :tags: bug, autogenerate, mysql
        :tickets: 671

        Fixed more false-positive failures produced by the new "compare type" logic
        first added in :ticket:`605`, particularly impacting MySQL string types
        regarding flags such as "charset" and "collation".

    .. change::
        :tags: bug, op directives, oracle
        :tickets: 670

        Fixed issue in Oracle backend where a table RENAME with a schema-qualified
        name would include the schema in the "to" portion, which is rejected by
        Oracle.


.. changelog::
    :version: 1.4.1
    :released: March 1, 2020

    .. change::
        :tags: bug, autogenerate
        :tickets: 661

        Fixed regression caused by the new "type comparison" logic introduced in
        1.4 as part of :ticket:`605` where comparisons of MySQL "unsigned integer"
        datatypes would produce false positives, as the regular expression logic
        was not correctly parsing the "unsigned" token when MySQL's default display
        width would be returned by the database.  Pull request courtesy Paul
        Becotte.

    .. change::
        :tags: bug, environment
        :tickets: 663

        Error message for "path doesn't exist" when loading up script environment
        now displays the absolute path.  Pull request courtesy Rowan Hart.

    .. change::
        :tags: bug, autogenerate
        :tickets: 654

        Fixed regression in 1.4.0 due to :ticket:`647` where unique constraint
        comparison with mixed case constraint names while not using a naming
        convention would produce false positives during autogenerate.

    .. change::
        :tags: bug, environment

        The check for matched rowcount when the alembic_version table is updated or
        deleted from is now conditional based on whether or not the dialect
        supports the concept of "rowcount" for UPDATE or DELETE rows matched.  Some
        third party dialects do not support this concept.  Pull request courtesy Ke
        Zhu.

    .. change::
        :tags: bug, operations
        :tickets: 655

        Fixed long-standing bug where an inline column CHECK constraint would not
        be rendered within an "ADD COLUMN" operation.  The DDL compiler is now
        consulted for inline constraints within the :meth:`.Operations.add_column`
        method as is done for regular CREATE TABLE operations.



.. changelog::
    :version: 1.4.0
    :released: February 4, 2020

    .. change::
        :tags: change

        The internal inspection routines no longer use SQLAlchemy's
        ``Inspector.from_engine()`` method, which is expected to be deprecated in
        1.4.  The ``inspect()`` function is now used.


    .. change::
        :tags: bug, autogenerate
        :tickets: 647

        Adjusted the unique constraint comparison logic in a similar manner as that
        of :ticket:`421` did for indexes in order to take into account SQLAlchemy's
        own truncation of long constraint names when a naming convention is in use.
        Without this step, a name that is truncated by SQLAlchemy based on a unique
        constraint naming convention or hardcoded name will not compare properly.


    .. change::
        :tags: feature, batch
        :tickets: 640

        Added new parameters :paramref:`.BatchOperations.add_column.insert_before`,
        :paramref:`.BatchOperations.add_column.insert_after` which provide for
        establishing the specific position in which a new column should be placed.
        Also added :paramref:`.Operations.batch_alter_table.partial_reordering`
        which allows the complete set of columns to be reordered when the new table
        is created.   Both operations apply only to when batch mode is recreating
        the whole table using ``recreate="always"``.  Thanks to Marcin Szymanski
        for assistance with the implementation.

    .. change::
        :tags: usecase, environment
        :tickets: 648

        Moved the use of the ``__file__`` attribute at the base of the Alembic
        package into the one place that it is specifically needed, which is when
        the config attempts to locate the template directory. This helps to allow
        Alembic to be fully importable in environments that are using Python
        memory-only import schemes.  Pull request courtesy layday.

    .. change::
        :tags: bug, autogenerate
        :tickets: 605

        A major rework of the "type comparison" logic is in place which changes the
        entire approach by which column datatypes are compared.  Types are now
        compared based on the DDL string generated by the metadata type vs. the
        datatype reflected from the database.  This means we compare types based on
        what would actually render and additionally if elements of the types change
        like string length, those changes are detected as well.  False positives
        like those generated between SQLAlchemy Boolean and MySQL TINYINT should
        also be resolved.   Thanks very much to Paul Becotte  for lots of hard work
        and patience on this one.

        .. note:: *updated* - this change also removes support for the
           ``compare_against_backend`` SQLAlchemy type hook.

        .. seealso::

            :ref:`autogenerate_detects` - updated comments on type comparison

.. changelog::
    :version: 1.3.3
    :released: January 22, 2020

    .. change::
        :tags: bug, postgresql
        :tickets: 637

        Fixed issue where COMMENT directives for PostgreSQL failed to correctly
        include an explicit schema name, as well as correct quoting rules for
        schema, table, and column names.  Pull request courtesy Matthew Sills.

    .. change::
        :tags: usecase, operations
        :tickets: 624

        Added support for rendering of "computed" elements on :class:`.Column`
        objects, supported in SQLAlchemy via the new :class:`.Computed` element
        introduced in version 1.3.11. Pull request courtesy Federico Caselli.

        Note that there is currently no support for ALTER COLUMN to add, remove, or
        modify the "GENERATED ALWAYS AS" element from a column;  at least for
        PostgreSQL, it does not seem to be supported by the database. Additionally,
        SQLAlchemy does not currently reliably reflect the "GENERATED ALWAYS AS"
        phrase from an existing column, so there is also no autogenerate support
        for addition or removal of the :class:`.Computed` element to or from an
        existing column, there is only support for adding new columns that include
        the :class:`.Computed` element.  In the case that the :class:`.Computed`
        element is removed from the :class:`.Column` object in the table metadata,
        PostgreSQL and Oracle currently reflect the "GENERATED ALWAYS AS"
        expression as the "server default" which will produce an op that tries to
        drop the element as a default.

.. changelog::
    :version: 1.3.2
    :released: December 16, 2019

    .. change::
        :tags: bug, api, autogenerate
        :tickets: 635

        Fixed regression introduced by :ticket:`579` where server default rendering
        functions began to require a dialect implementation, however the
        :func:`.render_python_code` convenience function did not include one, thus
        causing the function to fail when used in a server default context.  The
        function now accepts a migration context argument and also creates one
        against the default dialect if one is not provided.


.. changelog::
    :version: 1.3.1
    :released: November 13, 2019

    .. change::
        :tags: bug, mssql
        :tickets: 621

        Fixed bug in MSSQL dialect where the drop constraint execution steps used
        to remove server default or implicit foreign key constraint failed to take
        into account the schema name of the target table.


.. changelog::
    :version: 1.3.0
    :released: October 31, 2019

    .. change::
        :tags: feature, command
        :tickets: 608

        Added support for ALEMBIC_CONFIG environment variable,
        refers to the location of the alembic configuration script
        in lieu of using the -c command line option.


    .. change::
        :tags: bug, autogenerate
        :tickets: 131

        Fixed bug in new Variant autogenerate where the order of the arguments to
        Variant were mistakenly reversed.

    .. change::
        :tags: change, compatibility

        Some internal modifications have been made to how the names of indexes and
        unique constraints work to make use of new functions added in SQLAlchemy
        1.4, so that SQLAlchemy has more flexibility over how naming conventions
        may be applied to these objects.

.. changelog::
    :version: 1.2.1
    :released: September 24, 2019

    .. change::
        :tags: bug, command
        :tickets: 601

        Reverted the name change of the "revisions" argument to
        :func:`.command.stamp` to "revision" as apparently applications are
        calling upon this argument as a keyword name.  Pull request courtesy
        Thomas Bechtold.  Special translations are also added to the command
        line interface so that it is still known as "revisions" in the CLI.

    .. change::
        :tags: bug, tests
        :tickets: 592

        Removed the "test requirements" from "setup.py test", as this command now
        only emits a removal error in any case and these requirements are unused.

.. changelog::
    :version: 1.2.0
    :released: September 20, 2019

    .. change::
        :tags: feature, command
        :tickets: 473

        Added new ``--purge`` flag to the ``alembic stamp`` command, which will
        unconditionally erase the version table before stamping anything.  This is
        useful for development where non-existent version identifiers might be left
        within the table.  Additionally, ``alembic.stamp`` now supports a list of
        revision identifiers, which are intended to allow setting up multiple heads
        at once.  Overall handling of version identifiers within the
        ``alembic.stamp`` command has been improved with many new tests and
        use cases added.

    .. change::
        :tags: bug, autogenerate
        :tickets: 550

        Improved the Python rendering of a series of migration operations such that
        a single "pass" is rendered for a :class:`.UpgradeOps` or
        :class:`.DowngradeOps` based on if no lines of Python code actually
        rendered under the operation, rather than whether or not sub-directives
        exist. Removed extra "pass" lines that would generate from the
        :class:`.ModifyTableOps` directive so that these aren't duplicated under
        operation rewriting scenarios.


    .. change::
        :tags: feature, runtime
        :tickets: 123

        Added new feature :meth:`.MigrationContext.autocommit_block`, a special
        directive which will provide for a non-transactional block inside of a
        migration script. The feature requires that: the database driver
        (e.g. DBAPI) supports the AUTOCOMMIT isolation mode.  The directive
        also necessarily needs to COMMIT the existing transaction in progress
        in order to enter autocommit mode.

        .. seealso::

            :meth:`.MigrationContext.autocommit_block`

    .. change::
        :tags: change: py3k

        Python 3.4 support is dropped, as the upstream tooling (pip, mysqlclient)
        etc are already dropping support for Python 3.4, which itself is no longer
        maintained.

    .. change::
        :tags: usecase, autogenerate
        :tickets: 518

        Added autogenerate support for :class:`.Column` objects that have
        dialect-specific ``**kwargs``, support first added in SQLAlchemy 1.3.
        This includes SQLite "on conflict" as well as options used by some
        third party dialects.

    .. change::
        :tags: usecase, autogenerate
        :tickets: 131

        Added rendering for SQLAlchemy ``Variant`` datatypes, which render as the
        base type plus one or more ``.with_variant()`` method calls.


    .. change::
        :tags: usecase, commands
        :tickets: 534

        Made the command interface revision lookup behavior more strict in that an
        Alembic revision number is only resolved based on a partial match rules if
        it has at least four characters, to prevent simple typographical issues
        from inadvertently  running migrations.

     .. change::
        :tags: feature, commands
        :tickets: 307

        Added "post write hooks" to revision generation.  These allow custom logic
        to run after a revision Python script is generated, typically for the
        purpose of running code formatters such as "Black" or "autopep8", but may
        be used for any arbitrary post-render hook as well, including custom Python
        functions or scripts.  The hooks are enabled by providing a
        ``[post_write_hooks]`` section in the alembic.ini file.  A single hook
        is provided which runs an arbitrary Python executable on the newly
        generated revision script, which can be configured to run code formatters
        such as Black; full examples are included in the documentation.

        .. seealso::

            :ref:`post_write_hooks`


    .. change::
        :tags: feature, environment
        :tickets: 463

        Added new flag ``--package`` to ``alembic init``.  For environments where
        the Alembic migration files and such are within the package tree and
        importable as modules, this flag can be specified which will add the
        additional ``__init__.py`` files in the version location and the
        environment location.

    .. change::
        :tags: bug, autogenerate
        :tickets: 549

        Fixed bug where rendering of comment text for table-level comments  within
        :meth:`.Operations.create_table_comment` and
        :meth:`.Operations.drop_table_comment` was not properly quote-escaped
        within rendered Python code for autogenerate.

    .. change::
        :tags: bug, autogenerate
        :tickets: 505

        Modified the logic of the :class:`.Rewriter` object such that it keeps a
        memoization of which directives it has processed, so that it can ensure it
        processes a particular directive only once, and additionally fixed
        :class:`.Rewriter` so that it functions correctly for multiple-pass
        autogenerate schemes, such as the one illustrated in the "multidb"
        template.  By tracking which directives have been processed, a
        multiple-pass scheme which calls upon the :class:`.Rewriter` multiple times
        for the same structure as elements are added can work without running
        duplicate operations on the same elements more than once.

.. changelog::
    :version: 1.1.0
    :released: August 26, 2019

    .. change::
        :tags: change

        Alembic 1.1 bumps the minimum version of SQLAlchemy to 1.1.   As was the
        case before, Python requirements remain at Python 2.7, or in the 3.x series
        Python 3.4.

    .. change::
        :tags: change, internals

        The test suite for Alembic now makes use of SQLAlchemy's testing framework
        directly.  Previously, Alembic had its own version of this framework that
        was mostly copied from that of SQLAlchemy to enable testing with older
        SQLAlchemy versions.  The majority of this code is now removed so that both
        projects can leverage improvements from a common testing framework.

    .. change::
        :tags: bug, commands
        :tickets: 562

        Fixed bug where the double-percent logic applied to some dialects such as
        psycopg2 would be rendered in ``--sql`` mode, by allowing dialect options
        to be passed through to the dialect used to generate SQL and then providing
        ``paramstyle="named"`` so that percent signs need not be doubled.   For
        users having this issue, existing env.py scripts need to add
        ``dialect_opts={"paramstyle": "named"}`` to their offline
        context.configure().  See the ``alembic/templates/generic/env.py`` template
        for an example.

    .. change::
        :tags: bug, py3k

        Fixed use of the deprecated "imp" module, which is used to detect  pep3147
        availability as well as to locate .pyc files, which started  emitting
        deprecation warnings during the test suite.   The warnings were not being
        emitted earlier during the test suite, the change is possibly due to
        changes in py.test itself but this is not clear. The check for pep3147 is
        set to True for any Python version 3.5 or greater now and importlib is used
        when available.  Note that some dependencies such as distutils may still be
        emitting this warning. Tests are adjusted to accommodate for dependencies
        that emit the warning as well.


    .. change::
        :tags: bug, mysql
        :tickets: 594

        Fixed issue where emitting a change of column name for MySQL did not
        preserve the column comment, even if it were specified as existing_comment.


    .. change::
        :tags: bug, setup
        :tickets: 592

        Removed the "python setup.py test" feature in favor of a straight run of
        "tox".   Per Pypa / pytest developers, "setup.py" commands are in general
        headed towards deprecation in favor of tox.  The tox.ini script has been
        updated such that running "tox" with no arguments will perform a single run
        of the test suite against the default installed Python interpreter.

        .. seealso::

            https://github.com/pypa/setuptools/issues/1684

            https://github.com/pytest-dev/pytest/issues/5534

    .. change::
        :tags: usecase, commands
        :tickets: 571

        The "alembic init" command will now proceed if the target directory exists
        as long as it's still empty.  Previously, it would not proceed if the
        directory existed. The new behavior is modeled from what git does, to
        accommodate for container or other deployments where an Alembic target
        directory may need to be already mounted instead of being created with
        alembic init.  Pull request courtesy Aviskar KC.



.. changelog::
    :version: 1.0.11
    :released: June 25, 2019

    .. change::
        :tags: bug, sqlite, autogenerate, batch
        :tickets: 579

        SQLite server default reflection will ensure parenthesis are surrounding a
        column default expression that is detected as being a non-constant
        expression, such as a ``datetime()`` default, to accommodate for the
        requirement that SQL expressions have to be parenthesized when being sent
        as DDL.  Parenthesis are not added to constant expressions to allow for
        maximum cross-compatibility with other dialects and existing test suites
        (such as Alembic's), which necessarily entails scanning the expression to
        eliminate for constant numeric and string values. The logic is added to the
        two "reflection->DDL round trip" paths which are currently autogenerate and
        batch migration.  Within autogenerate, the logic is on the rendering side,
        whereas in batch the logic is installed as a column reflection hook.


    .. change::
        :tags: bug, sqlite, autogenerate
        :tickets: 579

        Improved SQLite server default comparison to accommodate for a ``text()``
        construct that added parenthesis directly vs. a construct that relied
        upon the SQLAlchemy SQLite dialect to render the parenthesis, as well
        as improved support for various forms of constant expressions such as
        values that are quoted vs. non-quoted.


    .. change::
        :tags: bug, autogenerate

        Fixed bug where the "literal_binds" flag was not being set when
        autogenerate would create a server default value, meaning server default
        comparisons would fail for functions that contained literal values.

    .. change::
       :tags: bug, mysql
       :tickets: 554

       Added support for MySQL "DROP CHECK", which is added as of MySQL 8.0.16,
       separate from MariaDB's "DROP CONSTRAINT" for CHECK constraints.  The MySQL
       Alembic implementation now checks for "MariaDB" in server_version_info to
       decide which one to use.



    .. change::
        :tags: bug, mysql, operations
        :tickets: 564

        Fixed issue where MySQL databases need to use CHANGE COLUMN when altering a
        server default of CURRENT_TIMESTAMP, NOW() and probably other functions
        that are only usable with DATETIME/TIMESTAMP columns.  While MariaDB
        supports both CHANGE and ALTER COLUMN in this case, MySQL databases only
        support CHANGE.  So the new logic is that if the server default change is
        against a DateTime-oriented column, the CHANGE format is used
        unconditionally, as in the vast majority of cases the server default is to
        be CURRENT_TIMESTAMP which may also be potentially bundled with an "ON
        UPDATE CURRENT_TIMESTAMP" directive, which SQLAlchemy does not currently
        support as a distinct field.  The fix additionally improves the server
        default comparison logic when the "ON UPDATE" clause is present and
        there are parenthesis to be adjusted for as is the case on some MariaDB
        versions.



    .. change::
        :tags: bug, environment

        Warnings emitted by Alembic now include a default stack level of 2, and in
        some cases it's set to 3, in order to help warnings indicate more closely
        where they are originating from.  Pull request courtesy Ash Berlin-Taylor.


    .. change::
        :tags: bug, py3k
        :tickets: 563

        Replaced the Python compatibility routines for ``getargspec()`` with a fully
        vendored version based on ``getfullargspec()`` from Python 3.3.
        Originally, Python was emitting deprecation warnings for this function in
        Python 3.8 alphas.  While this change was reverted, it was observed that
        Python 3 implementations for ``getfullargspec()`` are an order of magnitude
        slower as of the 3.4 series where it was rewritten against ``Signature``.
        While Python plans to improve upon this situation, SQLAlchemy projects for
        now are using a simple replacement to avoid any future issues.


.. changelog::
    :version: 1.0.10
    :released: April 28, 2019

    .. change::
       :tags: bug, commands
       :tickets: 552

       Fixed bug introduced in release 0.9.0 where the helptext for commands
       inadvertently got expanded to include function docstrings from the
       command.py module.  The logic has been adjusted to only refer to the first
       line(s) preceding the first line break within each docstring, as was the
       original intent.

    .. change::
        :tags: bug, operations, mysql
        :tickets: 551

        Added an assertion in :meth:`.RevisionMap.get_revisions` and other methods
        which ensures revision numbers are passed as strings or collections of
        strings.   Driver issues particularly on MySQL may inadvertently be passing
        bytes here which leads to failures later on.

    .. change::
        :tags: bug, autogenerate, mysql
        :tickets: 553

        Fixed bug when using the
        :paramref:`.EnvironmentContext.configure.compare_server_default` flag set
        to ``True`` where a server default that is introduced in the table metadata
        on an ``Integer`` column, where there is no existing server default in the
        database, would raise a ``TypeError``.

.. changelog::
    :version: 1.0.9
    :released: April 15, 2019

    .. change::
       :tags: bug, operations
       :tickets: 548

       Simplified the internal scheme used to generate the ``alembic.op`` namespace
       to no longer attempt to generate full method signatures (e.g. rather than
       generic ``*args, **kw``) as this was not working in most cases anyway, while
       in rare circumstances it would in fact sporadically have access to the real
       argument names and then fail when generating the function due to missing
       symbols in the argument signature.

.. changelog::
    :version: 1.0.8
    :released: March 4, 2019

    .. change::
       :tags: bug, operations
       :tickets: 528

       Removed use of deprecated ``force`` parameter for SQLAlchemy quoting
       functions as this parameter will be removed in a future release.
       Pull request courtesy Parth Shandilya(ParthS007).

    .. change::
       :tags: bug, autogenerate, postgresql, py3k
       :tickets: 541

       Fixed issue where server default comparison on the PostgreSQL dialect would
       fail for a blank string on Python 3.7 only, due to a change in regular
       expression behavior in Python 3.7.


.. changelog::
    :version: 1.0.7
    :released: January 25, 2019

    .. change::
       :tags: bug, autogenerate
       :tickets: 529

       Fixed issue in new comment support where autogenerated Python code
       for comments wasn't using ``repr()`` thus causing issues with
       quoting.  Pull request courtesy Damien Garaud.

.. changelog::
    :version: 1.0.6
    :released: January 13, 2019

    .. change::
        :tags: feature, operations
        :tickets: 422

        Added Table and Column level comments for supported backends.
        New methods :meth:`.Operations.create_table_comment` and
        :meth:`.Operations.drop_table_comment` are added.  A new arguments
        :paramref:`.Operations.alter_column.comment` and
        :paramref:`.Operations.alter_column.existing_comment` are added to
        :meth:`.Operations.alter_column`.   Autogenerate support is also added
        to ensure comment add/drops from tables and columns are generated as well
        as that :meth:`.Operations.create_table`, :meth:`.Operations.add_column`
        both include the comment field from the source :class:`.Table`
        or :class:`.Column` object.

.. changelog::
    :version: 1.0.5
    :released: November 27, 2018

    .. change::
        :tags: bug, py3k
        :tickets: 507

        Resolved remaining Python 3 deprecation warnings, covering
        the use of inspect.formatargspec() with a vendored version
        copied from the Python standard library, importing
        collections.abc above Python 3.3 when testing against abstract
        base classes, fixed one occurrence of log.warn(), as well as a few
        invalid escape sequences.

.. changelog::
    :version: 1.0.4
    :released: November 27, 2018

    .. change::
       :tags: change

       Code hosting has been moved to GitHub, at
       https://github.com/sqlalchemy/alembic.  Additionally, the
       main Alembic website documentation URL is now
       https://alembic.sqlalchemy.org.

.. changelog::
    :version: 1.0.3
    :released: November 14, 2018

    .. change::
        :tags: bug, mssql
        :tickets: 516

       Fixed regression caused by :ticket:`513`, where the logic to consume
       ``mssql_include`` was not correctly interpreting the case where the flag
       was not present, breaking the ``op.create_index`` directive for SQL Server
       as a whole.

.. changelog::
    :version: 1.0.2
    :released: October 31, 2018

    .. change::
       :tags: bug, autogenerate
       :tickets: 515

       The ``system=True`` flag on :class:`.Column`, used primarily in conjunction
       with the Postgresql "xmin" column, now renders within the autogenerate
       render process, allowing the column to be excluded from DDL.  Additionally,
       adding a system=True column to a model will produce no autogenerate diff as
       this column is implicitly present in the database.

    .. change::
       :tags: bug, mssql
       :tickets: 513

       Fixed issue where usage of the SQL Server ``mssql_include`` option within a
       :meth:`.Operations.create_index` would raise a KeyError, as the additional
       column(s) need to be added to the table object used by the construct
       internally.

.. changelog::
    :version: 1.0.1
    :released: October 17, 2018

    .. change::
        :tags: bug, commands
        :tickets: 497

        Fixed an issue where revision descriptions were essentially
        being formatted twice. Any revision description that contained
        characters like %, writing output to stdout will fail because
        the call to config.print_stdout attempted to format any
        additional args passed to the function.
        This fix now only applies string formatting if any args are provided
        along with the output text.

    .. change::
       :tags: bug, autogenerate
       :tickets: 512

       Fixed issue where removed method ``union_update()`` was used when a
       customized :class:`.MigrationScript` instance included entries in the
       ``.imports`` data member, raising an AttributeError.


.. changelog::
    :version: 1.0.0
    :released: July 13, 2018
    :released: July 13, 2018
    :released: July 13, 2018

    .. change::
        :tags: feature, general
        :tickets: 491

        For Alembic 1.0, Python 2.6 / 3.3 support is being dropped, allowing a
        fixed setup.py to be built as well as universal wheels.  Pull request
        courtesy Hugo.




    .. change::
        :tags: feature, general

        With the 1.0 release, Alembic's minimum SQLAlchemy support version
        moves to 0.9.0, previously 0.7.9.

    .. change::
        :tags: bug, batch
        :tickets: 502

        Fixed issue in batch where dropping a primary key column, then adding it
        back under the same name but without the primary_key flag, would not remove
        it from the existing PrimaryKeyConstraint.  If a new PrimaryKeyConstraint
        is added, it is used as-is, as was the case before.

.. changelog::
    :version: 0.9.10
    :released: June 29, 2018

    .. change::
        :tags: bug, autogenerate

        The "op.drop_constraint()" directive will now render using ``repr()`` for
        the schema name, in the same way that "schema" renders for all the other op
        directives.  Pull request courtesy Denis Kataev.

    .. change::
        :tags: bug, autogenerate
        :tickets: 494

        Added basic capabilities for external dialects to support rendering of
        "nested" types, like arrays, in a manner similar to that of the Postgresql
        dialect.

    .. change::
        :tags: bug, autogenerate

        Fixed issue where "autoincrement=True" would not render for a column that
        specified it, since as of SQLAlchemy 1.1 this is no longer the default
        value for "autoincrement".  Note the behavior only takes effect against the
        SQLAlchemy 1.1.0 and higher; for pre-1.1 SQLAlchemy, "autoincrement=True"
        does not render as was the case before. Pull request courtesy  Elad Almos.

.. changelog::
    :version: 0.9.9
    :released: March 22, 2018

    .. change::
        :tags: feature, commands
        :tickets: 481

        Added new flag ``--indicate-current`` to the ``alembic history`` command.
        When listing versions, it will include the token "(current)" to indicate
        the given version is a current head in the target database.  Pull request
        courtesy Kazutaka Mise.

    .. change::
        :tags: bug, autogenerate, mysql
        :tickets: 455

        The fix for :ticket:`455` in version 0.9.6 involving MySQL server default
        comparison was entirely non functional, as the test itself was also broken
        and didn't reveal that it wasn't working. The regular expression to compare
        server default values like CURRENT_TIMESTAMP to current_timestamp() is
        repaired.

    .. change::
        :tags: bug, mysql, autogenerate
        :tickets: 483

        Fixed bug where MySQL server default comparisons were basically not working
        at all due to incorrect regexp added in :ticket:`455`.  Also accommodates
        for MariaDB 10.2 quoting differences in reporting integer based server
        defaults.




    .. change::
        :tags: bug, operations, mysql
        :tickets: 487

        Fixed bug in ``op.drop_constraint()`` for MySQL where
        quoting rules would not be applied to the constraint name.

.. changelog::
    :version: 0.9.8
    :released: February 16, 2018

    .. change::
        :tags: bug, runtime
        :tickets: 482

        Fixed bug where the :meth:`.Script.as_revision_number` method
        did not accommodate for the 'heads' identifier, which in turn
        caused the :meth:`.EnvironmentContext.get_head_revisions`
        and :meth:`.EnvironmentContext.get_revision_argument` methods
        to be not usable when multiple heads were present.
        The :meth:.`EnvironmentContext.get_head_revisions` method returns
        a tuple in all cases as documented.



    .. change::
        :tags: bug, postgresql, autogenerate
        :tickets: 478

        Fixed bug where autogenerate of :class:`.ExcludeConstraint`
        would render a raw quoted name for a Column that has case-sensitive
        characters, which when invoked as an inline member of the Table
        would produce a stack trace that the quoted name is not found.
        An incoming Column object is now rendered as ``sa.column('name')``.

    .. change::
        :tags: bug, autogenerate
        :tickets: 468

        Fixed bug where the indexes would not be included in a
        migration that was dropping the owning table.   The fix
        now will also emit DROP INDEX for the indexes ahead of time,
        but more importantly will include CREATE INDEX in the
        downgrade migration.

    .. change::
        :tags: bug, postgresql
        :tickets: 480

        Fixed the autogenerate of the module prefix
        when rendering the text_type parameter of
        postgresql.HSTORE, in much the same way that
        we do for ARRAY's type and JSON's text_type.

    .. change::
        :tags: bug, mysql
        :tickets: 479

        Added support for DROP CONSTRAINT to the MySQL Alembic
        dialect to support MariaDB 10.2 which now has real
        CHECK constraints.  Note this change does **not**
        add autogenerate support, only support for op.drop_constraint()
        to work.

.. changelog::
    :version: 0.9.7
    :released: January 16, 2018

    .. change::
        :tags: bug, autogenerate
        :tickets: 472

        Fixed regression caused by :ticket:`421` which would
        cause case-sensitive quoting rules to interfere with the
        comparison logic for index names, thus causing indexes to show
        as added for indexes that have case-sensitive names.   Works with
        SQLAlchemy 0.9 and later series.


    .. change::
        :tags: bug, postgresql, autogenerate
        :tickets: 461

        Fixed bug where autogenerate would produce a DROP statement for the index
        implicitly created by a Postgresql EXCLUDE constraint, rather than skipping
        it as is the case for indexes implicitly generated by unique constraints.
        Makes use of SQLAlchemy 1.0.x's improved "duplicates index" metadata and
        requires at least SQLAlchemy version 1.0.x to function correctly.



.. changelog::
    :version: 0.9.6
    :released: October 13, 2017

    .. change::
        :tags: bug, commands
        :tickets: 458

        Fixed a few Python3.6 deprecation warnings by replacing ``StopIteration``
        with ``return``, as well as using ``getfullargspec()`` instead of
        ``getargspec()`` under Python 3.

    .. change::
        :tags: bug, commands
        :tickets: 441

        An addition to :ticket:`441` fixed in 0.9.5, we forgot to also filter
        for the ``+`` sign in migration names which also breaks due to the relative
        migrations feature.

    .. change::
        :tags: bug, autogenerate
        :tickets: 442

        Fixed bug expanding upon the fix for
        :ticket:`85` which adds the correct module import to the
        "inner" type for an ``ARRAY`` type, the fix now accommodates for the
        generic ``sqlalchemy.types.ARRAY`` type added in SQLAlchemy 1.1,
        rendering the inner type correctly regardless of whether or not the
        Postgresql dialect is present.

    .. change::
        :tags: bug, mysql
        :tickets: 455

        Fixed bug where server default comparison of CURRENT_TIMESTAMP would fail
        on MariaDB 10.2 due to a change in how the function is
        represented by the database during reflection.

    .. change::
        :tags: bug, autogenerate

        Fixed bug where comparison of ``Numeric`` types would produce
        a difference if the Python-side ``Numeric`` inadvertently specified
        a non-None "scale" with a "precision" of None, even though this ``Numeric``
        type will pass over the "scale" argument when rendering. Pull request
        courtesy Ivan Mmelnychuk.

    .. change::
        :tags: feature, commands
        :tickets: 447

        The ``alembic history`` command will now make use of the revision
        environment ``env.py`` unconditionally if the ``revision_environment``
        configuration flag is set to True.  Previously, the environment would
        only be invoked if the history specification were against a database-stored
        revision token.

    .. change::
        :tags: bug, batch
        :tickets: 457

        The name of the temporary table in batch mode is now generated
        off of the original table name itself, to avoid conflicts for the
        unusual case of multiple batch operations running against the same
        database schema at the same time.

    .. change::
        :tags: bug, autogenerate
        :tickets: 456

        A :class:`.ForeignKeyConstraint` can now render correctly if the
        ``link_to_name`` flag is set, as it will not attempt to resolve the name
        from a "key" in this case.  Additionally, the constraint will render
        as-is even if the remote column name isn't present on the referenced
        remote table.

    .. change::
        :tags: bug, runtime, py3k
        :tickets: 449

        Reworked "sourceless" system to be fully capable of handling any
        combination of: Python2/3x, pep3149 or not, PYTHONOPTIMIZE or not,
        for locating and loading both env.py files as well as versioning files.
        This includes: locating files inside of ``__pycache__`` as well as listing
        out version files that might be only in ``versions/__pycache__``, deduplicating
        version files that may be in ``versions/__pycache__`` and ``versions/``
        at the same time, correctly looking for .pyc or .pyo files based on
        if pep488 is present or not. The latest Python3x deprecation warnings
        involving importlib are also corrected.

.. changelog::
    :version: 0.9.5
    :released: August 9, 2017

    .. change::
        :tags: bug, commands
        :tickets: 441

        A :class:`.CommandError` is raised if the "--rev-id" passed to the
        :func:`.revision` command contains dashes or at-signs, as this interferes
        with the command notation used to locate revisions.

    .. change::
        :tags: bug, postgresql
        :tickets: 424

        Added support for the dialect-specific keyword arguments
        to :meth:`.Operations.drop_index`.   This includes support for
        ``postgresql_concurrently`` and others.

    .. change::
        :tags: bug, commands

        Fixed bug in timezone feature introduced in
        :ticket:`425` when the creation
        date in a revision file is calculated, to
        accommodate for timezone names that contain
        mixed-case characters in their name as opposed
        to all uppercase.  Pull request courtesy Nils
        Philippsen.

.. changelog::
    :version: 0.9.4
    :released: July 31, 2017

    .. change::
      :tags: bug, runtime

      Added an additional attribute to the new
      :paramref:`.EnvironmentContext.configure.on_version_apply` API,
      :attr:`.MigrationInfo.up_revision_ids`, to accommodate for the uncommon
      case of the ``alembic stamp`` command being used to move from multiple
      branches down to a common branchpoint; there will be multiple
      "up" revisions in this one case.

.. changelog::
    :version: 0.9.3
    :released: July 6, 2017

    .. change::
      :tags: feature, runtime

      Added a new callback hook
      :paramref:`.EnvironmentContext.configure.on_version_apply`,
      which allows user-defined code to be invoked each time an individual
      upgrade, downgrade, or stamp operation proceeds against a database.
      Pull request courtesy John Passaro.

    .. change:: 433
      :tags: bug, autogenerate
      :tickets: 433

      Fixed bug where autogen comparison of a :class:`.Variant` datatype
      would not compare to the dialect level type for the "default"
      implementation of the :class:`.Variant`, returning the type as changed
      between database and table metadata.

    .. change:: 431
      :tags: bug, tests
      :tickets: 431

      Fixed unit tests to run correctly under the SQLAlchemy 1.0.x series
      prior to version 1.0.10 where a particular bug involving Postgresql
      exclude constraints was fixed.

.. changelog::
    :version: 0.9.2
    :released: May 18, 2017

    .. change:: 429
      :tags: bug, mssql
      :tickets: 429

      Repaired :meth:`.Operations.rename_table` for SQL Server when the
      target table is in a remote schema, the schema name is omitted from
      the "new name" argument.

    .. change:: 425
      :tags: feature, commands
      :tickets: 425

      Added a new configuration option ``timezone``, a string timezone name
      that will be applied to the create date timestamp rendered
      inside the revision file as made available to the ``file_template`` used
      to generate the revision filename.  Note this change adds the
      ``python-dateutil`` package as a dependency.

    .. change:: 421
      :tags: bug, autogenerate
      :tickets: 421

      The autogenerate compare scheme now takes into account the name truncation
      rules applied by SQLAlchemy's DDL compiler to the names of the
      :class:`.Index` object, when these names are dynamically truncated
      due to a too-long identifier name.   As the identifier truncation is
      deterministic, applying the same rule to the metadata name allows
      correct comparison to the database-derived name.

    .. change:: 419
      :tags: bug environment
      :tickets: 419

      A warning is emitted when an object that's not a
      :class:`~sqlalchemy.engine.Connection` is passed to
      :meth:`.EnvironmentContext.configure`.  For the case of a
      :class:`~sqlalchemy.engine.Engine` passed, the check for "in transaction"
      introduced in version 0.9.0 has been relaxed to work in the case of an
      attribute error, as some users appear to be passing an
      :class:`~sqlalchemy.engine.Engine` and not a
      :class:`~sqlalchemy.engine.Connection`.

.. changelog::
    :version: 0.9.1
    :released: March 1, 2017

    .. change:: 417
      :tags: bug, commands
      :tickets: 417, 369

      An adjustment to the bug fix for :ticket:`369` to accommodate for
      env.py scripts that use an enclosing transaction distinct from the
      one that the context provides, so that the check for "didn't commit
      the transaction" doesn't trigger in this scenario.

.. changelog::
    :version: 0.9.0
    :released: February 28, 2017

    .. change:: 38
      :tags: feature, autogenerate
      :tickets: 38

      The :paramref:`.EnvironmentContext.configure.target_metadata` parameter
      may now be optionally specified as a sequence of :class:`.MetaData`
      objects instead of a single :class:`.MetaData` object.  The
      autogenerate process will process the sequence of :class:`.MetaData`
      objects in order.

    .. change:: 369
      :tags: bug, commands
      :tickets: 369

      A :class:`.CommandError` is now raised when a migration file opens
      a database transaction and does not close/commit/rollback, when
      the backend database or environment options also specify transactional_ddl
      is False.   When transactional_ddl is not in use, Alembic doesn't
      close any transaction so a transaction opened by a migration file
      will cause the following migrations to fail to apply.

    .. change:: 413
      :tags: bug, autogenerate, mysql
      :tickets: 413

      The ``autoincrement=True`` flag is now rendered within the
      :meth:`.Operations.alter_column` operation if the source column indicates
      that this flag should be set to True.  The behavior is sensitive to
      the SQLAlchemy version in place, as the "auto" default option is new
      in SQLAlchemy 1.1.  When the source column indicates autoincrement
      as True or "auto", the flag will render as True if the original column
      contextually indicates that it should have "autoincrement" keywords,
      and when the source column explicitly sets it to False, this is also
      rendered.  The behavior is intended to preserve the AUTO_INCREMENT flag
      on MySQL as the column is fully recreated on this backend.  Note that this
      flag does **not** support alteration of a column's "autoincrement" status,
      as this is not portable across backends.

    .. change:: 411
      :tags: bug, postgresql
      :tickets: 411

      Fixed bug where Postgresql JSON/JSONB types rendered on SQLAlchemy
      1.1 would render the "astext_type" argument which defaults to
      the ``Text()`` type without the module prefix, similarly to the
      issue with ARRAY fixed in :ticket:`85`.

    .. change:: 85
      :tags: bug, postgresql
      :tickets: 85

      Fixed bug where Postgresql ARRAY type would not render the import prefix
      for the inner type; additionally, user-defined renderers take place
      for the inner type as well as the outer type.  Pull request courtesy
      Paul Brackin.

    .. change:: process_revision_directives_command
      :tags: feature, autogenerate

      Added a keyword argument ``process_revision_directives`` to the
      :func:`.command.revision` API call.  This function acts in the
      same role as the environment-level
      :paramref:`.EnvironmentContext.configure.process_revision_directives`,
      and allows API use of the
      command to drop in an ad-hoc directive process function.  This
      function can be used among other things to place a complete
      :class:`.MigrationScript` structure in place.

    .. change:: 412
      :tags: feature, postgresql
      :tickets: 412

      Added support for Postgresql EXCLUDE constraints, including the
      operation directive :meth:`.Operations.create_exclude_constraints`
      as well as autogenerate render support for the ``ExcludeConstraint``
      object as present in a ``Table``.  Autogenerate detection for an EXCLUDE
      constraint added or removed to/from an existing table is **not**
      implemented as the SQLAlchemy Postgresql dialect does not yet support
      reflection of EXCLUDE constraints.

      Additionally, unknown constraint types now warn when
      encountered within an autogenerate action rather than raise.

    .. change:: fk_schema_compare
      :tags: bug, operations

      Fixed bug in :func:`.ops.create_foreign_key` where the internal table
      representation would not be created properly if the foreign key referred
      to a table in a different schema of the same name.  Pull request
      courtesy Konstantin Lebedev.

.. changelog::
    :version: 0.8.10
    :released: January 17, 2017

    .. change:: 406
      :tags: bug, versioning
      :tickets: 406

      The alembic_version table, when initially created, now establishes a
      primary key constraint on the "version_num" column, to suit database
      engines that don't support tables without primary keys.   This behavior
      can be controlled using the parameter
      :paramref:`.EnvironmentContext.configure.version_table_pk`.  Note that
      this change only applies to the initial creation of the alembic_version
      table; it does not impact any existing alembic_version table already
      present.

    .. change:: 402
      :tags: bug, batch
      :tickets: 402

      Fixed bug where doing ``batch_op.drop_constraint()`` against the
      primary key constraint would fail to remove the "primary_key" flag
      from the column, resulting in the constraint being recreated.

    .. change:: update_uq_dedupe
      :tags: bug, autogenerate, oracle

      Adjusted the logic originally added for :ticket:`276` that detects MySQL
      unique constraints which are actually unique indexes to be generalized
      for any dialect that has this behavior, for SQLAlchemy version 1.0 and
      greater.  This is to allow for upcoming SQLAlchemy support for unique
      constraint reflection for Oracle, which also has no dedicated concept of
      "unique constraint" and instead establishes a unique index.

    .. change:: 356
      :tags: bug, versioning
      :tickets: 356

      Added a file ignore for Python files of the form ``.#<name>.py``,
      which are generated by the Emacs editor.  Pull request courtesy
      Markus Mattes.

.. changelog::
    :version: 0.8.9
    :released: November 28, 2016

    .. change::  393
      :tags: bug, autogenerate
      :tickets: 393

      Adjustment to the "please adjust!" comment in the script.py.mako
      template so that the generated comment starts with a single pound
      sign, appeasing flake8.

    .. change::
      :tags: bug, batch
      :tickets: 391

      Batch mode will not use CAST() to copy data if ``type_`` is given, however
      the basic type affinity matches that of the existing type.  This to
      avoid SQLite's CAST of TIMESTAMP which results in truncation of the
      data, in those cases where the user needs to add redundant ``type_`` for
      other reasons.

    .. change::
      :tags: bug, autogenerate
      :tickets: 393

      Continued pep8 improvements by adding appropriate whitespace in
      the base template for generated migrations.  Pull request courtesy
      Markus Mattes.

    .. change::
      :tags: bug, revisioning

      Added an additional check when reading in revision files to detect
      if the same file is being read twice; this can occur if the same directory
      or a symlink equivalent is present more than once in version_locations.
      A warning is now emitted and the file is skipped.  Pull request courtesy
      Jiri Kuncar.

    .. change::
      :tags: bug, autogenerate
      :tickets: 395

      Fixed bug where usage of a custom TypeDecorator which returns a
      per-dialect type via :meth:`.TypeDecorator.load_dialect_impl` that differs
      significantly from the default "impl" for the type decorator would fail
      to compare correctly during autogenerate.

    .. change::
      :tags: bug, autogenerate, postgresql
      :tickets: 392

      Fixed bug in Postgresql "functional index skip" behavior where a
      functional index that ended in ASC/DESC wouldn't be detected as something
      we can't compare in autogenerate, leading to duplicate definitions
      in autogenerated files.

    .. change::
      :tags: bug, versioning

      Fixed bug where the "base" specifier, as in "base:head", could not
      be used explicitly when ``--sql`` mode was present.

.. changelog::
    :version: 0.8.8
    :released: September 12, 2016

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

    .. change::
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
      to actually run the default.  This accommodates for default-generation
      functions that generate a new value each time such as a uuid function.

    .. change::
      :tags: bug, batch
      :tickets: 361

      Fixed bug introduced by the fix for :ticket:`338` in version 0.8.4
      where a server default could no longer be dropped in batch mode.
      Pull request courtesy Martin Domke.

    .. change::
      :tags: bug, batch, mssql

      Fixed bug where SQL Server arguments for drop_column() would not
      be propagated when running under a batch block.  Pull request
      courtesy Michal Petrucha.

.. changelog::
    :version: 0.8.5
    :released: March 9, 2016

    .. change::
      :tags: bug, autogenerate
      :tickets: 335

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

      A major improvement to the hash id generation function, which for some
      reason used an awkward arithmetic formula against uuid4() that produced
      values that tended to start with the digits 1-4.  Replaced with a
      simple substring approach which provides an even distribution.  Pull
      request courtesy Antti Haapala.

    .. change::
      :tags: feature, autogenerate

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
      implicit one PostgreSQL generates.   Future integration with
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

      A file named ``__init__.py`` in the ``versions/`` directory is now
      ignored by Alembic when the collection of version files is retrieved.
      Pull request courtesy Michael Floering.

    .. change::
      :tags: bug

      Fixed Py3K bug where an attempt would be made to sort None against
      string values when autogenerate would detect tables across multiple
      schemas, including the default schema.  Pull request courtesy
      paradoxxxzero.

    .. change::
      :tags: bug

      Autogenerate render will render the arguments within a Table construct
      using ``*[...]`` when the number of columns/elements is greater than
      255.  Pull request courtesy Ryan P. Kelly.

    .. change::
      :tags: bug

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
      :paramref:`.Operations.drop_column.mssql_drop_check` or
      :paramref:`.Operations.drop_column.mssql_drop_default`
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

      Fixes to Py3k in-place compatibility regarding output encoding and related;
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
      operation, will generate an ADD CONSTRAINT
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
      to be added to a table made use of the ".key" parameter.

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
      "NoneType" error from occurring when
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

      Improved error message when specifying
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
      to the bugtracker.

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
