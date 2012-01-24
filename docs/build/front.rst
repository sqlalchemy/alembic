============
Front Matter
============

Information about the Alembic project.

Project Homepage
================

Alembic is hosted on `Bitbucket <http://bitbucket.org>`_ - the lead project
page is at https://bitbucket.org/zzzeek/alembic. Source code is tracked here
using `Mercurial <http://mercurial.selenic.com/>`_.

Releases and project status are available on Pypi at
http://pypi.python.org/pypi/alembic.

The most recent published version of this documentation should be at
http://readthedocs.org/docs/alembic/.

Project Status
==============

Note that Alembic is still in alpha status.   Users should take
care to report bugs and missing features (see :ref:`bugs`) on an as-needed
basis.  It should be expected that the development version may be required
for proper implementation of recently repaired issues in between releases;
the latest tip is always available at https://bitbucket.org/zzzeek/alembic/get/tip.tar.gz.

.. _installation:

Installation
============

Install released versions of Alembic from the Python package index with `pip <http://pypi.python.org/pypi/pip>`_ or a similar tool::

    pip install alembic

Installation via source distribution is via the ``setup.py`` script::

    python setup.py install

The install will add the ``alembic`` command to the environment.  All operations with Alembic
then proceed through the usage of this command.

Dependencies
------------

Alembic's install process will ensure that `SQLAlchemy <http://www.sqlalchemy.org>`_ 
is installed, in addition to other dependencies.  Alembic will work with 
SQLAlchemy as of version **0.6**, though with a limited featureset.  
The latest version of SQLAlchemy within the **0.7** series is strongly recommended.

Upgrading from Alembic 0.1 to 0.2
=================================

Alembic 0.2 has some reorganizations and features that might impact an existing 0.1
installation.   These include:

* The ``alembic.op`` and ``alembic.context`` names are no longer Python modules,
  and are instead objects placed at those names when migrations run.   This 
  means an env.py script or migration script that tries to import from 
  the object will fail, such as ``from alembic.op import create_table``.
  The imports used should now be of the form ``from alembic import context``
  and ``from alembic import op``.   The various methods associated with the
  context and ops should be invoked from those names now, such as ``op.create_table()``.
  The included files and the tutorial in 0.1 already did things this way,
  though the examples for each ``op`` docstring did not.   Hopefully most users
  stuck with the tutorial convention, where the usage examples will
  still work without change.

* The naming convention for migration files is now customizable, and defaults
  to the scheme "%(rev)s_%(slug)s", where "slug" is based on the message
  added to the script.   When Alembic reads one of these files, it looks
  at a new variable named ``revision`` inside of the script to get at the
  revision identifier.   Scripts that use the new naming convention
  will need to render this ``revision`` identifier inside the script,
  so the ``script.py.mako`` file within an existing alembic environment
  needs to have both ``revision`` and ``down_revision`` specified::

        # revision identifiers, used by Alembic.
        revision = ${repr(up_revision)}
        down_revision = ${repr(down_revision)}

  Existing scripts that use the 0.1 naming convention **don't have to be changed**,
  unless you are renaming them.  Alembic will fall back to pulling in the version 
  identifier from the filename if ``revision`` isn't present, as long as the 
  filename uses the old naming convention.


Community
=========

Alembic is developed by `Mike Bayer <http://techspot.zzzeek.org>`_, and is 
loosely associated with the `SQLAlchemy <http://www.sqlalchemy.org/>`_ and `Pylons <http://www.pylonsproject.org>`_
projects. 

User issues, discussion of potential bugs and features should be posted
to the Alembic Google Group at `sqlalchemy-alembic <https://groups.google.com/group/sqlalchemy-alembic>`_.

.. _bugs:

Bugs
====
Bugs and feature enhancements to Alembic should be reported on the `Bitbucket
issue tracker <https://bitbucket.org/zzzeek/alembic/issues?status=new&status=open>`_.  
