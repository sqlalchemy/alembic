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
http://alembic.readthedocs.org/.

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

* The ``alembic.op`` module is now generated from a class called
  :class:`.Operations`, including standalone functions that each proxy
  to the current instance of :class:`.Operations`.   The behavior here
  is tailored such that an existing migration script that imports
  symbols directly from ``alembic.op``, that is, 
  ``from alembic.op import create_table``, should still work fine; though ideally
  it's better to use the style ``from alembic import op``, then call
  migration methods directly from the ``op`` member.  The functions inside
  of ``alembic.op`` are at the moment minimally tailored proxies; a future
  release should refine these to more closely resemble the :class:`.Operations`
  methods they represent.
* The ``alembic.context`` module no longer exists, instead ``alembic.context``
  is an object inside the ``alembic`` module which proxies to an underlying
  instance of :class:`.EnvironmentContext`.  :class:`.EnvironmentContext`
  represents the current environment in an encapsulated way.   Most ``env.py``
  scripts that don't import from the ``alembic.context`` name directly,
  instead importing ``context`` itself, should be fine here.   A script that attempts to
  import from it, such as ``from alembic.context import configure``, will
  need to be changed to read ``from alembic import context; context.configure()``.
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
