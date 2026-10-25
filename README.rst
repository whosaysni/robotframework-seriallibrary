=================================
SerialLibrary for Robot Framework
=================================

Robot Framework test library for serial ports, built on
`pySerial <https://pyserial.readthedocs.io>`_.

It drives real ports (``/dev/ttyUSB0``, ``COM3``) as well as any
`pySerial URL <https://pyserial.readthedocs.io/en/latest/url_handlers.html>`_
(``loop://``, ``socket://host:port``, ``rfc2217://host:port``...).

Requirements: Python 3.10+, Robot Framework 7.x, pySerial 3.5+.


Installation
============

.. code:: bash

    pip install robotframework-seriallibrary

.. note::

   `robotframework-pyserial <https://pypi.org/project/robotframework-pyserial/>`_
   is a different library that also installs a ``SerialLibrary`` module, with
   other keywords (``Connect``, ``Write``, ``Read``...). Do not install both in
   the same environment: ``Library    SerialLibrary`` can only load one of them,
   and test suites written for the other one fail with unknown keywords.


Usage
=====

.. code:: robotframework

    *** Settings ***
    Library    SerialLibrary

    *** Test Cases ***
    Hello serial test
        Add Port    loop://
        Write Data    Hello World    encoding=ascii
        Read Data Should Be    Hello World    encoding=ascii
        [Teardown]    Delete All Ports

With a single port, the port, the encoding and the port parameters can be
given when importing the library:

.. code:: robotframework

    *** Settings ***
    Library    SerialLibrary    /dev/ttyUSB0    encoding=ascii    baudrate=115200

    *** Test Cases ***
    Firmware answers to AT
        Write Data    AT\r\n
        ${answer} =    Read Until    OK\r\n    terminator_encoding=ascii
        Should End With    ${answer}    OK\r\n

The default encoding is ``hexlify``, which reads and writes bytes as
space-separated hexadecimal pairs:

.. code:: robotframework

    *** Test Cases ***
    Read until a terminator or a size
        Add Port    loop://    timeout=0.1
        Write Data    01 23 45 0A 67 89 AB CD EF
        ${read} =    Read Until
        Should Be Equal    ${read}    01 23 45 0A
        ${read} =    Read Until    size=2
        Should Be Equal    ${read}    67 89
        ${read} =    Read Until    CD
        Should Be Equal    ${read}    AB CD
        [Teardown]    Delete All Ports

See the `keyword documentation <https://whosaysni.github.io/robotframework-seriallibrary/>`_
for all keywords.


Development
===========

.. code:: bash

    python -m venv .venv
    .venv/bin/pip install -e .[dev]
    .venv/bin/pytest                                   # unit tests
    .venv/bin/robot --outputdir results tests/acceptance  # acceptance tests
    .venv/bin/ruff check src tests tools && .venv/bin/robocop check tests
    .venv/bin/python tools/libdoc.py                   # keyword documentation

``tests/hardware`` runs against a real ESP32 board (auto-reset wiring on
DTR/RTS); it only resets the board and reads its boot log:

.. code:: bash

    .venv/bin/robot --variable PORT:/dev/ttyUSB0 --outputdir results tests/hardware

``tests/acceptance/legacy`` holds the original 0.4.x test suite, kept
unchanged to make sure existing test suites keep working.

See `CONTRIBUTING.rst <https://github.com/whosaysni/robotframework-seriallibrary/blob/develop/CONTRIBUTING.rst>`_
to report a bug, propose a change or make a release.
