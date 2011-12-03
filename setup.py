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

readme = os.path.join(os.path.dirname(__file__), 'README.rst')


setup(name='alembic',
      version=VERSION,
      description="A database migration tool for SQLAlchemy.",
      long_description=open(readme).read(),
      classifiers=[
      'Development Status :: 3 - Alpha',
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
      tests_require = ['nose >= 0.11'],
      test_suite = "nose.collector",
      zip_safe=False,
      install_requires=[
          'SQLAlchemy>=0.6.0',
          'Mako',
          # TODO: should this not be here if the env. is 
          # Python 2.7/3.2 ? not sure how this is supposed 
          # to be handled
          'argparse'
      ],
      entry_points = {
        'console_scripts': [ 'alembic = alembic.config:main' ],
      },
      **extra
)
