from setuptools import setup, find_packages
import sys
import os
import re

extra = {}
if sys.version_info >= (3, 0):
    extra.update(
        use_2to3=True,
    )

v = open(os.path.join(os.path.dirname(__file__), 'alembic', '__init__.py'))
VERSION = re.compile(r".*__version__ = '(.*?)'", re.S).match(v.read()).group(1)
v.close()


setup(name='alembic',
      version=VERSION,
      description="A database migration tool for SQLAlchemy.",
      long_description="""\
Alembic is an open ended migrations tool.
Basic operation involves the creation of script files, 
each representing a version transition for one or more databases.
The scripts execute within the context of a particular connection 
and transactional configuration that is explicitly constructed.

Key goals of Alembic are:

 * Super-minimalistic migration scripts.  For simple ALTER 
   operations, modifying columns and adding/dropping constraints, 
   no SQLAlchemy constructs are needed, just table and column 
   names plus flags.
 * Transparent and explicit declaration of all configuration 
   as well as the engine/transactional environment in which 
   migrations run, starting with templates which generate the
   migration environment.  The environment can be modified 
   to suit the specifics of the use case.
 * Support for multiple-database configurations, including
   migrations that are run for all / some connections.
 * Support for running migrations transactionally for 
   "transactional DDL" backends, which include Postgresql and 
   Microsoft SQL Server.
 * Allowing any series of migrations to be generated as SQL 
   scripts to standard out, instead of emitting to the database.
 * Support for branched series of migrations, including the
   ability to view branches and "splice" them together.
 * The ability to "prune" old migration scripts, setting the
   "root" of the system to a newer file.
 * The ability to integrate configuration with other frameworks.
   A sample Pylons template is included which pulls all 
   configuration from the Pylons project environment.

""",
      classifiers=[
      'Development Status :: 3 - Alpha',
      'Environment :: Console',
      'Intended Audience :: Developers',
      'Programming Language :: Python',
      'Programming Language :: Python :: 3',
      'Topic :: Database :: Front-Ends',
      ],
      keywords='SQLAlchemy migrations',
      author='Mike Bayer',
      author_email='mike@zzzcomputing.com',
      url='http://bitbucket.org/zzzeek/alembic',
      license='MIT',
      packages=find_packages('.', exclude=['examples*', 'test*']),
      include_package_data=True,
      scripts=['scripts/alembic'],
      tests_require = ['nose >= 0.11'],
      test_suite = "nose.collector",
      zip_safe=False,
      install_requires=[
          'SQLAlchemy>=0.6.0',
          'Mako'
      ],
      entry_points="""
      """,
      **extra
)
