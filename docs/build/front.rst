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

While Alembic can be installed system wide, it's more common that it's
installed local to a `virtual environment
<https://docs.python.org/3/tutorial/venv.html>`_ , as it also uses libraries
such as SQLAlchemy and database drivers that are more appropriate for
local installations.

The documentation below is **only one kind of approach to installing Alembic
for a project**; there are many such approaches. The documentation below is
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

The next step is **optional**.   If our project itself has a ``setup.py``
file, we can also install it in the local virtual environment in
`editable mode <https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs>`_::

    $ /path/to/your/project/.venv/bin/pip install -e .

If we don't "install" the project locally, that's fine as well; the default
``alembic.ini`` file includes a directive ``prepend_sys_path = .`` so that the
local path is also in ``sys.path``. This allows us to run the ``alembic``
command line tool from this directory without our project being "installed" in
that environment.

.. versionchanged:: 1.5.5  Fixed a long-standing issue where the ``alembic``
   command-line tool would not preserve the default ``sys.path`` of ``.``
   by implementing ``prepend_sys_path`` option.

As a final step, the `virtualenv activate <https://virtualenv.pypa.io/en/latest/userguide/#activate-script>`_
tool can be used so that the ``alembic`` command is available without any
path information, within the context of the current shell::

    $ source /path/to/your/project/.venv/bin/activate

Dependencies
------------

Alembic's install process will ensure that SQLAlchemy_
is installed, in addition to other dependencies.  Alembic will work with
SQLAlchemy as of version **1.3.0**.

.. versionchanged:: 1.5.0 Support for SQLAlchemy older than 1.3.0 was dropped.

Alembic supports Python versions **3.6 and above**

.. versionchanged::  1.7  Alembic now supports Python 3.6 and newer; support
   for Python 2.7 has been dropped.

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
