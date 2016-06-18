============
Front Matter
============

Information about the Alembic project.

Project Homepage
================

Alembic is hosted on `Bitbucket <http://bitbucket.org>`_ - the lead project
page is at https://bitbucket.org/zzzeek/alembic. Source code is tracked here
using `Git <http://git-scm.com/>`_.

.. versionchanged:: 0.6
	The source repository was moved from Mercurial to Git.

Releases and project status are available on Pypi at
http://pypi.python.org/pypi/alembic.

The most recent published version of this documentation should be at
http://alembic.zzzcomputing.com/.

Project Status
==============

Alembic is currently in beta status and is expected to be fairly
stable.   Users should take care to report bugs and missing features
(see :ref:`bugs`) on an as-needed
basis.  It should be expected that the development version may be required
for proper implementation of recently repaired issues in between releases;
the latest master is always available at https://bitbucket.org/zzzeek/alembic/get/master.tar.gz.

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

Alembic's install process will ensure that SQLAlchemy_
is installed, in addition to other dependencies.  Alembic will work with
SQLAlchemy as of version **0.7.3**, however more features are available with
newer versions such as the 0.9 or 1.0 series.

Alembic supports Python versions 2.6 and above.

Community
=========

Alembic is developed by `Mike Bayer <http://techspot.zzzeek.org>`_, and is
loosely associated with the SQLAlchemy_, `Pylons <http://www.pylonsproject.org>`_,
and `Openstack <http://www.openstack.org>`_ projects.

User issues, discussion of potential bugs and features should be posted
to the Alembic Google Group at `sqlalchemy-alembic <https://groups.google.com/group/sqlalchemy-alembic>`_.

.. _bugs:

Bugs
====
Bugs and feature enhancements to Alembic should be reported on the `Bitbucket
issue tracker <https://bitbucket.org/zzzeek/alembic/issues?status=new&status=open>`_.


.. _SQLAlchemy: http://www.sqlalchemy.org
