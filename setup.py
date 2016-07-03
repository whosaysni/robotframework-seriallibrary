#!/usr/bin/env python

from sys import platform

requires = {}

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if platform.startswith('java'):
    try:
        import javax.comm
    except ImportError:
        print ('Remember, PySerial on Jython requires java.comm.')


from os.path import abspath, dirname, join

CURDIR = dirname(abspath(__file__))
VERSION = (0, 0, 0)
execfile(join(CURDIR, 'src', 'SerialLibrary', 'version.py'))
with open(join(CURDIR, 'README.rst')) as readme:
    README = readme.read()
CLASSIFIERS = """
Development Status :: 3 - Alpha
License :: OSI Approved :: Apache Software License
Operating System :: OS Independent
Programming Language :: Python
Topic :: Software Development :: Testing
""".strip()

setup(
    name='robotframework-seriallibrary',
    version='.'.join(map(str, VERSION)),
    description='Robot Framework test library for serial connection',
    long_description=README,
    author='Yasushi Masuda',
    author_email='whosaysni@gmail.com',
    url='https://github.com/whosaysni/SerialLibrary',
    license='Apache License 2.0',
    keywords='robotframework testing testautomation serial',
    platforms='any',
    classifiers=CLASSIFIERS.splitlines(),
    package_dir={'': 'src'},
    packages=['SerialLibrary'],
    requires = dict(
        install_requires=['robotframework', 'pyserial'])
)
