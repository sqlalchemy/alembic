from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import os
import re
import sys


v = open(os.path.join(os.path.dirname(__file__), 'alembic', '__init__.py'))
VERSION = re.compile(r".*__version__ = '(.*?)'", re.S).match(v.read()).group(1)
v.close()


readme = os.path.join(os.path.dirname(__file__), 'README.rst')

requires = [
    'SQLAlchemy>=0.7.6',
    'Mako',
    'python-editor>=0.3',
]

try:
    import argparse
except ImportError:
    requires.append('argparse')


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(name='alembic',
      version=VERSION,
      description="A database migration tool for SQLAlchemy.",
      long_description=open(readme).read(),
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: Implementation :: CPython',
          'Programming Language :: Python :: Implementation :: PyPy',
          'Topic :: Database :: Front-Ends',
      ],
      keywords='SQLAlchemy migrations',
      author='Mike Bayer',
      author_email='mike@zzzcomputing.com',
      url='http://bitbucket.org/zzzeek/alembic',
      license='MIT',
      packages=find_packages('.', exclude=['examples*', 'test*']),
      include_package_data=True,
      tests_require=['pytest', 'mock', 'Mako'],
      cmdclass={'test': PyTest},
      zip_safe=False,
      install_requires=requires,
      entry_points={
          'console_scripts': ['alembic = alembic.config:main'],
      }
      )
