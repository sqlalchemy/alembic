from setuptools import setup, find_packages
import os
import re

v = open(os.path.join(os.path.dirname(__file__), 'alembic', '__init__.py'))
VERSION = re.compile(r".*__version__ = '(.*?)'", re.S).match(v.read()).group(1)
v.close()

setup(name='alembic',
      version=VERSION,
      description="A database migration tool for SQLAlchemy."
      long_description="""\
alembic allows the creation of script files which specify a particular revision of a database,
and its movements to other revisions.   The scripting system executes within the context
of a particular connection and transactional configuration, and encourages the usage of 
SQLAlchemy DDLElement constructs and table reflection in order to execute changes to 
schemas.

The current goal of the tool is to allow explicit but minimalistic scripting 
between any two states, with only a simplistic model of dependency traversal
working in the background to execute a series of steps.

The author is well aware that the goal of "minimal and simplistic" is how 
tools both underpowered and massively bloated begin.   It is hoped that 
Alembic's basic idea is useful enough that the tool can remain straightforward
without the need for vast tracts of complexity to be added, but that
remains to be seen.


""",
      classifiers=[
      'Development Status :: 3 - Alpha',
      'Environment :: Console',
      'Intended Audience :: Developers',
      'Programming Language :: Python',
      'Topic :: Database :: Front-Ends',
      ],
      keywords='SQLAlchemy migrations',
      author='Mike Bayer',
      author_email='mike@zzzcomputing.com',
      url='http://bitbucket.org/zzzeek/alembic',
      license='MIT',
      packages=find_packages('.', exclude=['examples*', 'test*']),
      scripts=['scripts/alembic'],
      tests_require = ['nose >= 0.11'],
      test_suite = "nose.collector",
      zip_safe=False,
      install_requires=[
          'SQLAlchemy>=0.6.0',
      ],
      entry_points="""
      """,
)
