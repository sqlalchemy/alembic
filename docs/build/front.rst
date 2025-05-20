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

To build a virtual environment for a specific project, a virtual environment
can be created using the
`Python venv library <https://docs.python.org/3/library/venv.html>`_::

    $ cd /path/to/your/project
    $ python -m venv .venv

There is now a Python interpreter that you can access in
``/path/to/your/project/.venv/bin/python``, as well as the `pip
<http://pypi.python.org/pypi/pip>`_ installer tool in
``/path/to/your/project/.venv/bin/pip``.

Next,the ``activate`` command installed by venv can be used so that
all binaries local to this new Python environment are in the local path::

    $ source /path/to/your/project/.venv/bin/activate

We now install Alembic as follows::

    $ pip install alembic

The install will add the ``alembic`` command to the virtual environment.  All
operations with Alembic in terms of this specific virtual environment will then
proceed through the usage of this command, as in::

    $ alembic init alembic

Finally, assuming your project is itself installable, meaning it has a
``pyproject.toml`` file, and/or ``setup.py`` script, the local project can
be made a part of the same local environment by installing it with ``pip``,
optionally using "editable" mode::

    $ pip install -e .



Dependencies
------------

Alembic's install process will ensure that SQLAlchemy_
is installed, in addition to other dependencies.  Alembic will work with
SQLAlchemy as of version **1.4.0**.

.. versionchanged:: 1.15.0 Support for SQLAlchemy older than 1.4.0 was dropped.

Alembic supports Python versions **3.9 and above**

.. versionchanged::  1.15  Alembic now supports Python 3.9 and newer.

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
