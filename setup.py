from setuptools import __version__
from setuptools import setup

if not int(__version__.partition(".")[0]) >= 47:
    raise RuntimeError(f"Setuptools >= 47 required. Found {__version__}")

setup()
