Release Notes
=============

1.0.0
-------

Rewrite for Robot Framework 7.x. Existing test suites keep working: keyword
names, argument names and order, and error messages are unchanged, and the
0.4.x test suite still passes as is.

Requirements

* Python 3.10+, Robot Framework 7.0+, pySerial 3.5+.

Modernisation

* Keywords are declared with ``@library`` / ``@keyword`` and fully typed, so
  Robot Framework converts and validates arguments and Libdoc shows the types.
* No more deprecated ``robot.utils`` helpers (``is_string``... are removed in
  Robot Framework 9).
* Keywords are tagged (``port``, ``read``, ``write``, ``modem lines``,
  ``configuration``, ``assertion``, ``system``) and the documentation was
  rewritten with sections, tables and examples.
* Acronyms are capitalised in keyword names (``Set RTS``, ``Get CTS Status``,
  ``Set RS485 Mode``...). Matching is case-insensitive, so the old spelling
  still works.
* Packaging moved to PEP 621 metadata built with hatchling.
* Releases are published to PyPI by GitHub Actions and the keyword
  documentation is online at
  https://whosaysni.github.io/robotframework-seriallibrary/.

Fixes

* Boolean port parameters given as text were always true: ``xonxoff=False``
  enabled XON/XOFF. Same for ``Set RS485 Mode`` settings.
* ``stopbits=1.5`` failed.
* ``Write Data`` and ``Read Data Should Be`` failed with ``bytes`` objects.
* ``Add Port    ...    open=False`` opened the port before closing it.
* A port that failed to open could be left half-registered.
* ``Write File Data`` left the file open.
* An unknown encoding was accepted by ``Set Encoding`` and failed later, in an
  unrelated keyword.
* ``Set Input/Output Flow Control`` failed with an ``AttributeError`` on ports
  that do not support it.

New features

* ``Add Port``, ``Set Default Parameters`` and library import fail on unknown
  port parameters instead of silently ignoring them.
* ``Set Default Parameters`` accepts named arguments
  (``Set Default Parameters    baudrate=115200``).
* ``Set RS485 Mode`` has explicit, typed arguments and a new ``enabled``
  argument.
* ``Read All And Log`` returns the data read and accepts the ``TRACE`` and
  ``ERROR`` levels.
* ``Write File Data`` accepts ``pathlib.Path`` objects.
* All ports are closed automatically at the end of the execution.

Behaviour changes

* Unknown port parameters fail (see above).
* ``Set RS485 Mode    delay_before_tx=None``, with no other setting, now
  disables RS485 mode. Use ``enabled=True`` to enable it with defaults.
* ``Set RTS``, ``RTS Should Be`` and the other line keywords fail on values
  that are not booleans (``On``, ``Off``, ``True``, ``1``...) instead of treating
  any text as true.


0.4.2
-------

* Fixed #7: port dictionary keys() no longer subscriptable on Python3.


0.4.1
-------

* Fixed encoding issue. (Thanks @schoener-one, @JasperCraeghs).
* Fixed "Read Until" keyword does not work with multichar terminator.
* Fixed bug introduced by Pyserial3.5+ parameter change (terminator->expected).


0.4.0
-------

Build using poetry.
Dropped Python2 support.


0.3.1
-------

Added Python 3.5+ supprt.

0.2.4
-------

Fixed typo in doc/docstring. (Thanks @gerryqd)

0.2.3
------

Set RS485 Mode now accepts keyword arguments so that
``serial.Serial.rs485_mode`` attribute can be initialized as valid
``RS485Settings`` instance. (`#1`__)

__ https://github.com/whosaysni/robotframework-seriallibrary/issues/1

0.2.2
------

Added 'Write File Data' keyword.


0.2.1
------

More tests.


0.2.0
------

Added regression tests.


0.1.1
------

Initial release.
