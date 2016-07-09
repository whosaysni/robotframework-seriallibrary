SerialLibrary
=============
Version:          (0, 2, 0)
Scope:            global
Named arguments:  supported

Robot Framework test library for manipulating serial ports

Using Library
--------------

Most simple use is to just import library and add port::

    *** settings ***
    Library    SerialLibrary

    *** test cases ***
    Hello serial test
        Add Port    loop://
        Write Data    Hello World    encoding=ascii
        Read Data Should Be    Hello World    encoding=ascii

Or, if you play with only one port and send ascii-only, more simply::

    *** settings ***
    Library    SerialLibrary    loop://    encoding=ascii

    *** test cases ***
    Hello serial test
         Write Data    Hello World
         Read Data Should Be    Hello World


Default Parameters
-------------------

Default parameter values except timeouts are set as same as SerialBase.
Default value or timeout and writer_timeout are set to 1.0.


Current port and port names
----------------------------

You may have several ports in a library instance simultaneously.
All ports added to the instance can be identified by its name, which
is taken from port name given at importing library or Add Port keyword
(Thus you cannot maintain multiple ports with same name).
Those ports are maintained in an internal dictionary and lives until
explicitly deleted from the library instance using Delete (All) Port(s).
Most of keywords in the library have `port_locator` parameter which
can be used to specify the port to manipulate.

The library has an idea of current port. Current port is the default
port used if `port_locator` parameter is omitted.  The first port added
to the library instance always becomes current port and you may freely
switch it with Switch Port keyword. If current port is deleted, most
recently added port is made current.


Port timeouts
--------------

Default (read/write) timeouts are set to 1.0 while pySerial defaults
are None (blocking). This is because there is no way to abort blocked
port from the library at this moment. If you really want blocking
port, carefully design your test to avoid infinite execution blocking.

Importing
---------
Arguments:  [port_locator=None, encoding=hexlify, \*\*kwargs]

Import Library.

If library is imported without parameters, no ports are prepared.
Importing library with port_locator parameter will add new port
with given name and make it as default port (current port).

If `encoding` is specified, all messages sent to serial port
will be encoded by specified encoding, also all bytes read back
from the port will be decoded as same way.
Default value is 'hexlify' that formats a byte sequence with
space-separated hex strings. Setting any other encoding is
possible, but please note:
- If your device dumps non-decodable byte sequence, read-related
keywords will fail to decode bytes.
- If your device is too slow to read, read-related keywords
may return incomplete byte sequence that unable to decode.

`kwargs` can be used to set library-instance-wide default value
to create new port instance internally. The 'default' default
values are taken from serial.SerialBase, except timeout/write_timeout
that are set to 1.0/1.0, respectively.

Add Port
--------
Arguments:  [port_locator, open=True, make_current=False, \*\*kwargs]

Adds new port with specified locator.

port_locator may be in (traditional) port name or url format.
If `open` has false value, the port is closed immediately.
Parameters given in kwargs will override those library defaults
initialized on import.
If make_current has truth value, the opened port is set to current
port. Note that if there's only one port in the library instance,
it will always be current port, regardless of make_current's value.

Fails if specified port_locator is already used in this library
instance.

Returns created port instance.

Cd Should Be
------------
Arguments:  [value, port_locator=None]

Fails if CD is not expected status.

Close Port
----------
Arguments:  [port_locator=None]

Closes specified port.

Closes current or specified port.
Current port is closed if port_locator is ommitted.
This keyword does nothing if port is not opened.
Fails if specified port is not found.

Com Port Should Exist Regexp
----------------------------
Arguments:  [regexp]

Fails if com port matching given pattern is not found on the system.

This keyword uses serial.tools.list_ports.grep internally thus
port name, description and hardware ID are searched.

Returns list of com ports matching the pattern, if exists.

Cts Should Be
-------------
Arguments:  [value, port_locator=None]

Fails if CTS is not expected status.

Current Port Should Be
----------------------
Arguments:  [port_locator]

Fails if given port locator does not match current port locator.

Current Port Should Be Regexp
-----------------------------
Arguments:  [port_locator_regexp]

Fails if given regexp does not match current port locator.

If current port is None, it will only match to empty sring.
Matching is case-insensitive.

Delete All Ports
----------------
Arguments:  []

Deletes all ports maintained in the library instance.

Opened ports are closed before deletion.

Delete Port
-----------
Arguments:  [port_locator=None]

Deletes specified port.

Port is closed if it is opened.
By default, current port is deleted and most recently added
ports is selected as new current port. Deleting last port
in the library instance makes current port set to None.
Fails if specified port is not found or attempt to delete
current port if it is set to None.

Dsr Should Be
-------------
Arguments:  [value, port_locator=None]

Fails if DSR is not expected status.

Dtr Should Be
-------------
Arguments:  [value, port_locator=None]

Fails if DTR status is not specified value.

Flush Port
----------
Arguments:  [port_locator=None]

Flush port so that all waiting data is processed.

Get Cd Status
-------------
Arguments:  [port_locator=None]

Returns CD (Carrier Detect) status.

Get Cts Status
--------------
Arguments:  [port_locator=None]

Returns CTS (Clear To Send) status.

Get Current Port Locator
------------------------
Arguments:  []

Returns port locator of current port.
If no port is associated to the current port (implies no port
in the library instance), None is returned.

Get Dsr Status
--------------
Arguments:  [port_locator=None]

Returns DSR (Data Set Ready) status.

Get Encoding
------------
Arguments:  []

Returns default encoding for the library instance.

Get Port Parameter
------------------
Arguments:  [param_name, port_locator=None]

Returns specified parameter of the port.

By default, current port is inspected.
Available parameters are those can be set at library import
or Add Port keyword: baudrate, bytesize, parity, stopbits,
timeout, xonxoff, rtscts, write_timeout, dsrdtr and
inter_byte_timeout.

Fails on wrong param_name or port_locator.

Get Ri Status
-------------
Arguments:  [port_locator=None]

Returns RI (Ring Indicator) status.

List Com Port Names
-------------------
Arguments:  []

Returns list of device names for com ports found on the system.

Items are sorted in dictionary order.

List Com Ports
--------------
Arguments:  []

Returns list of com ports found on the system.

This is thin-wrapper of serial.tools.list_ports.
Returned list consists of possible ListPortInfo instances.
You may access attributes of ListPortInfo by extended variable
syntax, e.g.::

    @{ports} =   List Ports
    Log  ${ports[0].device}

Open Port
---------
Arguments:  [port_locator=None]

Opens specified port.

If port_locator is ommitted, current port is opened.
If port is opened already, this keyword does nothing.
Fails if specified port is not found.

Port Should Be Closed
---------------------
Arguments:  [port_locator=None]

Fails if specified port is open.

Port Should Be Open
-------------------
Arguments:  [port_locator=None]

Fails if specified port is closed.

Port Should Have Unread Bytes
-----------------------------
Arguments:  [port_locator=None]

Fails if port input buffer does not contain data.
Fails if the port is closed.

Port Should Have Unsent Bytes
-----------------------------
Arguments:  [port_locator=None]

Fails if port output buffer does not contain data.
Also fails if the port is closed.
Not that if platform does not support out_waiting, this
keyword will fail.

Port Should Not Have Unread Bytes
---------------------------------
Arguments:  [port_locator=None]

Fails if port input buffer contains data.
Fails if the port is closed.

Port Should Not Have Unsent Bytes
---------------------------------
Arguments:  [port_locator=None]

Fails if port output buffer contains data.
Fails if the port is closed.

Read All And Log
----------------
Arguments:  [loglevel=debug, encoding=None, port_locator=None]

Read all available data and write it to log.

This is useful if you want to discard bytes in read queue, but just want
to log it.
Loglevel can be 'info', 'debug' or 'warn' (case insensitive).
Any other level causes error.
If `encoding` is not given, default encoding is used.

Read All Data
-------------
Arguments:  [encoding=None, port_locator=None]

Read all available data from the port's incoming buffer.

If `encoding` is not given, default encoding is used.

Read Data Should Be
-------------------
Arguments:  [data, encoding=None, port_locator=None]

Fails if all read bytes from the port not equals to specifed data.

This keyword compares values in byte space; data is encoded to bytes
then compared to bytes read from the port.

Read N Bytes
------------
Arguments:  [size=1, encoding=None, port_locator=None]

Reads specified number of bytes from the port.

Note that if no timeout is specified this keyword may block
until the requested number of bytes is read.
Returns (encoded) read data.

Read Until
----------
Arguments:  [terminator= , size=None, encoding=None, port_locator=None]

Read until a termination sequence is found, size exceeded or timeout.

If `encoding` is not given, default encoding is used.
Note that encoding affects terminator too, so if you want to use
character 'X' as terminator and encoding=hexlify (default), you should
call this keyword as Read Until terminator=58.

Reset Default Parameters
------------------------
Arguments:  []

Resets default parameters to those defined in serial.SerialBase.

This keyword does not directly affect those exisitng ports added
so far.

Reset Input Buffer
------------------
Arguments:  [port_locator=None]

Clears input buffer.

All data in the port's input buffer will be descarded.
Fails if the port is closed.

Reset Output Buffer
-------------------
Arguments:  [port_locator=None]

Clears outout buffer.

All data in the port's output buffer will be descarded.
Fails if the port is closed.

Ri Should Be
------------
Arguments:  [value, port_locator=None]

Fails if RI is not expected status.

Rts Should Be
-------------
Arguments:  [value, port_locator=None]

Fails if RTS status is not specified value.

Send Break
----------
Arguments:  [duration=0.25, port_locator=None]

Sends BREAK to port.

The semantics of duration is same as pySerial's send_break.

Set Default Parameters
----------------------
Arguments:  [params]

Updates default parameters with given dictionary.

Argument `params` should be a dictionary variable.
Only supported parameters are taken into account,
while others are ignored silently.
Values can be in any types and are converted into
appropreate type.

Set Dtr
-------
Arguments:  [value, port_locator=None]

Sets DTR (Data Terminal Ready) status.

Set Encoding
------------
Arguments:  [encoding=None]

Sets default encoding for the library instance.

Returns previous encoding.
If encoding is set to None, just returns current encoding.

Set Input Flow Control
----------------------
Arguments:  [enable=True, port_locator=None]

[Unsupported] Sets input flow control status on the port.

Fails if platforms that does not support the feature.

Set Output Flow Control
-----------------------
Arguments:  [enable=True, port_locator=None]

[Unsupported] Sets input flow control status on the port.

Fails if the platform that does not support the feature.

Set Port Parameter
------------------
Arguments:  [param_name, value, port_locator=None]

Sets port parameter.

By default, current port is affected.
Available parameters are same as Get Port Parameter keyword.
For most parameter, changing it on opened port will cause
port reconfiguration.
Fails on wrong param_name or port_locator.
Returns previous value.

Set Rs485 Mode
--------------
Arguments:  [status, port_locator=None]

Sets RS485 mode on the port.

Fails if the platform that does not support the feature.

Set Rts
-------
Arguments:  [value, port_locator=None]

Sets RTS (Request To Send) status.

Switch Port
-----------
Arguments:  [port_locator]

Make specified port as current port.

Fails if specified port is not added in the library
instance.

Write Data
----------
Arguments:  [data, encoding=None, port_locator=None]

Writes data into the port.

If data is a Python's byte string object, it will be written
to the port intact. If data is unicode string, it will be
encoded with given encoding before writing. Otherwise,
data is converted to unicode and processed same as unicode string.

