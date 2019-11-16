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

Installation of Alembic is typically local to a project setup and it is usually
assumed that an approach like `virtual environments
<https://docs.python.org/3/tutorial/venv.html>`_ are used, which would include
that the target project also `has a setup.py script
<https://packaging.python.org/tutorials/packaging-projects/>`_.

.. note::

    While the ``alembic`` command line tool runs perfectly fine no matter where
    its installed, the rationale for project-local setup is that the Alembic
    command line tool runs most of its key operations through a Python file
    ``env.py`` that is established as part of a project's setup when the
    ``alembic init`` command is run for that project;  the purpose of
    ``env.py`` is to establish database connectivity and optionally model
    definitions for the migration process, the latter of which in particular
    usually rely upon being able to import the modules of the project itself.


The documentation below is **only one kind of approach to installing Alembic for a
project**; there are many such approaches.   The documentation below is
provided only for those users who otherwise have no specific project setup
chosen.

To build a virtual environment for a specific project, first we assume that
`Python virtualenv <https://pypi.org/project/virtualenv/>`_ is installed
systemwide.  Then::

    $ cd /path/to/your/project
    $ virtualenv .venv

There is now a Python interpreter that you can access in
``/path/to/your/project/.venv/bin/python``, as well as the `pip
<http://pypi.python.org/pypi/pip>`_ installer tool in
``/path/to/your/project/.venv/bin/pip``.

We now install Alembic as follows::

    $ /path/to/your/project/.venv/bin/pip install alembic

The install will add the ``alembic`` command to the virtual environment.  All
operations with Alembic in terms of this specific virtual environment will then
proceed through the usage of this command, as in::

    $ /path/to/your/project/.venv/bin/alembic init .

Next, we ensure that the local project is also installed, in a development environment
this would be in `editable mode <https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs>`_::

    $ /path/to/your/project/.venv/bin/pip install -e .

As a final step, the `virtualenv activate <https://virtualenv.pypa.io/en/latest/userguide/#activate-script>`_
tool can be used so that the ``alembic`` command is available without any
path information, within the context of the current shell::

    $ source /path/to/your/project/.venv/bin/activate

Dependencies
------------

Alembic's install process will ensure that SQLAlchemy_
is installed, in addition to other dependencies.  Alembic will work with
SQLAlchemy as of version **0.9.0**, however more features are available with
newer versions such as the 1.1 or 1.2 series.

.. versionchanged:: 1.0.0 Support for SQLAlchemy 0.8 and 0.7.9 was dropped.

Alembic supports Python versions 2.7, 3.5 and above.

.. versionchanged::  1.0.0  Support for Python 2.6 and 3.3 was dropped.

.. versionchanged::  1.1.1  Support for Python 3.4 was dropped.

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
