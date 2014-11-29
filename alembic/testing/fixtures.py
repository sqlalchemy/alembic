# coding: utf-8
import io
import re

from sqlalchemy import create_engine, text, MetaData

import alembic
from alembic.compat import configparser
from alembic import util
from alembic.compat import string_types, text_type
from alembic.migration import MigrationContext
from alembic.environment import EnvironmentContext
from alembic.operations import Operations
from alembic.ddl.impl import _impls
from contextlib import contextmanager
from .plugin.plugin_base import SkipTest
from .assertions import _get_dialect, eq_
from . import mock

testing_config = configparser.ConfigParser()
testing_config.read(['test.cfg'])


if not util.sqla_094:
    class TestBase(object):
        # A sequence of database names to always run, regardless of the
        # constraints below.
        __whitelist__ = ()

        # A sequence of requirement names matching testing.requires decorators
        __requires__ = ()

        # A sequence of dialect names to exclude from the test class.
        __unsupported_on__ = ()

        # If present, test class is only runnable for the *single* specified
        # dialect.  If you need multiple, use __unsupported_on__ and invert.
        __only_on__ = None

        # A sequence of no-arg callables. If any are True, the entire testcase is
        # skipped.
        __skip_if__ = None

        def assert_(self, val, msg=None):
            assert val, msg

        # apparently a handful of tests are doing this....OK
        def setup(self):
            if hasattr(self, "setUp"):
                self.setUp()

        def teardown(self):
            if hasattr(self, "tearDown"):
                self.tearDown()
else:
    from sqlalchemy.testing.fixtures import TestBase


def capture_db():
    buf = []

    def dump(sql, *multiparams, **params):
        buf.append(str(sql.compile(dialect=engine.dialect)))
    engine = create_engine("postgresql://", strategy="mock", executor=dump)
    return engine, buf

_engs = {}


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
            self.connection = mock.Mock(dialect=dialect)

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

