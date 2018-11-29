============
Front Matter
============

Information about the Alembic project.

Project Homepage
================

Alembic is hosted on GitHub at https://github.com/sqlalchemy/alembic under the SQLAlchemy organization.

Releases and project status are available on Pypi at https://pypi.python.org/pypi/alembic.

The most recent published version of this documentation should be at https://alembic.sqlalchemy.org.


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
SQLAlchemy as of version **0.9.0**, however more features are available with
newer versions such as the 1.1 or 1.2 series.

.. versionchanged:: 1.0.0 Support for SQLAlchemy 0.8 and 0.7.9 was dropped.

Alembic supports Python versions 2.7, 3.4 and above.

.. versionchanged::  1.0.0  Support for Python 2.6 and 3.3 was dropped.

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

Bugs and feature enhancements to Alembic should be reported on the `GitHub
issue tracker
<https://github.com/sqlalchemy/alembic/issues/>`_.

.. _SQLAlchemy: https://www.sqlalchemy.org
