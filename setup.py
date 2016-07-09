#!/usr/bin/env python

from imp import load_source
from os.path import abspath, dirname, join
from sys import platform


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if platform.startswith('java'):
    try:
        import javax.comm
    except ImportError:
        print ('Remember, PySerial on Jython requires java.comm.')


CURDIR = dirname(abspath(__file__))
VERSION = load_source(
    'version', 'version',
    open(join(CURDIR, 'src', 'SerialLibrary', 'version.py'))).VERSION
README = open(join(CURDIR, 'README.rst')).read()
CLASSIFIERS = '\n'.join(
    map(' :: '.join, [
        ('Development Status', '3 - Alpha'),
        ('License', 'OSI Approved', 'Apache Software License'),
        ('Operating System', 'OS Independent'),
        ('Programming Language', 'Python'),
        ('Topic', 'Software Development', 'Testing'),
    ])
)


setup(
    name='robotframework-seriallibrary',
    version='.'.join(map(str, VERSION)),
    description='Robot Framework test library for serial connection',
    long_description=README,
    author='Yasushi Masuda',
    author_email='whosaysni@gmail.com',
    url='https://github.com/whosaysni/robotframework-seriallibrary',
    license='Apache License 2.0',
    keywords='robotframework testing testautomation serial',
    platforms='any',
    classifiers=CLASSIFIERS.splitlines(),
    package_dir={'': 'src'},
    packages=['SerialLibrary'],
    install_requires=['robotframework', 'pyserial'],
)
