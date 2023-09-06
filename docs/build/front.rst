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

Alembic supports Python versions **3.7 and above**

.. versionchanged::  1.8  Alembic now supports Python 3.7 and newer.
.. versionchanged::  1.7  Alembic now supports Python 3.6 and newer; support
   for Python 2.7 has been dropped.

.. _versioning_scheme:

Versioning Scheme
-----------------

Alembic's versioning scheme is based on that of
`SQLAlchemy's versioning scheme <https://www.sqlalchemy.org/download.html#versions>`_.
In particular, it should be noted that while Alembic uses a three-number
versioning scheme, it **does not use SemVer**. In SQLAlchemy and Alembic's
scheme, **the middle digit is considered to be a "Significant Minor Release",
which may include removal of previously deprecated APIs with some risk of
non-backwards compatibility in a very small number of cases**.

This means that version "1.8.0", "1.9.0", "1.10.0", "1.11.0", etc. are
**Significant Minor Releases**, which will include new API features and may
remove or modify existing ones.

Therefore, when `pinning <https://pip.pypa.io/en/stable/topics/repeatable-installs/>`_
Alembic releases, pin to the "major" and "minor" digits to avoid API changes.

A true "Major" release such as a change to "2.0" would include complete
redesigns/re-architectures of foundational features; currently no such series
of changes are planned, although changes such as replacing the entire
"autogenerate" scheme with a new approach would qualify for that level of
change.



Community
=========

Alembic is developed by `Mike Bayer <http://techspot.zzzeek.org>`_, and is
part of the SQLAlchemy_ project.

User issues, discussion of potential bugs and features are most easily
discussed using `GitHub Discussions <https://github.com/sqlalchemy/alembic/discussions/>`_.

.. _bugs:

Bugs
====

Bugs and feature enhancements to Alembic should be reported on the `GitHub
issue tracker
<https://github.com/sqlalchemy/alembic/issues/>`_.

.. _SQLAlchemy: https://www.sqlalchemy.org
