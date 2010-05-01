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
and transactional configuration that is explicitly constructed.

Key goals of Alembic are:

 * Super-minimalistic migration scripts.  For simple ALTER 
   operations, modifying columns and adding/dropping constraints, 
   no SQLAlchemy constructs are needed, just table and column 
   names plus flags.
 * Transparent and explicit declaration of all configuration 
   as well as the engine/transactional environment in which 
   migrations run, based on templates which generate the
   migration environment.  The environment can be modified 
   to suit the specifics of the use case.
 * Support for multiple-database configurations, including
   migrations that are run for all / some connections.
 * Support for running migrations transactionally for 
   "transactional DDL" backends, which include Postgresql and 
   SQLite.
 * Allowing any series of migrations to be generated as SQL 
   scripts.
 * Support for branched series of migrations, including the
   ability to view branches and "splice" them together.
 * The ability to "prune" old migration scripts, setting the
   "root" of the system to a newer file.
 * The ability to integrate configuration with other frameworks.
   A Pylons template is included which pulls all configuration
   from the Pylons project environment.
    
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
