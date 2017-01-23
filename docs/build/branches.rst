.. _branches:

Working with Branches
=====================

.. note:: Alembic 0.7.0 features an all-new versioning model that fully
   supports branch points, merge points, and long-lived, labeled branches,
   including independent branches originating from multiple bases.
   A great emphasis has been placed on there being almost no impact on the
   existing Alembic workflow, including that all commands work pretty much
   the same as they did before, the format of migration files doesn't require
   any change (though there are some changes that are recommended),
   and even the structure of the ``alembic_version``
   table does not change at all.  However, most alembic commands now offer
   new features which will break out an Alembic environment into
   "branch mode", where things become a lot more intricate.   Working in
   "branch mode" should be considered as a "beta" feature, with many new
   paradigms and use cases still to be stress tested in the wild.
   Please tread lightly!

.. versionadded:: 0.7.0

A **branch** describes a point in a migration stream when two or more
versions refer to the same parent migration as their anscestor.  Branches
occur naturally when two divergent source trees, both containing Alembic
revision files created independently within those source trees, are merged
together into one.  When this occurs, the challenge of a branch is to **merge** the
branches into a single series of changes, so that databases established
from either source tree individually can be upgraded to reference the merged
result equally.  Another scenario where branches are present are when we create them
directly; either at some point in the migration stream we'd like different
series of migrations to be managed independently (e.g. we create a tree),
or we'd like separate migration streams for different features starting
at the root (e.g. a *forest*).  We'll illustrate all of these cases, starting
with the most common which is a source-merge-originated branch that we'll
merge.

Starting with the "account table" example we began in :ref:`create_migration`,
assume we have our basemost version ``1975ea83b712``, which leads into
the second revision ``ae1027a6acf``, and the migration files for these
two revisions are checked into our source repository.
Consider if we merged into our source repository another code branch which contained
a revision for another table called ``shopping_cart``.  This revision was made
against our first Alembic revision, the one that generated ``account``.   After
loading the second source tree in, a new file
``27c6a30d7c24_add_shopping_cart_table.py`` exists within our ``versions`` directory.
Both it, as well as ``ae1027a6acf_add_a_column.py``, reference
``1975ea83b712_add_account_table.py`` as the "downgrade" revision.  To illustrate::

    # main source tree:
    1975ea83b712 (create account table) -> ae1027a6acf (add a column)

    # branched source tree
    1975ea83b712 (create account table) -> 27c6a30d7c24 (add shopping cart table)

Above, we can see ``1975ea83b712`` is our **branch point**; two distinct versions
both refer to it as its parent.  The Alembic command ``branches`` illustrates
this fact::

  $ alembic branches --verbose
  Rev: 1975ea83b712 (branchpoint)
  Parent: <base>
  Branches into: 27c6a30d7c24, ae1027a6acf
  Path: foo/versions/1975ea83b712_add_account_table.py

      create account table

      Revision ID: 1975ea83b712
      Revises:
      Create Date: 2014-11-20 13:02:46.257104

               -> 27c6a30d7c24 (head), add shopping cart table
               -> ae1027a6acf (head), add a column

History shows it too, illustrating two ``head`` entries as well
as a ``branchpoint``::

    $ alembic history
    1975ea83b712 -> 27c6a30d7c24 (head), add shopping cart table
    1975ea83b712 -> ae1027a6acf (head), add a column
    <base> -> 1975ea83b712 (branchpoint), create account table

We can get a view of just the current heads using ``alembic heads``::

    $ alembic heads --verbose
    Rev: 27c6a30d7c24 (head)
    Parent: 1975ea83b712
    Path: foo/versions/27c6a30d7c24_add_shopping_cart_table.py

        add shopping cart table

        Revision ID: 27c6a30d7c24
        Revises: 1975ea83b712
        Create Date: 2014-11-20 13:03:11.436407

    Rev: ae1027a6acf (head)
    Parent: 1975ea83b712
    Path: foo/versions/ae1027a6acf_add_a_column.py

        add a column

        Revision ID: ae1027a6acf
        Revises: 1975ea83b712
        Create Date: 2014-11-20 13:02:54.849677

If we try to run an ``upgrade`` to the usual end target of ``head``, Alembic no
longer considers this to be an unambiguous command.  As we have more than
one ``head``, the ``upgrade`` command wants us to provide more information::

    $ alembic upgrade head
      FAILED: Multiple head revisions are present for given argument 'head'; please specify a specific
      target revision, '<branchname>@head' to narrow to a specific head, or 'heads' for all heads

The ``upgrade`` command gives us quite a few options in which we can proceed
with our upgrade, either giving it information on *which* head we'd like to upgrade
towards, or alternatively stating that we'd like *all* heads to be upgraded
towards at once.  However, in the typical case of two source trees being
merged, we will want to pursue a third option, which is that we can **merge** these
branches.

Merging Branches
----------------

An Alembic merge is a migration file that joins two or
more "head" files together. If the two branches we have right now can
be said to be a "tree" structure, introducing this merge file will
turn it into a "diamond" structure::

                                -- ae1027a6acf -->
                               /                   \
    <base> --> 1975ea83b712 -->                      --> mergepoint
                               \                   /
                                -- 27c6a30d7c24 -->

We create the merge file using ``alembic merge``; with this command, we can
pass to it an argument such as ``heads``, meaning we'd like to merge all
heads.  Or, we can pass it individual revision numbers sequentally::

    $ alembic merge -m "merge ae1 and 27c" ae1027 27c6a
      Generating /path/to/foo/versions/53fffde5ad5_merge_ae1_and_27c.py ... done

Looking inside the new file, we see it as a regular migration file, with
the only new twist is that ``down_revision`` points to both revisions::

    """merge ae1 and 27c

    Revision ID: 53fffde5ad5
    Revises: ae1027a6acf, 27c6a30d7c24
    Create Date: 2014-11-20 13:31:50.811663

    """

    # revision identifiers, used by Alembic.
    revision = '53fffde5ad5'
    down_revision = ('ae1027a6acf', '27c6a30d7c24')
    branch_labels = None

    from alembic import op
    import sqlalchemy as sa


    def upgrade():
        pass


    def downgrade():
        pass

This file is a regular migration file, and if we wish to, we may place
:class:`.Operations` directives into the ``upgrade()`` and ``downgrade()``
functions like any other migration file.  Though it is probably best to limit
the instructions placed here only to those that deal with any kind of
reconciliation that is needed between the two merged branches, if any.

The ``heads`` command now illustrates that the multiple heads in our
``versions/`` directory have been resolved into our new head::

    $ alembic heads --verbose
    Rev: 53fffde5ad5 (head) (mergepoint)
    Merges: ae1027a6acf, 27c6a30d7c24
    Path: foo/versions/53fffde5ad5_merge_ae1_and_27c.py

        merge ae1 and 27c

        Revision ID: 53fffde5ad5
        Revises: ae1027a6acf, 27c6a30d7c24
        Create Date: 2014-11-20 13:31:50.811663

History shows a similar result, as the mergepoint becomes our head::

    $ alembic history
    ae1027a6acf, 27c6a30d7c24 -> 53fffde5ad5 (head) (mergepoint), merge ae1 and 27c
    1975ea83b712 -> ae1027a6acf, add a column
    1975ea83b712 -> 27c6a30d7c24, add shopping cart table
    <base> -> 1975ea83b712 (branchpoint), create account table

With a single ``head`` target, a generic ``upgrade`` can proceed::

    $ alembic upgrade head
    INFO  [alembic.migration] Context impl PostgresqlImpl.
    INFO  [alembic.migration] Will assume transactional DDL.
    INFO  [alembic.migration] Running upgrade  -> 1975ea83b712, create account table
    INFO  [alembic.migration] Running upgrade 1975ea83b712 -> 27c6a30d7c24, add shopping cart table
    INFO  [alembic.migration] Running upgrade 1975ea83b712 -> ae1027a6acf, add a column
    INFO  [alembic.migration] Running upgrade ae1027a6acf, 27c6a30d7c24 -> 53fffde5ad5, merge ae1 and 27c


.. topic:: merge mechanics

  The upgrade process traverses through all of our migration files using
  a  **topological sorting** algorithm, treating the list of migration
  files not as a linked list, but as a **directed acyclic graph**.  The starting
  points of this traversal are the **current heads** within our database,
  and the end point is the "head" revision or revisions specified.

  When a migration proceeds across a point at which there are multiple heads,
  the ``alembic_version`` table will at that point store *multiple* rows,
  one for each head.  Our migration process above will emit SQL against
  ``alembic_version`` along these lines:

    .. sourcecode:: sql

      -- Running upgrade  -> 1975ea83b712, create account table
      INSERT INTO alembic_version (version_num) VALUES ('1975ea83b712')

      -- Running upgrade 1975ea83b712 -> 27c6a30d7c24, add shopping cart table
      UPDATE alembic_version SET version_num='27c6a30d7c24' WHERE alembic_version.version_num = '1975ea83b712'

      -- Running upgrade 1975ea83b712 -> ae1027a6acf, add a column
      INSERT INTO alembic_version (version_num) VALUES ('ae1027a6acf')

      -- Running upgrade ae1027a6acf, 27c6a30d7c24 -> 53fffde5ad5, merge ae1 and 27c
      DELETE FROM alembic_version WHERE alembic_version.version_num = 'ae1027a6acf'
      UPDATE alembic_version SET version_num='53fffde5ad5' WHERE alembic_version.version_num = '27c6a30d7c24'

  At the point at which both ``27c6a30d7c24`` and ``ae1027a6acf`` exist within our
  database, both values are present in ``alembic_version``, which now has
  two rows.   If we upgrade to these two versions alone, then stop and
  run ``alembic current``, we will see this::

      $ alembic current --verbose
      Current revision(s) for postgresql://scott:XXXXX@localhost/test:
      Rev: ae1027a6acf
      Parent: 1975ea83b712
      Path: foo/versions/ae1027a6acf_add_a_column.py

          add a column

          Revision ID: ae1027a6acf
          Revises: 1975ea83b712
          Create Date: 2014-11-20 13:02:54.849677

      Rev: 27c6a30d7c24
      Parent: 1975ea83b712
      Path: foo/versions/27c6a30d7c24_add_shopping_cart_table.py

          add shopping cart table

          Revision ID: 27c6a30d7c24
          Revises: 1975ea83b712
          Create Date: 2014-11-20 13:03:11.436407

  A key advantage to the ``merge`` process is that it will
  run equally well on databases that were present on version ``ae1027a6acf``
  alone, versus databases that were present on version ``27c6a30d7c24`` alone;
  whichever version was not yet applied, will be applied before the merge point
  can be crossed.   This brings forth a way of thinking about a merge file,
  as well as about any Alembic revision file.  As they are considered to
  be "nodes" within a set that is subject to topological sorting, each
  "node" is a point that cannot be crossed until all of its dependencies
  are satisfied.

  Prior to Alembic's support of merge points, the use case of databases
  sitting on different heads was basically impossible to reconcile; having
  to manually splice the head files together invariably meant that one migration
  would occur before the other, thus being incompatible with databases that
  were present on the other migration.

Working with Explicit Branches
------------------------------

The ``alembic upgrade`` command hinted at other options besides merging when
dealing with multiple heads.  Let's back up and assume we're back where
we have as our heads just ``ae1027a6acf`` and ``27c6a30d7c24``::

    $ alembic heads
    27c6a30d7c24
    ae1027a6acf

Earlier, when we did ``alembic upgrade head``, it gave us an error which
suggested ``please specify a specific target revision, '<branchname>@head' to
narrow to a specific head, or 'heads' for all heads`` in order to proceed
without merging.   Let's cover those cases.

Referring to all heads at once
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``heads`` identifier is a lot like ``head``, except it explicitly refers
to *all* heads at once.  That is, it's like telling Alembic to do the operation
for both ``ae1027a6acf`` and ``27c6a30d7c24`` simultaneously.  If we started
from a fresh database and ran ``upgrade heads`` we'd see::

    $ alembic upgrade heads
    INFO  [alembic.migration] Context impl PostgresqlImpl.
    INFO  [alembic.migration] Will assume transactional DDL.
    INFO  [alembic.migration] Running upgrade  -> 1975ea83b712, create account table
    INFO  [alembic.migration] Running upgrade 1975ea83b712 -> ae1027a6acf, add a column
    INFO  [alembic.migration] Running upgrade 1975ea83b712 -> 27c6a30d7c24, add shopping cart table

Since we've upgraded to ``heads``, and we do in fact have more than one head,
that means these two distinct heads are now in our ``alembic_version`` table.
We can see this if we run ``alembic current``::

    $ alembic current
    ae1027a6acf (head)
    27c6a30d7c24 (head)

That means there's two rows in ``alembic_version`` right now.  If we downgrade
one step at a time, Alembic will **delete** from the ``alembic_version`` table
each branch that's closed out, until only one branch remains; then it will
continue updating the single value down to the previous versions::

    $ alembic downgrade -1
    INFO  [alembic.migration] Running downgrade ae1027a6acf -> 1975ea83b712, add a column

    $ alembic current
    27c6a30d7c24 (head)

    $ alembic downgrade -1
    INFO  [alembic.migration] Running downgrade 27c6a30d7c24 -> 1975ea83b712, add shopping cart table

    $ alembic current
    1975ea83b712 (branchpoint)

    $ alembic downgrade -1
    INFO  [alembic.migration] Running downgrade 1975ea83b712 -> , create account table

    $ alembic current

Referring to a Specific Version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We can pass a specific version number to ``upgrade``.  Alembic will ensure that
all revisions upon which this version depends are invoked, and nothing more.
So if we ``upgrade`` either to ``27c6a30d7c24`` or ``ae1027a6acf`` specifically,
it guarantees that ``1975ea83b712`` will have been applied, but not that
any "sibling" versions are applied::

    $ alembic upgrade 27c6a
    INFO  [alembic.migration] Running upgrade  -> 1975ea83b712, create account table
    INFO  [alembic.migration] Running upgrade 1975ea83b712 -> 27c6a30d7c24, add shopping cart table

With ``1975ea83b712`` and ``27c6a30d7c24`` applied, ``ae1027a6acf`` is just
a single additional step::

    $ alembic upgrade ae102
    INFO  [alembic.migration] Running upgrade 1975ea83b712 -> ae1027a6acf, add a column

Working with Branch Labels
^^^^^^^^^^^^^^^^^^^^^^^^^^

To satisfy the use case where an environment has long-lived branches, especially
independent branches as will be discussed in the next section, Alembic supports
the concept of **branch labels**.   These are string values that are present
within the migration file, using the new identifier ``branch_labels``.
For example, if we want to refer to the "shopping cart" branch using the name
"shoppingcart", we can add that name to our file
``27c6a30d7c24_add_shopping_cart_table.py``::

    """add shopping cart table

    """

    # revision identifiers, used by Alembic.
    revision = '27c6a30d7c24'
    down_revision = '1975ea83b712'
    branch_labels = ('shoppingcart',)

    # ...

The ``branch_labels`` attribute refers to a string name, or a tuple
of names, which will now apply to this revision, all descendants of this
revision, as well as all ancestors of this revision up until the preceding
branch point, in this case ``1975ea83b712``.  We can see the ``shoppingcart``
label applied to this revision::

    $ alembic history
    1975ea83b712 -> 27c6a30d7c24 (shoppingcart) (head), add shopping cart table
    1975ea83b712 -> ae1027a6acf (head), add a column
    <base> -> 1975ea83b712 (branchpoint), create account table

With the label applied, the name ``shoppingcart`` now serves as an alias
for the ``27c6a30d7c24`` revision specifically.  We can illustrate this
by showing it with ``alembic show``::

    $ alembic show shoppingcart
    Rev: 27c6a30d7c24 (head)
    Parent: 1975ea83b712
    Branch names: shoppingcart
    Path: foo/versions/27c6a30d7c24_add_shopping_cart_table.py

        add shopping cart table

        Revision ID: 27c6a30d7c24
        Revises: 1975ea83b712
        Create Date: 2014-11-20 13:03:11.436407

However, when using branch labels, we usually want to use them using a syntax
known as "branch at" syntax; this syntax allows us to state that we want to
use a specific revision, let's say a "head" revision, in terms of a *specific*
branch.  While normally, we can't refer to ``alembic upgrade head`` when
there's multiple heads, we *can* refer to this head specifcally using
``shoppingcart@head`` syntax::

    $ alembic upgrade shoppingcart@head
    INFO  [alembic.migration] Running upgrade 1975ea83b712 -> 27c6a30d7c24, add shopping cart table

The ``shoppingcart@head`` syntax becomes important to us if we wish to
add new migration files to our versions directory while maintaining multiple
branches.  Just like the ``upgrade`` command, if we attempted to add a new
revision file to our multiple-heads layout without a specific parent revision,
we'd get a familiar error::

    $ alembic revision -m "add a shopping cart column"
      FAILED: Multiple heads are present; please specify the head revision on
      which the new revision should be based, or perform a merge.

The ``alembic revision`` command is pretty clear in what we need to do;
to add our new revision specifically to the ``shoppingcart`` branch,
we use the ``--head`` argument, either with the specific revision identifier
``27c6a30d7c24``, or more generically using our branchname ``shoppingcart@head``::

    $ alembic revision -m "add a shopping cart column"  --head shoppingcart@head
      Generating /path/to/foo/versions/d747a8a8879_add_a_shopping_cart_column.py ... done

``alembic history`` shows both files now part of the ``shoppingcart`` branch::

    $ alembic history
    1975ea83b712 -> ae1027a6acf (head), add a column
    27c6a30d7c24 -> d747a8a8879 (shoppingcart) (head), add a shopping cart column
    1975ea83b712 -> 27c6a30d7c24 (shoppingcart), add shopping cart table
    <base> -> 1975ea83b712 (branchpoint), create account table

We can limit our history operation just to this branch as well::

    $ alembic history -r shoppingcart:
    27c6a30d7c24 -> d747a8a8879 (shoppingcart) (head), add a shopping cart column
    1975ea83b712 -> 27c6a30d7c24 (shoppingcart), add shopping cart table

If we want to illustrate the path of ``shoppingcart`` all the way from the
base, we can do that as follows::

    $ alembic history -r :shoppingcart@head
    27c6a30d7c24 -> d747a8a8879 (shoppingcart) (head), add a shopping cart column
    1975ea83b712 -> 27c6a30d7c24 (shoppingcart), add shopping cart table
    <base> -> 1975ea83b712 (branchpoint), create account table

We can run this operation from the "base" side as well, but we get a different
result::

    $ alembic history -r shoppingcart@base:
    1975ea83b712 -> ae1027a6acf (head), add a column
    27c6a30d7c24 -> d747a8a8879 (shoppingcart) (head), add a shopping cart column
    1975ea83b712 -> 27c6a30d7c24 (shoppingcart), add shopping cart table
    <base> -> 1975ea83b712 (branchpoint), create account table

When we list from ``shoppingcart@base`` without an endpoint, it's really shorthand
for ``-r shoppingcart@base:heads``, e.g. all heads, and since ``shoppingcart@base``
is the same "base" shared by the ``ae1027a6acf`` revision, we get that
revision in our listing as well.  The ``<branchname>@base`` syntax can be
useful when we are dealing with individual bases, as we'll see in the next
section.

The ``<branchname>@head`` format can also be used with revision numbers
instead of branch names, though this is less convenient.  If we wanted to
add a new revision to our branch that includes the un-labeled ``ae1027a6acf``,
if this weren't a head already, we could ask for the "head of the branch
that includes ``ae1027a6acf``" as follows::

    $ alembic revision -m "add another account column" --head ae10@head
      Generating /path/to/foo/versions/55af2cb1c267_add_another_account_column.py ... done

More Label Syntaxes
^^^^^^^^^^^^^^^^^^^

The ``heads`` symbol can be combined with a branch label, in the case that
your labeled branch itself breaks off into multiple branches::

    $ alembic upgrade shoppingcart@heads

Relative identifiers, as introduced in :ref:`relative_migrations`,
work with labels too.  For example, upgrading to ``shoppingcart@+2``
means to upgrade from current heads on "shoppingcart" upwards two revisions::

    $ alembic upgrade shoppingcart@+2

This kind of thing works from history as well::

    $ alembic history -r current:shoppingcart@+2

The newer ``relnum+delta`` format can be combined as well, for example
if we wanted to list along ``shoppingcart`` up until two revisions
before the head::

    $ alembic history -r :shoppingcart@head-2

.. _multiple_bases:

Working with Multiple Bases
---------------------------

.. note::  The multiple base feature is intended to allow for multiple Alembic
   versioning lineages which **share the same alembic_version table**.  This is
   so that individual revisions within the lineages can have cross-dependencies
   on each other.   For the simpler case where one project has multiple,
   **completely independent** revision lineages that refer to **separate**
   alembic_version tables, see the example in :ref:`multiple_environments`.

We've seen in the previous section that ``alembic upgrade`` is fine
if we have multiple heads, ``alembic revision`` allows us to tell it which
"head" we'd like to associate our new revision file with, and branch labels
allow us to assign names to branches that we can use in subsequent commands.
Let's put all these together and refer to a new "base", that is, a whole
new tree of revision files that will be semi-independent of the account/shopping
cart revisions we've been working with.  This new tree will deal with
database tables involving "networking".

.. _multiple_version_directories:

Setting up Multiple Version Directories
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

While optional, it is often the case that when working with multiple bases,
we'd like different sets of version files to exist within their own directories;
typically, if an application is organized into several sub-modules, each
one would have a version directory containing migrations pertinent to
that module.  So to start out, we can edit ``alembic.ini`` to refer
to multiple directories;  we'll also state the current ``versions``
directory as one of them::

  # version location specification; this defaults
  # to foo/versions.  When using multiple version
  # directories, initial revisions must be specified with --version-path
  version_locations = %(here)s/model/networking %(here)s/alembic/versions

The new directory ``%(here)s/model/networking`` is in terms of where
the ``alembic.ini`` file is, as we are using the symbol ``%(here)s`` which
resolves to this location.   When we create our first new revision
targeted at this directory,
``model/networking`` will be created automatically if it does not
exist yet.  Once we've created a revision here, the path is used automatically
when generating subsequent revision files that refer to this revision tree.

Creating a Labeled Base Revision
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We also want our new branch to have its own name, and for that we want to
apply a branch label to the base.  In order to achieve this using the
``alembic revision`` command without editing, we need to ensure our
``script.py.mako`` file, used
for generating new revision files, has the appropriate substitutions present.
If Alembic version 0.7.0 or greater was used to generate the original
migration environment, this is already done.  However when working with an older
environment, ``script.py.mako`` needs to have this directive added, typically
underneath the ``down_revision`` directive::

    # revision identifiers, used by Alembic.
    revision = ${repr(up_revision)}
    down_revision = ${repr(down_revision)}

    # add this here in order to use revision with branch_label
    branch_labels = ${repr(branch_labels)}

With this in place, we can create a new revision file, starting up a branch
that will deal with database tables involving networking; we specify the
``--head`` version of ``base``, a ``--branch-label`` of ``networking``,
and the directory we want this first revision file to be
placed in with ``--version-path``::

    $ alembic revision -m "create networking branch" --head=base --branch-label=networking --version-path=model/networking
      Creating directory /path/to/foo/model/networking ... done
      Generating /path/to/foo/model/networking/3cac04ae8714_create_networking_branch.py ... done

If we ran the above command and we didn't have the newer ``script.py.mako``
directive, we'd get this error::

  FAILED: Version 3cac04ae8714 specified branch_labels networking, however
  the migration file foo/model/networking/3cac04ae8714_create_networking_branch.py
  does not have them; have you upgraded your script.py.mako to include the 'branch_labels'
  section?

When we receive the above error, and we would like to try again, we need to
either **delete** the incorrectly generated file in order to run ``revision``
again, *or* we can edit the ``3cac04ae8714_create_networking_branch.py``
directly to add the ``branch_labels`` in of our choosing.

Running with Multiple Bases
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once we have a new, permanent (for as long as we desire it to be)
base in our system, we'll always have multiple heads present::

    $ alembic heads
    3cac04ae8714 (networking) (head)
    27c6a30d7c24 (shoppingcart) (head)
    ae1027a6acf (head)

When we want to add a new revision file to ``networking``, we specify
``networking@head`` as the ``--head``.  The appropriate version directory
is now selected automatically based on the head we choose::

    $ alembic revision -m "add ip number table" --head=networking@head
      Generating /path/to/foo/model/networking/109ec7d132bf_add_ip_number_table.py ... done

It's important that we refer to the head using ``networking@head``; if we
only refer to ``networking``, that refers to only ``3cac04ae8714`` specifically;
if we specify this and it's not a head, ``alembic revision`` will make sure
we didn't mean to specify the head::

    $ alembic revision -m "add DNS table" --head=networking
      FAILED: Revision 3cac04ae8714 is not a head revision; please
      specify --splice to create a new branch from this revision

As mentioned earlier, as this base is independent, we can view its history
from the base using ``history -r networking@base:``::

    $ alembic history -r networking@base:
    109ec7d132bf -> 29f859a13ea (networking) (head), add DNS table
    3cac04ae8714 -> 109ec7d132bf (networking), add ip number table
    <base> -> 3cac04ae8714 (networking), create networking branch

At the moment, this is the same output we'd get at this point if we used
``-r :networking@head``.  However, that will change later on as we use
additional directives.

We may now run upgrades or downgrades freely, among individual branches
(let's assume a clean database again)::

    $ alembic upgrade networking@head
    INFO  [alembic.migration] Running upgrade  -> 3cac04ae8714, create networking branch
    INFO  [alembic.migration] Running upgrade 3cac04ae8714 -> 109ec7d132bf, add ip number table
    INFO  [alembic.migration] Running upgrade 109ec7d132bf -> 29f859a13ea, add DNS table

or against the whole thing using ``heads``::

    $ alembic upgrade heads
    INFO  [alembic.migration] Running upgrade  -> 1975ea83b712, create account table
    INFO  [alembic.migration] Running upgrade 1975ea83b712 -> 27c6a30d7c24, add shopping cart table
    INFO  [alembic.migration] Running upgrade 27c6a30d7c24 -> d747a8a8879, add a shopping cart column
    INFO  [alembic.migration] Running upgrade 1975ea83b712 -> ae1027a6acf, add a column
    INFO  [alembic.migration] Running upgrade ae1027a6acf -> 55af2cb1c267, add another account column

Branch Dependencies
-------------------

When working with multiple roots, it is expected that these different
revision streams will need to refer to one another.   For example, a new
revision in ``networking`` which needs to refer to the ``account``
table will want to establish ``55af2cb1c267, add another account column``,
the last revision that
works with the account table, as a dependency.   From a graph perspective,
this means nothing more that the new file will feature both
``55af2cb1c267, add another account column`` and ``29f859a13ea, add DNS table`` as "down" revisions,
and looks just as though we had merged these two branches together.  However,
we don't want to consider these as "merged"; we want the two revision
streams to *remain independent*, even though a version in ``networking``
is going to reach over into the other stream.  To support this use case,
Alembic provides a directive known as ``depends_on``, which allows
a revision file to refer to another as a "dependency", very similar to
an entry in ``down_revision`` from a graph perspective, but different
from a semantic perspective.

To use ``depends_on``, we can specify it as part of our ``alembic revision``
command::

    $ alembic revision -m "add ip account table" --head=networking@head  --depends-on=55af2cb1c267
      Generating /path/to/foo/model/networking/2a95102259be_add_ip_account_table.py ... done

Within our migration file, we'll see this new directive present::

    # revision identifiers, used by Alembic.
    revision = '2a95102259be'
    down_revision = '29f859a13ea'
    branch_labels = None
    depends_on='55af2cb1c267'

``depends_on`` may be either a real revision number or a branch
name.  When specified at the command line, a resolution from a
partial revision number will work as well.   It can refer
to any number of dependent revisions as well; for example, if we were
to run the command::

    $ alembic revision -m "add ip account table" \\
        --head=networking@head  \\
        --depends-on=55af2cb1c267 --depends-on=d747a --depends-on=fa445
      Generating /path/to/foo/model/networking/2a95102259be_add_ip_account_table.py ... done

We'd see inside the file::

    # revision identifiers, used by Alembic.
    revision = '2a95102259be'
    down_revision = '29f859a13ea'
    branch_labels = None
    depends_on = ('55af2cb1c267', 'd747a8a8879', 'fa4456a9201')

We also can of course add or alter this value within the file manually after
it is generated, rather than using the ``--depends-on`` argument.

.. versionadded:: 0.8 The ``depends_on`` attribute may be set directly
   from the ``alembic revision`` command, rather than editing the file
   directly.  ``depends_on`` identifiers may also be specified as
   branch names at the command line or directly within the migration file.
   The values may be specified as partial revision numbers from the command
   line which will be resolved to full revision numbers in the output file.

We can see the effect this directive has when we view the history
of the ``networking`` branch in terms of "heads", e.g., all the revisions that
are descendants::

    $ alembic history -r :networking@head
    29f859a13ea (55af2cb1c267) -> 2a95102259be (networking) (head), add ip account table
    109ec7d132bf -> 29f859a13ea (networking), add DNS table
    3cac04ae8714 -> 109ec7d132bf (networking), add ip number table
    <base> -> 3cac04ae8714 (networking), create networking branch
    ae1027a6acf -> 55af2cb1c267 (effective head), add another account column
    1975ea83b712 -> ae1027a6acf, Add a column
    <base> -> 1975ea83b712 (branchpoint), create account table

What we see is that the full history of the ``networking`` branch, in terms
of an "upgrade" to the "head", will include that the tree building
up ``55af2cb1c267, add another account column``
will be pulled in first.   Interstingly, we don't see this displayed
when we display history in the other direction, e.g. from ``networking@base``::

    $ alembic history -r networking@base:
    29f859a13ea (55af2cb1c267) -> 2a95102259be (networking) (head), add ip account table
    109ec7d132bf -> 29f859a13ea (networking), add DNS table
    3cac04ae8714 -> 109ec7d132bf (networking), add ip number table
    <base> -> 3cac04ae8714 (networking), create networking branch

The reason for the discrepancy is that displaying history from the base
shows us what would occur if we ran a downgrade operation, instead of an
upgrade.  If we downgraded all the files in ``networking`` using
``networking@base``, the dependencies aren't affected, they're left in place.

We also see something odd if we view ``heads`` at the moment::

    $ alembic heads
    2a95102259be (networking) (head)
    27c6a30d7c24 (shoppingcart) (head)
    55af2cb1c267 (effective head)

The head file that we used as a "dependency", ``55af2cb1c267``, is displayed
as an "effective" head, which we can see also in the history display earlier.
What this means is that at the moment, if we were to upgrade all versions
to the top, the ``55af2cb1c267`` revision number would not actually be
present in the ``alembic_version`` table; this is because it does not have
a branch of its own subsequent to the ``2a95102259be`` revision which depends
on it::

    $ alembic upgrade heads
    INFO  [alembic.migration] Running upgrade 29f859a13ea, 55af2cb1c267 -> 2a95102259be, add ip account table

    $ alembic current
    2a95102259be (head)
    27c6a30d7c24 (head)

The entry is still displayed in ``alembic heads`` because Alembic knows that
even though this revision isn't a "real" head, it's still something that
we developers consider semantically to be a head, so it's displayed, noting
its special status so that we don't get quite as confused when we don't
see it within ``alembic current``.

If we add a new revision onto ``55af2cb1c267``, the branch again becomes
a "real" branch which can have its own entry in the database::

    $ alembic revision -m "more account changes" --head=55af2cb@head
      Generating /path/to/foo/versions/34e094ad6ef1_more_account_changes.py ... done

    $ alembic upgrade heads
    INFO  [alembic.migration] Running upgrade 55af2cb1c267 -> 34e094ad6ef1, more account changes

    $ alembic current
    2a95102259be (head)
    27c6a30d7c24 (head)
    34e094ad6ef1 (head)


For posterity, the revision tree now looks like::

    $ alembic history
    29f859a13ea (55af2cb1c267) -> 2a95102259be (networking) (head), add ip account table
    109ec7d132bf -> 29f859a13ea (networking), add DNS table
    3cac04ae8714 -> 109ec7d132bf (networking), add ip number table
    <base> -> 3cac04ae8714 (networking), create networking branch
    1975ea83b712 -> 27c6a30d7c24 (shoppingcart) (head), add shopping cart table
    55af2cb1c267 -> 34e094ad6ef1 (head), more account changes
    ae1027a6acf -> 55af2cb1c267, add another account column
    1975ea83b712 -> ae1027a6acf, Add a column
    <base> -> 1975ea83b712 (branchpoint), create account table


                        --- 27c6 --> d747 --> <head>
                       /   (shoppingcart)
    <base> --> 1975 -->
                       \
                         --- ae10 --> 55af --> <head>
                                        ^
                                        +--------+ (dependency)
                                                 |
                                                 |
    <base> --> 3782 -----> 109e ----> 29f8 ---> 2a95 --> <head>
             (networking)


If there's any point to be made here, it's if you are too freely branching, merging
and labeling, things can get pretty crazy!  Hence the branching system should
be used carefully and thoughtfully for best results.

