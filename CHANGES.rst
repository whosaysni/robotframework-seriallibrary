Release Notes
=============

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
``RS485Settings`` instance.

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
