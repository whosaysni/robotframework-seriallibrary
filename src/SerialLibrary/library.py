import codecs
import re
from collections.abc import Mapping
from os import SEEK_CUR, PathLike
from pathlib import Path
from typing import Any, BinaryIO

from robot.api import Error, Failure, TypeInfo, logger
from robot.api.deco import keyword, library
from serial import SerialBase, serial_for_url
from serial.rs485 import RS485Settings
from serial.serialutil import LF
from serial.tools.list_ports import comports, grep
from serial.tools.list_ports_common import ListPortInfo

from . import hexlify
from .version import __version__

CURRENT_PORT = "_"
DEFAULT_ENCODING = hexlify.NAME

# Settings accepted by `Add Port`, `Set Default Parameters` and friends,
# with the type their values are converted to.
PORT_PARAMETER_TYPES: dict[str, Any] = {
    "baudrate": int,
    "bytesize": int,
    "parity": str,
    "stopbits": int | float,
    "xonxoff": bool,
    "dsrdtr": bool,
    "rtscts": bool,
    "timeout": float | None,
    "write_timeout": float | None,
    "inter_byte_timeout": float | None,
}

DEFAULT_SETTINGS: dict[str, Any] = SerialBase(timeout=1.0, write_timeout=1.0, inter_byte_timeout=0.0).get_settings()

LOG_LEVELS = {
    "TRACE": logger.trace,
    "DEBUG": logger.debug,
    "INFO": logger.info,
    "WARN": logger.warn,
    "WARNING": logger.warn,
    "ERROR": logger.error,
}


def _to_bool(value: Any, name: str) -> bool:
    """Robot converts ``On``/``Off``, ``yes``/``no``, ``1``/``0``... to bool and
    passes other strings through untouched; reject those instead of treating
    every non-empty string as true."""
    if isinstance(value, (bool, int, float)):
        return bool(value)
    raise Error(f"Argument '{name}' got value '{value}' that cannot be converted to a boolean.")


def _to_on_off(value: Any) -> str:
    return "On" if value else "Off"


def _convert_parameters(params: Mapping[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(params) - set(PORT_PARAMETER_TYPES))
    if unknown:
        raise Error(
            f"Unknown port parameter(s): {', '.join(unknown)}. Valid parameters are: {', '.join(PORT_PARAMETER_TYPES)}."
        )
    converted = {}
    for name, value in params.items():
        value = TypeInfo.from_type_hint(PORT_PARAMETER_TYPES[name]).convert(value, name)
        if PORT_PARAMETER_TYPES[name] is bool:
            value = _to_bool(value, name)
        converted[name] = value
    return converted


def _check_encoding(encoding: str) -> str:
    try:
        codecs.lookup(encoding)
    except LookupError:
        raise Error(f"Unknown encoding '{encoding}'.") from None
    return encoding


class _PortCloser:
    """Library listener closing every port when the library goes out of scope."""

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, library: "SerialLibrary"):
        self._library = library

    def close(self) -> None:
        self._library.delete_all_ports()


@library(scope="GLOBAL", version=__version__, doc_format="ROBOT", auto_keywords=False)
class SerialLibrary:
    """Robot Framework library for testing devices over serial ports.

    SerialLibrary is built on [https://pyserial.readthedocs.io|pySerial]. It can
    drive real ports (``/dev/ttyUSB0``, ``COM3``) as well as any
    [https://pyserial.readthedocs.io/en/latest/url_handlers.html|pySerial URL]
    such as ``loop://``, ``socket://host:port`` or ``rfc2217://host:port``.

    == Table of contents ==

    %TOC%

    = Usage =

    Import the library and add a port:

    | * Settings *
    | Library    SerialLibrary
    |
    | * Test Cases *
    | Hello serial test
    |     `Add Port`               loop://
    |     `Write Data`             Hello World    encoding=ascii
    |     `Read Data Should Be`    Hello World    encoding=ascii
    |     [Teardown]    `Delete All Ports`

    When a suite talks to a single port, the port and the encoding can be
    given when importing the library:

    | * Settings *
    | Library    SerialLibrary    /dev/ttyUSB0    encoding=ascii    baudrate=115200
    |
    | * Test Cases *
    | Hello serial test
    |     `Write Data`             Hello World
    |     `Read Data Should Be`    Hello World

    = Ports and the current port =

    A library instance can hold several ports at once. Each port is identified
    by its _port locator_: the device name or URL given to `Add Port` (or at
    import). The same locator cannot be added twice.

    The library keeps track of a _current port_. Keywords accept an optional
    ``port_locator`` argument; when it is omitted, or set to ``_``, the current
    port is used. The first port added becomes current, `Switch Port` (or
    ``make_current=True`` in `Add Port`) changes it, and when the current port
    is deleted the most recently added remaining port becomes current.

    All ports still open are closed automatically at the end of the execution.

    = Encodings =

    Data written to and read from a port are converted between text and bytes
    with an _encoding_. The default encoding is ``hexlify``: bytes are written
    and read as space-separated hexadecimal pairs, e.g. ``01 23 AB``. Any
    [https://docs.python.org/3/library/codecs.html#standard-encodings|Python
    encoding] can be used instead, library-wide (at import or with
    `Set Encoding`) or per keyword call with the ``encoding`` argument.

    With text encodings, keep in mind that:
    - a device sending bytes that are invalid in the encoding produces
      replacement characters,
    - a read that stops in the middle of a multi-byte character returns an
      incomplete sequence.

    `Write Data` and `Read Data Should Be` also accept ``bytes`` objects, which
    are used as is, whatever the encoding.

    = Port parameters =

    The following parameters can be given at import (as library-wide
    defaults), to `Add Port`, `Set Default Parameters`, `Get Port Parameter`
    and `Set Port Parameter`. Values are converted to the right type
    automatically.

    | = Parameter =          | = Type =         | = Default = | = Description =                          |
    | ``baudrate``           | int              | 9600        | Speed in bits per second.                |
    | ``bytesize``           | int              | 8           | Data bits: 5, 6, 7 or 8.                 |
    | ``parity``             | str              | N           | ``N``, ``E``, ``O``, ``M`` or ``S``.     |
    | ``stopbits``           | int or float     | 1           | 1, 1.5 or 2.                             |
    | ``xonxoff``            | bool             | False       | Software flow control.                   |
    | ``rtscts``             | bool             | False       | RTS/CTS hardware flow control.           |
    | ``dsrdtr``             | bool             | False       | DSR/DTR hardware flow control.           |
    | ``timeout``            | float or None    | 1.0         | Read timeout in seconds.                 |
    | ``write_timeout``      | float or None    | 1.0         | Write timeout in seconds.                |
    | ``inter_byte_timeout`` | float or None    | 0.0         | Timeout between bytes, 0 disables it.    |

    Unknown parameter names fail, so typos do not go unnoticed.

    = Timeouts =

    The default read and write timeouts are 1 second, whereas pySerial blocks
    forever by default. A blocked read cannot be interrupted from Robot
    Framework, so only use ``timeout=None`` if you are sure the device
    answers.
    """

    def __init__(self, port_locator: str | None = None, encoding: str = DEFAULT_ENCODING, **kwargs: Any):
        """Imports the library, optionally adding a first port.

        ``port_locator`` is added with `Add Port` and becomes the current port.

        ``encoding`` is the default encoding of the library, see
        `Encodings`.

        ``kwargs`` set the library-wide default values of the
        `port parameters`, e.g. ``baudrate=115200``.
        """
        self._encoding = _check_encoding(encoding)
        self._ports: dict[str, SerialBase] = {}
        self._defaults: dict[str, Any] = dict(DEFAULT_SETTINGS)
        self._current_port_locator: str | None = None
        self.ROBOT_LIBRARY_LISTENER = _PortCloser(self)
        self.set_default_parameters(kwargs)
        if port_locator is not None:
            self.add_port(port_locator)

    # ----------------------------------------------------------------------
    # Internal helpers

    def _port(self, port_locator: str | None = None) -> SerialBase:
        if port_locator in (None, CURRENT_PORT):
            port_locator = self._current_port_locator
        if port_locator not in self._ports:
            raise Error("No such port.")
        return self._ports[port_locator]

    def _encode(self, data: str | bytes, encoding: str | None = None, encoding_mode: str | None = None) -> bytes:
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        return data.encode(encoding or self._encoding, encoding_mode or "strict")

    def _decode(self, data: bytes, encoding: str | None = None, encoding_mode: str | None = None) -> str:
        return data.decode(encoding or self._encoding, encoding_mode or "replace")

    # ----------------------------------------------------------------------
    # Encoding

    @keyword(tags=["configuration"])
    def get_encoding(self) -> str:
        """Returns the default encoding of the library.

        See `Encodings`.
        """
        return self._encoding

    @keyword(tags=["configuration"])
    def set_encoding(self, encoding: str | None = None) -> str:
        """Sets the default encoding of the library and returns the previous one.

        Without ``encoding``, only returns the current encoding.
        Fails if the encoding is unknown. See `Encodings`.
        """
        previous = self._encoding
        if encoding:
            self._encoding = _check_encoding(encoding)
        return previous

    # ----------------------------------------------------------------------
    # System ports

    @keyword("List COM Ports", tags=["system"])
    def list_com_ports(self) -> list[ListPortInfo]:
        """Returns the serial ports found on the system.

        Items are pySerial ``ListPortInfo`` objects, whose attributes are
        available with the extended variable syntax:

        | @{ports} =    `List COM Ports`
        | Log    ${ports}[0].device
        | Log    ${ports}[0].description
        """
        return comports()

    @keyword("List COM Port Names", tags=["system"])
    def list_com_port_names(self) -> list[str]:
        """Returns the sorted device names of the serial ports found on the system."""
        return sorted(port_info.device for port_info in self.list_com_ports())

    @keyword("COM Port Should Exist Regexp", tags=["system", "assertion"])
    def com_port_should_exist_regexp(self, regexp: str) -> list[ListPortInfo]:
        """Fails if no serial port on the system matches ``regexp``.

        The device name, description and hardware ID of each port are
        searched. Returns the matching ports.

        | `COM Port Should Exist Regexp`    USB VID:PID=0403:6001
        """
        found = list(grep(regexp))
        if not found:
            raise Failure("Matching port does not exist.")
        return found

    # ----------------------------------------------------------------------
    # Default parameters

    @keyword(tags=["configuration"])
    def set_default_parameters(self, params: Mapping[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        """Updates the library-wide default `port parameters`.

        Parameters can be given as a dictionary, as named arguments, or both.
        Ports added afterwards use the new defaults; existing ports are not
        affected. Returns the previous defaults.

        | &{params} =    Create Dictionary    baudrate=115200    timeout=2
        | `Set Default Parameters`    ${params}
        | `Set Default Parameters`    baudrate=115200    timeout=2
        """
        previous = dict(self._defaults)
        self._defaults.update(_convert_parameters({**(params or {}), **kwargs}))
        return previous

    @keyword(tags=["configuration"])
    def reset_default_parameters(self) -> None:
        """Resets the default `port parameters` to their initial values.

        Existing ports are not affected.
        """
        self._defaults = dict(DEFAULT_SETTINGS)

    # ----------------------------------------------------------------------
    # Port management

    @keyword(tags=["port"])
    def get_current_port_locator(self) -> str | None:
        """Returns the locator of the current port, or ``None`` if there is none."""
        return self._current_port_locator

    @keyword(tags=["port", "assertion"])
    def current_port_should_be(self, port_locator: str | None) -> None:
        """Fails if the current port is not ``port_locator``."""
        if port_locator not in (self._current_port_locator, CURRENT_PORT):
            raise Failure("Port does not match.")

    @keyword(tags=["port", "assertion"])
    def current_port_should_be_regexp(self, port_locator_regexp: str) -> None:
        """Fails if the current port locator does not match ``port_locator_regexp``.

        Matching is case-insensitive and anchored at the beginning of the
        locator. When there is no current port, only an empty pattern matches.
        """
        if not re.match(port_locator_regexp, self._current_port_locator or "", re.IGNORECASE):
            raise Failure("Port does not match.")

    @keyword(tags=["port"])
    def add_port(
        self,
        port_locator: str | None,
        open: bool = True,
        make_current: bool = False,
        **kwargs: Any,
    ) -> SerialBase:
        """Adds a new port and returns the underlying pySerial object.

        ``port_locator`` is a device name (``/dev/ttyUSB0``, ``COM3``) or a
        pySerial URL (``loop://``, ``socket://host:port``...).

        The port is opened unless ``open`` is false. It becomes the current
        port if ``make_current`` is true or if it is the only port.

        ``kwargs`` override the default `port parameters` for this port.

        Fails if the locator is invalid or already used.

        | `Add Port`    /dev/ttyUSB0    baudrate=115200    timeout=0.5
        | `Add Port`    loop://         open=False    make_current=True
        """
        if port_locator in (None, "", CURRENT_PORT):
            raise Error("Invalid port locator.")
        if port_locator in self._ports:
            raise Error("Port already exists.")
        settings = {**self._defaults, **_convert_parameters(kwargs)}
        port = serial_for_url(port_locator, do_not_open=True, **settings)
        if _to_bool(open, "open"):
            port.open()
        self._ports[port_locator] = port
        if self._current_port_locator is None or _to_bool(make_current, "make_current"):
            self._current_port_locator = port_locator
        logger.debug(f"Added port '{port_locator}' with settings {port.get_settings()}.")
        return port

    @keyword(tags=["port"])
    def delete_port(self, port_locator: str | None = None) -> None:
        """Closes and deletes a port, the current port by default.

        If the current port is deleted, the most recently added remaining port
        becomes current. Fails if the port does not exist.
        """
        if port_locator is None:
            port_locator = self._current_port_locator
        if port_locator not in self._ports:
            raise Error("Invalid port locator.")
        self._ports.pop(port_locator).close()
        if port_locator == self._current_port_locator:
            self._current_port_locator = next(reversed(self._ports), None)

    @keyword(tags=["port"])
    def delete_all_ports(self) -> None:
        """Closes and deletes all ports.

        Handy as a suite or test teardown.
        """
        self._current_port_locator = None
        while self._ports:
            _, port = self._ports.popitem()
            port.close()

    @keyword(tags=["port"])
    def open_port(self, port_locator: str | None = None) -> None:
        """Opens a port, the current port by default.

        Does nothing if the port is already open.
        """
        port = self._port(port_locator)
        if not port.is_open:
            port.open()

    @keyword(tags=["port"])
    def close_port(self, port_locator: str | None = None) -> None:
        """Closes a port, the current port by default, without deleting it.

        Does nothing if the port is already closed. Use `Open Port` to reopen it.
        """
        self._port(port_locator).close()

    @keyword(tags=["port", "assertion"])
    def port_should_be_open(self, port_locator: str | None = None) -> None:
        """Fails if the port is closed."""
        if not self._port(port_locator).is_open:
            raise Failure("Port is closed.")

    @keyword(tags=["port", "assertion"])
    def port_should_be_closed(self, port_locator: str | None = None) -> None:
        """Fails if the port is open."""
        if self._port(port_locator).is_open:
            raise Failure("Port is open.")

    @keyword(tags=["port"])
    def switch_port(self, port_locator: str) -> None:
        """Makes ``port_locator`` the current port.

        Fails if the port does not exist.
        """
        if port_locator not in self._ports:
            raise Error("No such port.")
        self._current_port_locator = port_locator

    @keyword(tags=["port", "configuration"])
    def get_port_parameter(self, param_name: str, port_locator: str | None = None) -> Any:
        """Returns the value of one of the `port parameters`.

        | ${baudrate} =    `Get Port Parameter`    baudrate
        """
        if param_name not in PORT_PARAMETER_TYPES:
            raise Error("Wrong parameter name.")
        return getattr(self._port(port_locator), param_name)

    @keyword(tags=["port", "configuration"])
    def set_port_parameter(self, param_name: str, value: Any, port_locator: str | None = None) -> Any:
        """Sets one of the `port parameters` and returns its previous value.

        Changing a parameter of an open port reconfigures it immediately.

        | `Set Port Parameter`    baudrate    115200
        | `Set Port Parameter`    timeout     None
        """
        if param_name not in PORT_PARAMETER_TYPES:
            raise Error("Wrong parameter name.")
        port = self._port(port_locator)
        previous = getattr(port, param_name)
        setattr(port, param_name, _convert_parameters({param_name: value})[param_name])
        return previous

    # ----------------------------------------------------------------------
    # Reading

    @keyword(tags=["read"])
    def read_all_data(self, encoding: str | None = None, port_locator: str | None = None) -> str:
        """Reads and returns all data available in the input buffer.

        Data is decoded with ``encoding``, or the default encoding.
        """
        return self._decode(self._port(port_locator).read_all(), encoding)

    @keyword(tags=["read"])
    def read_all_and_log(
        self, loglevel: str = "DEBUG", encoding: str | None = None, port_locator: str | None = None
    ) -> str:
        """Reads all available data, logs it and returns it.

        Useful to empty the input buffer while keeping a trace of what was
        discarded. ``loglevel`` is ``TRACE``, ``DEBUG``, ``INFO``, ``WARN`` or
        ``ERROR`` (case-insensitive).
        """
        log = LOG_LEVELS.get(loglevel.upper())
        if log is None:
            raise Error("Invalid loglevel.")
        data = self.read_all_data(encoding, port_locator)
        log(data)
        return data

    @keyword(tags=["read", "assertion"])
    def read_data_should_be(
        self, data: str | bytes, encoding: str | None = None, port_locator: str | None = None
    ) -> None:
        """Reads all available data and fails if it differs from ``data``.

        The comparison is made on bytes: ``data`` is encoded with ``encoding``
        (or the default encoding) and compared with the bytes read. The error
        message shows both values in hexadecimal.

        | `Write Data`             AT
        | `Read Data Should Be`    OK    encoding=ascii
        """
        expected = self._encode(data, encoding)
        read = self._port(port_locator).read_all()
        if read != expected:
            read_hex = self._decode(read, DEFAULT_ENCODING)
            expected_hex = self._decode(expected, DEFAULT_ENCODING)
            raise Failure(f"'{read_hex}'(read) != '{expected_hex}'(data)")

    @keyword(tags=["read"])
    def read_until(
        self,
        expected: str | bytes | None = None,
        size: int | None = None,
        encoding: str | None = None,
        port_locator: str | None = None,
        terminator_encoding: str | None = None,
        terminator: str | bytes | None = None,
    ) -> str:
        """Reads until ``expected`` is found, ``size`` bytes are read or the read times out.

        ``expected`` defaults to a line feed. It is encoded with
        ``terminator_encoding``, or the default encoding. With the default
        ``hexlify`` encoding, ``X`` as a terminator is therefore written ``58``.
        ``terminator`` is an alias of ``expected``.

        The data read, terminator included, is decoded with ``encoding``, or
        the default encoding.

        | ${line} =    `Read Until`
        | ${line} =    `Read Until`    0D 0A
        | ${line} =    `Read Until`    OK    terminator_encoding=ascii    encoding=ascii
        """
        if expected is None:
            expected = terminator
        expected = self._encode(expected, terminator_encoding) if expected else LF
        data = self._port(port_locator).read_until(expected=expected, size=size)
        return self._decode(data, encoding)

    @keyword(tags=["read"])
    def read_n_bytes(
        self,
        size: int = 1,
        encoding: str | None = None,
        encoding_mode: str | None = None,
        port_locator: str | None = None,
    ) -> str:
        """Reads up to ``size`` bytes and returns them decoded.

        Fewer bytes are returned if the read times out. ``encoding_mode`` is
        the decoding error handler, ``replace`` by default.
        """
        return self._decode(self._port(port_locator).read(size), encoding, encoding_mode)

    @keyword(tags=["read", "assertion"])
    def port_should_have_unread_bytes(self, port_locator: str | None = None) -> None:
        """Fails if the input buffer is empty."""
        if not self._port(port_locator).in_waiting:
            raise Failure("Port has no in-waiting data.")

    @keyword(tags=["read", "assertion"])
    def port_should_not_have_unread_bytes(self, port_locator: str | None = None) -> None:
        """Fails if the input buffer contains data."""
        if self._port(port_locator).in_waiting:
            raise Failure("Port has in-waiting data.")

    # ----------------------------------------------------------------------
    # Writing

    @keyword(tags=["write"])
    def write_data(
        self,
        data: str | bytes,
        encoding: str | None = None,
        encoding_mode: str | None = None,
        port_locator: str | None = None,
    ) -> None:
        """Writes ``data`` to the port.

        Text is encoded with ``encoding``, or the default encoding.
        ``encoding_mode`` is the encoding error handler, ``strict`` by default.
        ``bytes`` are written as is.

        | `Write Data`    01 02 FF
        | `Write Data`    AT+GMR\\r\\n    encoding=ascii
        """
        data = self._encode(data, encoding, encoding_mode)
        logger.debug(f"Writing {self._decode(data, DEFAULT_ENCODING)}")
        self._port(port_locator).write(data)

    @keyword(tags=["write"])
    def write_file_data(
        self,
        file_or_path: Path | BinaryIO,
        offset: int = 0,
        length: int = -1,
        port_locator: str | None = None,
    ) -> None:
        """Writes the content of a file to the port.

        ``file_or_path`` is a path, absolute or relative to the working
        directory, or a binary file object.

        The file is first moved ``offset`` bytes forward from its current
        position (the start, for a path). Then ``length`` bytes are written,
        or everything up to the end if ``length`` is negative.

        | `Write File Data`    ${CURDIR}/firmware.bin
        | `Write File Data`    ${CURDIR}/firmware.bin    offset=512    length=256
        """
        if isinstance(file_or_path, (str, PathLike)):
            with Path(file_or_path).open("rb") as stream:
                data = self._read_stream(stream, offset, length)
        else:
            data = self._read_stream(file_or_path, offset, length)
        self._port(port_locator).write(data)

    @staticmethod
    def _read_stream(stream: BinaryIO, offset: int, length: int) -> bytes:
        if offset > 0:
            stream.seek(offset, SEEK_CUR)
        return stream.read(length) if length >= 0 else stream.read()

    @keyword(tags=["write", "assertion"])
    def port_should_have_unsent_bytes(self, port_locator: str | None = None) -> None:
        """Fails if the output buffer is empty.

        Fails also on platforms where the output buffer cannot be inspected.
        """
        if not self._port(port_locator).out_waiting:
            raise Failure("Port has no out-waiting data.")

    @keyword(tags=["write", "assertion"])
    def port_should_not_have_unsent_bytes(self, port_locator: str | None = None) -> None:
        """Fails if the output buffer contains data."""
        if self._port(port_locator).out_waiting:
            raise Failure("Port has out-waiting data.")

    # ----------------------------------------------------------------------
    # Buffers

    @keyword(tags=["write"])
    def flush_port(self, port_locator: str | None = None) -> None:
        """Waits until all data in the output buffer has been sent."""
        self._port(port_locator).flush()

    @keyword(tags=["read"])
    def reset_input_buffer(self, port_locator: str | None = None) -> None:
        """Discards all data in the input buffer."""
        self._port(port_locator).reset_input_buffer()

    @keyword(tags=["write"])
    def reset_output_buffer(self, port_locator: str | None = None) -> None:
        """Discards all data in the output buffer."""
        self._port(port_locator).reset_output_buffer()

    @keyword(tags=["write"])
    def send_break(self, duration: float = 0.25, port_locator: str | None = None) -> None:
        """Sends a BREAK condition lasting ``duration`` seconds."""
        self._port(port_locator).send_break(duration)

    # ----------------------------------------------------------------------
    # Modem lines

    @keyword("Set RTS", tags=["modem lines"])
    def set_rts(self, value: bool, port_locator: str | None = None) -> None:
        """Sets the RTS (Request To Send) line.

        ``value`` is a boolean such as ``On``, ``Off``, ``True`` or ``False``.
        """
        self._port(port_locator).rts = _to_bool(value, "value")

    @keyword("Set DTR", tags=["modem lines"])
    def set_dtr(self, value: bool, port_locator: str | None = None) -> None:
        """Sets the DTR (Data Terminal Ready) line.

        ``value`` is a boolean such as ``On``, ``Off``, ``True`` or ``False``.
        """
        self._port(port_locator).dtr = _to_bool(value, "value")

    def _line_should_be(self, line: str, value: bool, port_locator: str | None) -> None:
        expected = _to_bool(value, "value")
        actual = bool(getattr(self._port(port_locator), line))
        if expected != actual:
            raise Failure(f"{line.upper()} should be {_to_on_off(expected)} but {_to_on_off(actual)}.")

    @keyword("RTS Should Be", tags=["modem lines", "assertion"])
    def rts_should_be(self, value: bool, port_locator: str | None = None) -> None:
        """Fails if the RTS line is not ``value`` (``On`` or ``Off``)."""
        self._line_should_be("rts", value, port_locator)

    @keyword("DTR Should Be", tags=["modem lines", "assertion"])
    def dtr_should_be(self, value: bool, port_locator: str | None = None) -> None:
        """Fails if the DTR line is not ``value`` (``On`` or ``Off``)."""
        self._line_should_be("dtr", value, port_locator)

    @keyword("CTS Should Be", tags=["modem lines", "assertion"])
    def cts_should_be(self, value: bool, port_locator: str | None = None) -> None:
        """Fails if the CTS (Clear To Send) line is not ``value`` (``On`` or ``Off``)."""
        self._line_should_be("cts", value, port_locator)

    @keyword("DSR Should Be", tags=["modem lines", "assertion"])
    def dsr_should_be(self, value: bool, port_locator: str | None = None) -> None:
        """Fails if the DSR (Data Set Ready) line is not ``value`` (``On`` or ``Off``)."""
        self._line_should_be("dsr", value, port_locator)

    @keyword("RI Should Be", tags=["modem lines", "assertion"])
    def ri_should_be(self, value: bool, port_locator: str | None = None) -> None:
        """Fails if the RI (Ring Indicator) line is not ``value`` (``On`` or ``Off``)."""
        self._line_should_be("ri", value, port_locator)

    @keyword("CD Should Be", tags=["modem lines", "assertion"])
    def cd_should_be(self, value: bool, port_locator: str | None = None) -> None:
        """Fails if the CD (Carrier Detect) line is not ``value`` (``On`` or ``Off``)."""
        self._line_should_be("cd", value, port_locator)

    @keyword("Get CTS Status", tags=["modem lines"])
    def get_cts_status(self, port_locator: str | None = None) -> bool:
        """Returns the state of the CTS (Clear To Send) line."""
        return self._port(port_locator).cts

    @keyword("Get DSR Status", tags=["modem lines"])
    def get_dsr_status(self, port_locator: str | None = None) -> bool:
        """Returns the state of the DSR (Data Set Ready) line."""
        return self._port(port_locator).dsr

    @keyword("Get RI Status", tags=["modem lines"])
    def get_ri_status(self, port_locator: str | None = None) -> bool:
        """Returns the state of the RI (Ring Indicator) line."""
        return self._port(port_locator).ri

    @keyword("Get CD Status", tags=["modem lines"])
    def get_cd_status(self, port_locator: str | None = None) -> bool:
        """Returns the state of the CD (Carrier Detect) line."""
        return self._port(port_locator).cd

    # ----------------------------------------------------------------------
    # Flow control and RS485

    @keyword(tags=["configuration"])
    def set_input_flow_control(self, enable: bool = True, port_locator: str | None = None) -> None:
        """Manually enables or disables input flow control (XON/XOFF or RTS).

        Only supported by real ports on POSIX systems; fails elsewhere.
        """
        port = self._port(port_locator)
        if not hasattr(port, "set_input_flow_control"):
            raise Error("Input flow control is not supported by this port.")
        port.set_input_flow_control(_to_bool(enable, "enable"))

    @keyword(tags=["configuration"])
    def set_output_flow_control(self, enable: bool = True, port_locator: str | None = None) -> None:
        """Manually enables or disables output flow control (XON/XOFF).

        Only supported by real ports on POSIX systems; fails elsewhere.
        """
        port = self._port(port_locator)
        if not hasattr(port, "set_output_flow_control"):
            raise Error("Output flow control is not supported by this port.")
        port.set_output_flow_control(_to_bool(enable, "enable"))

    @keyword("Set RS485 Mode", tags=["configuration"])
    def set_rs485_mode(
        self,
        port_locator: str | None = None,
        *,
        enabled: bool | None = None,
        rts_level_for_tx: bool | None = None,
        rts_level_for_rx: bool | None = None,
        loopback: bool | None = None,
        delay_before_tx: float | None = None,
        delay_before_rx: float | None = None,
    ) -> None:
        """Enables or disables the RS485 mode of the port.

        Without arguments, RS485 mode is disabled. Giving any of the settings
        below enables it, with the defaults shown for the others:

        | = Setting =          | = Default = |
        | ``rts_level_for_tx`` | True        |
        | ``rts_level_for_rx`` | False       |
        | ``loopback``         | False       |
        | ``delay_before_tx``  | None        |
        | ``delay_before_rx``  | None        |

        ``enabled=True`` enables RS485 mode with all defaults, and
        ``enabled=False`` disables it whatever the other settings.

        | `Set RS485 Mode`    rts_level_for_tx=False    rts_level_for_rx=True
        | `Set RS485 Mode`    enabled=True
        | `Set RS485 Mode`
        """
        settings = {
            name: value
            for name, value in [
                ("rts_level_for_tx", rts_level_for_tx),
                ("rts_level_for_rx", rts_level_for_rx),
                ("loopback", loopback),
                ("delay_before_tx", delay_before_tx),
                ("delay_before_rx", delay_before_rx),
            ]
            if value is not None
        }
        for name in ("rts_level_for_tx", "rts_level_for_rx", "loopback"):
            if name in settings:
                settings[name] = _to_bool(settings[name], name)
        enable = _to_bool(enabled, "enabled") if enabled is not None else bool(settings)
        self._port(port_locator).rs485_mode = RS485Settings(**settings) if enable else None
