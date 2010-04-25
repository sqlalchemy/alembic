from setuptools import setup, find_packages
import os
import re

v = open(os.path.join(os.path.dirname(__file__), 'alembic', '__init__.py'))
VERSION = re.compile(r".*__version__ = '(.*?)'", re.S).match(v.read()).group(1)
v.close()


def datafiles():
    out = []
    for root, dirs, files in os.walk('./templates'):
        if files:
            out.append((root, [os.path.join(root, f) for f in files]))
    return out
    
setup(name='alembic',
      version=VERSION,
      description="A database migration tool for SQLAlchemy.",
      long_description="""\
Alembic is an open ended migrations tool.
Basic operation involves the creation of script files, 
each representing a version transition for one or more databases.  
The scripts execute within the context of a particular connection 
and transactional configuration that is locally configurable.

Key goals of Alembic are:

 * extremely flexible and obvious configuration, including the 
   capability to deal with multiple database setups, both vertical
   and horizontally partioned patterns
 * complete control over the engine/transactional environment 
   in which migrations run, with an emphasis on all migrations running
   under a single transaction per-engine if supported by the 
   underlying database, as well as using two-phase commit if
   running with multiple databases.
 * The ability to generate any set of migration scripts as textual
   SQL files.
 * rudimental capability to deal with source code branches, 
   by organizing migration scripts based on dependency references,
   and providing a "splice" command to bridge two branches.
 * allowing an absolute minimum of typing, both to run commands 
   as well as to create new migrations.   Simple migration
   commands on existing schema constructs use only strings and 
   flags, not requiring the usage of SQLAlchemy metadata objects.
   Columns can be added without the need for Table/MetaData 
   objects.  Engines and connections need not be referenced
   in script files.
 * Old migration files can be deleted if those older versions
   are no longer needed.
 * The ability to integrate seamlessly and simply with frameworks 
   such as Pylons, using the framework's SQLAlchemy environment 
   to keep database connection configuration centralized.
    
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
      data_files=datafiles(),
      tests_require = ['nose >= 0.11'],
      test_suite = "nose.collector",
      zip_safe=False,
      install_requires=[
          'SQLAlchemy>=0.6.0',
          'Mako'
      ],
      entry_points="""
      """,
)
