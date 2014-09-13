# coding: utf-8
import io
import os
import re
import shutil
import textwrap

from nose import SkipTest
from sqlalchemy.engine import default
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.util import decorator

import alembic
from alembic.compat import configparser
from alembic import util
from alembic.compat import string_types, text_type, u, py33
from alembic.migration import MigrationContext
from alembic.environment import EnvironmentContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory, Script
from alembic.ddl.impl import _impls
from contextlib import contextmanager

from sqlalchemy.testing.fixtures import TestBase
from .assertions import _get_dialect, eq_

testing_config = configparser.ConfigParser()
testing_config.read(['test.cfg'])


def capture_db():
    buf = []

    def dump(sql, *multiparams, **params):
        buf.append(str(sql.compile(dialect=engine.dialect)))
    engine = create_engine("postgresql://", strategy="mock", executor=dump)
    return engine, buf

_engs = {}


@decorator
def requires_08(fn, *arg, **kw):
    if not util.sqla_08:
        raise SkipTest("SQLAlchemy 0.8.0b2 or greater required")
    return fn(*arg, **kw)


@decorator
def requires_09(fn, *arg, **kw):
    if not util.sqla_09:
        raise SkipTest("SQLAlchemy 0.9 or greater required")
    return fn(*arg, **kw)


@decorator
def requires_092(fn, *arg, **kw):
    if not util.sqla_092:
        raise SkipTest("SQLAlchemy 0.9.2 or greater required")
    return fn(*arg, **kw)


@decorator
def requires_094(fn, *arg, **kw):
    if not util.sqla_094:
        raise SkipTest("SQLAlchemy 0.9.4 or greater required")
    return fn(*arg, **kw)


@contextmanager
def capture_context_buffer(**kw):
    if kw.pop('bytes_io', False):
        buf = io.BytesIO()
    else:
        buf = io.StringIO()

    kw.update({
        'dialect_name': "sqlite",
        'output_buffer': buf
    })
    conf = EnvironmentContext.configure

    def configure(*arg, **opt):
        opt.update(**kw)
        return conf(*arg, **opt)

    with mock.patch.object(EnvironmentContext, "configure", configure):
        yield buf


def op_fixture(dialect='default', as_sql=False, naming_convention=None):
    impl = _impls[dialect]

    class Impl(impl):

        def __init__(self, dialect, as_sql):
            self.assertion = []
            self.dialect = dialect
            self.as_sql = as_sql
            # TODO: this might need to
            # be more like a real connection
            # as tests get more involved
            self.connection = None

        def _exec(self, construct, *args, **kw):
            if isinstance(construct, string_types):
                construct = text(construct)
            assert construct.supports_execution
            sql = text_type(construct.compile(dialect=self.dialect))
            sql = re.sub(r'[\n\t]', '', sql)
            self.assertion.append(
                sql
            )

    opts = {}
    if naming_convention:
        if not util.sqla_092:
            raise SkipTest(
                "naming_convention feature requires "
                "sqla 0.9.2 or greater")
        opts['target_metadata'] = MetaData(naming_convention=naming_convention)

    class ctx(MigrationContext):

        def __init__(self, dialect='default', as_sql=False):
            self.dialect = _get_dialect(dialect)
            self.impl = Impl(self.dialect, as_sql)
            self.opts = opts
            self.as_sql = as_sql

        def assert_(self, *sql):
            # TODO: make this more flexible about
            # whitespace and such
            eq_(self.impl.assertion, list(sql))

        def assert_contains(self, sql):
            for stmt in self.impl.assertion:
                if sql in stmt:
                    return
            else:
                assert False, "Could not locate fragment %r in %r" % (
                    sql,
                    self.impl.assertion
                )
    context = ctx(dialect, as_sql)
    alembic.op._proxy = Operations(context)
    return context

