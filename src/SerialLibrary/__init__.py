import codecs
import re
from collections import OrderedDict
from os import SEEK_CUR
from sys import platform
if platform == 'win32':
    from ntpath import abspath, isabs, join
else:
    from os.path import abspath, isabs, join

from serial import Serial, SerialBase, serial_for_url
from serial.serialutil import LF
from serial.tools.list_ports import comports, grep
from serial.tools import hexlify_codec

from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn
from robot.utils import asserts, is_truthy, is_string
from robot.utils.unic import unic

from version import VERSION as __version__



# add hexlify to codecs
def hexlify_decode_plus(data, errors='strict'):
    udata, length = hexlify_codec.hex_decode(data, errors)
    return (udata.rstrip(), length)

hexlify_codec_plus = codecs.CodecInfo(
    name='hexlify',
    encode=hexlify_codec.hex_encode,
    decode=hexlify_decode_plus,
    incrementalencoder=hexlify_codec.IncrementalEncoder,
    incrementaldecoder=hexlify_codec.IncrementalDecoder,
    streamwriter=hexlify_codec.StreamWriter,
    streamreader=hexlify_codec.StreamReader)

codecs.register(lambda c: hexlify_codec_plus if c == 'hexlify' else None)

DEFAULT_SETTINGS = SerialBase(
    timeout=1.0, write_timeout=1.0, inter_byte_timeout=0.0).get_settings()


def is_truthy_on_off(item):
    if is_string(item):
        item = item.strip()
        if item.isdigit():
            return bool(int(item))
        return item.strip().upper() not in ['FALSE', 'NO', '0', 'OFF', '']
    return bool(item)


def to_on_off(value):
    return 'On' if bool(value) is True else 'Off'


class SerialLibrary:
    """Robot Framework test library for manipulating serial ports

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

    """

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'
    ROBOT_LIBRARY_VERSION = __version__

    LOGGER_MAP = dict(INFO=logger.info, DEBUG=logger.debug, WARN=logger.warn)

    def __init__(self, port_locator=None, encoding='hexlify', **kwargs):
        """
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

        """
        self._encoding = encoding
        self._ports = OrderedDict()
        self._defaults = dict(DEFAULT_SETTINGS)
        self.set_default_parameters(kwargs)
        self._current_port_locator = None
        if port_locator is not None:
            self.add_port(port_locator)
            self._current_port_str = port_locator

    def _encode(self, ustring, encoding=None, encoding_mode='strict'):
        """
        Encode (unicode) string into raw bytes.

        If encoding is not specified, instance's default encoding will be used.
        """
        return ustring.encode(encoding or self._encoding, encoding_mode)

    def _decode(self, bstring, encoding=None, encoding_mode='replace'):
        """
        Decode raw bytes to (unicode) string.
        """
        return bstring.decode(encoding or self._encoding, encoding_mode)

    def _port(self, port_locator=None, fail=True):
        """
        Lookup port by name.

        If port_locator is None or string '_', current port
        is returned.
        If specified port is not found, exception is raised
        when fail is True, otherwise None is returned silently.
        """
        if port_locator in [None, '_']:
            port_locator = self._current_port_locator
        port = self._ports.get(port_locator, None)
        if port is None and is_truthy(fail) is True:
            asserts.fail('No such port.')
        return port

    def get_encoding(self):
        """
        Returns default encoding for the library instance.
        """
        return self._encoding

    def set_encoding(self, encoding=None):
        """
        Sets default encoding for the library instance.

        Returns previous encoding.
        If encoding is set to None, just returns current encoding.
        """
        prev_encoding = self._encoding
        if encoding:
            self._encoding = encoding
        return prev_encoding

    def list_com_ports(self):
        """
        Returns list of com ports found on the system.

        This is thin-wrapper of serial.tools.list_ports.
        Returned list consists of possible ListPortInfo instances.
        You may access attributes of ListPortInfo by extended variable
        syntax, e.g.::

            @{ports} =   List Ports
            Log  ${ports[0].device}
        """
        return comports()

    def list_com_port_names(self):
        """
        Returns list of device names for com ports found on the system.

        Items are sorted in dictionary order.
        """
        return sorted(port_info.device for port_info in self.list_com_ports())

    def com_port_should_exist_regexp(self, regexp):
        """
        Fails if com port matching given pattern is not found on the system.

        This keyword uses serial.tools.list_ports.grep internally thus
        port name, description and hardware ID are searched.

        Returns list of com ports matching the pattern, if exists.
        """
        found = list(grep(regexp))
        asserts.assert_true(len(found) > 0, 'Matching port does not exist.')
        return found

    def set_default_parameters(self, params):
        """
        Updates default parameters with given dictionary.

        Argument `params` should be a dictionary variable.
        Only supported parameters are taken into account,
        while others are ignored silently.
        Values can be in any types and are converted into
        appropreate type.
        """
        prev_value = OrderedDict(self._defaults)
        for key, value in params.items():
            if key in self._defaults:
                value_type = type(self._defaults.get(key))
                self._defaults[key] = value_type(value)
        return prev_value

    def reset_default_parameters(self):
        """
        Resets default parameters to those defined in serial.SerialBase.

        This keyword does not directly affect those exisitng ports added
        so far.
        """
        self._defaults = dict(DEFAULT_SETTINGS)

    def get_current_port_locator(self):
        """
        Returns port locator of current port.
        If no port is associated to the current port (implies no port
        in the library instance), None is returned.
        """
        return self._current_port_locator

    def current_port_should_be(self, port_locator):
        """
        Fails if given port locator does not match current port locator.
        """
        if port_locator not in [self._current_port_locator, '_']:
            asserts.fail('Port does not match.')

    def current_port_should_be_regexp(self, port_locator_regexp):
        """
        Fails if given regexp does not match current port locator.

        If current port is None, it will only match to empty sring.
        Matching is case-insensitive.
        """
        current_port_locator = self._current_port_locator
        if current_port_locator is None:
            current_port_locator = ''
        regexp = re.compile(port_locator_regexp, re.I)
        asserts.assert_not_none(
            regexp.match(current_port_locator),
            'Port does not match.', values=False)

    def add_port(self, port_locator, open=True, make_current=False, **kwargs):
        """
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
        """
        if port_locator in [None, '', '_']:
            asserts.fail('Invalid port locator.')
        elif port_locator in self._ports:
            asserts.fail('Port already exists.')
        serial_kw = dict(
            (k, type(v)(kwargs.get(k, v)))
            for k, v in self._defaults.items())
        # try url first, then port name
        try:
            port = serial_for_url(port_locator, **serial_kw)
        except (AttributeError, ValueError):
            port = Serial(port_locator, **serial_kw)
        asserts.assert_not_none(port, 'Port initialization failed.')
        self._ports[port_locator] = port
        if port.is_open and (is_truthy(open) is False):
            port.close()
        if self._current_port_locator is None or make_current:
            self._current_port_locator = port_locator
        return port

    def delete_port(self, port_locator=None):
        """
        Deletes specified port.

        Port is closed if it is opened.
        By default, current port is deleted and most recently added
        ports is selected as new current port. Deleting last port
        in the library instance makes current port set to None.
        Fails if specified port is not found or attempt to delete
        current port if it is set to None.
        """
        if port_locator is None:
            port_locator = self._current_port_locator
        # fails if invalid port locator.
        if port_locator not in self._ports:
            asserts.fail('Invalid port locator.')
        port = self._ports.pop(port_locator)
        if port.is_open:
            port.close()
        # if the deleted port is current port, most recent port
        # left in the instacne will be current port
        if port_locator == self._current_port_locator:
            self._current_port_locator = None
            if self._ports.keys():
                self._current_port_locator = self._ports.keys()[-1]
        del port

    def delete_all_ports(self):
        """
        Deletes all ports maintained in the library instance.

        Opened ports are closed before deletion.
        """
        self._current_port_locator = None
        while self._ports:
            locator, port = self._ports.popitem()
            if port.is_open:
                port.close()
                del port

    def open_port(self, port_locator=None):
        """
        Opens specified port.

        If port_locator is ommitted, current port is opened.
        If port is opened already, this keyword does nothing.
        Fails if specified port is not found.
        """
        port = self._port(port_locator)
        if not port.is_open:
            port.open()

    def close_port(self, port_locator=None):
        """
        Closes specified port.

        Closes current or specified port.
        Current port is closed if port_locator is ommitted.
        This keyword does nothing if port is not opened.
        Fails if specified port is not found.
        """
        port = self._port(port_locator)
        if port.is_open:
            port.close()

    def port_should_be_open(self, port_locator=None):
        """
        Fails if specified port is closed.
        """
        asserts.assert_true(
            self._port(port_locator).is_open,
            'Port is closed.'
        )

    def port_should_be_closed(self, port_locator=None):
        """
        Fails if specified port is open.
        """
        asserts.assert_false(
            self._port(port_locator).is_open,
            'Port is open.'
        )

    def switch_port(self, port_locator):
        """
        Make specified port as current port.

        Fails if specified port is not added in the library
        instance.
        """
        if port_locator not in self._ports:
            asserts.fail('No such port.')
        self._current_port_locator = port_locator

    def get_port_parameter(self, param_name, port_locator=None):
        """
        Returns specified parameter of the port.

        By default, current port is inspected.
        Available parameters are those can be set at library import
        or Add Port keyword: baudrate, bytesize, parity, stopbits,
        timeout, xonxoff, rtscts, write_timeout, dsrdtr and
        inter_byte_timeout.

        Fails on wrong param_name or port_locator.
        """
        if param_name not in self._defaults:
            asserts.fail('Wrong parameter name.')
        port = self._port(port_locator)
        return getattr(port, param_name)

    def set_port_parameter(self, param_name, value, port_locator=None):
        """
        Sets port parameter.

        By default, current port is affected.
        Available parameters are same as Get Port Parameter keyword.
        For most parameter, changing it on opened port will cause
        port reconfiguration.
        Fails on wrong param_name or port_locator.
        Returns previous value.
        """
        if param_name not in self._defaults:
            asserts.fail('Wrong parameter name.')
        port = self._port(port_locator, fail=True)
        prev_value = getattr(port, param_name)
        param_type = type(self._defaults.get(param_name))
        setattr(port, param_name, param_type(value))
        return prev_value

    def read_all_data(self, encoding=None, port_locator=None):
        """
        Read all available data from the port's incoming buffer.

        If `encoding` is not given, default encoding is used.
        """
        return self._decode(self._port(port_locator).read_all(), encoding)

    def read_all_and_log(self, loglevel='debug', encoding=None, port_locator=None):
        """
        Read all available data and write it to log.

        This is useful if you want to discard bytes in read queue, but just want
        to log it.
        Loglevel can be 'info', 'debug' or 'warn' (case insensitive).
        Any other level causes error.
        If `encoding` is not given, default encoding is used.
        """
        loglevel = loglevel.upper()
        logger_func = self.LOGGER_MAP.get(loglevel, None)
        if logger_func is None:
            raise asserts.fail('Invalid loglevel.')
        logger_func(self.read_all_data(encoding, port_locator))

    def read_data_should_be(
            self, data, encoding=None, port_locator=None):
        """
        Fails if all read bytes from the port not equals to specifed data.

        This keyword compares values in byte space; data is encoded to bytes
        then compared to bytes read from the port.
        """
        bdata = self._encode(data, encoding)
        bread = self._port(port_locator).read_all()
        if bread != bdata:
            hex_bread = self._decode(bread, 'hexlify')
            hex_bdata = self._decode(bdata, 'hexlify')
            msg = "'%s'(read) != '%s'(data)" % (hex_bread, hex_bdata)
            asserts.fail(msg)

    def read_until(self, terminator=LF, size=None, encoding=None, port_locator=None):
        """
        Read until a termination sequence is found, size exceeded or timeout.

        If `encoding` is not given, default encoding is used.
        Note that encoding affects terminator too, so if you want to use
        character 'X' as terminator and encoding=hexlify (default), you should
        call this keyword as Read Until terminator=58.
        """
        if size is not None:
            size = float(size)
        if terminator != LF:
            terminator = self._encode(terminator)
        return self._decode(
            self._port(port_locator).read_until(terminator=terminator, size=size),
            encoding)

    def port_should_have_unread_bytes(self, port_locator=None):
        """
        Fails if port input buffer does not contain data.
        Fails if the port is closed.
        """
        asserts.assert_true(
            self._port(port_locator).in_waiting,
            'Port has no in-waiting data.')

    def port_should_not_have_unread_bytes(self, port_locator=None):
        """
        Fails if port input buffer contains data.
        Fails if the port is closed.
        """
        asserts.assert_false(
            self._port(port_locator).in_waiting,
            'Port has in-waiting data.')

    def port_should_have_unsent_bytes(self, port_locator=None):
        """
        Fails if port output buffer does not contain data.
        Also fails if the port is closed.
        Not that if platform does not support out_waiting, this
        keyword will fail.
        """
        asserts.assert_true(
            self._port(port_locator).out_waiting,
            'Port has no out-waiting data.')

    def port_should_not_have_unsent_bytes(self, port_locator=None):
        """
        Fails if port output buffer contains data.
        Fails if the port is closed.
        """
        asserts.assert_false(
            self._port(port_locator).out_waiting,
            'Port has out-waiting data.')

    def read_n_bytes(self, size=1, encoding=None, port_locator=None):
        """
        Reads specified number of bytes from the port.

        Note that if no timeout is specified this keyword may block
        until the requested number of bytes is read.
        Returns (encoded) read data.
        """
        if is_string(size):
            size = int(size)
        return self._decode(self._port(port_locator).read(size))

    def write_data(self, data, encoding=None, port_locator=None):
        """
        Writes data into the port.

        If data is a Python's byte string object, it will be written
        to the port intact. If data is unicode string, it will be
        encoded with given encoding before writing. Otherwise,
        data is converted to unicode and processed same as unicode string.
        """
        if not isinstance(data, (unicode, bytes)):
            data = unic(data)
        if isinstance(data, unicode):
            data = self._encode(data, encoding)
        self._port(port_locator).write(data)

    def flush_port(self, port_locator=None):
        """
        Flush port so that all waiting data is processed.
        """
        self._port(port_locator).flush()

    def reset_input_buffer(self, port_locator=None):
        """
        Clears input buffer.

        All data in the port's input buffer will be descarded.
        Fails if the port is closed.
        """
        self._port(port_locator).reset_input_buffer()

    def reset_output_buffer(self, port_locator=None):
        """
        Clears outout buffer.

        All data in the port's output buffer will be descarded.
        Fails if the port is closed.
        """
        self._port(port_locator).reset_output_buffer()

    def send_break(self, duration=0.25, port_locator=None):
        """
        Sends BREAK to port.

        The semantics of duration is same as pySerial's send_break.
        """
        self._port(port_locator).send_break(float(duration))

    def set_rts(self, value, port_locator=None):
        """
        Sets RTS (Request To Send) status.
        """
        self._port(port_locator).rts = is_truthy_on_off(value)
        value = 1 if is_truthy_on_off(value) else 0
        self._port(port_locator).rts = value

    def set_dtr(self, value, port_locator=None):
        """
        Sets DTR (Data Terminal Ready) status.
        """
        self._port(port_locator).dtr = is_truthy_on_off(value)

    def _attr_should_be(self, attr, value, port_locator):
        """
        Fails specified attribute does not have expected value.
        """
        value = 1 if is_truthy_on_off(value) else 0
        status = getattr(self._port(port_locator), attr)
        if value != status:
            msg = '%s should be %s but %s.' % (
                attr.upper(), to_on_off(value), to_on_off(status))
            asserts.fail(msg)

    def rts_should_be(self, value, port_locator=None):
        """
        Fails if RTS status is not specified value.
        """
        self._attr_should_be('rts', value, port_locator)

    def dtr_should_be(self, value, port_locator=None):
        """
        Fails if DTR status is not specified value.
        """
        self._attr_should_be('dtr', value, port_locator)

    def get_cts_status(self, port_locator=None):
        """
        Returns CTS (Clear To Send) status.
        """
        return self._port(port_locator).cts

    def get_dsr_status(self, port_locator=None):
        """
        Returns DSR (Data Set Ready) status.
        """
        return self._port(port_locator).dsr

    def get_ri_status(self, port_locator=None):
        """
        Returns RI (Ring Indicator) status.
        """
        return self._port(port_locator).ri

    def get_cd_status(self, port_locator=None):
        """
        Returns CD (Carrier Detect) status.
        """
        return self._port(port_locator).cd

    def cts_should_be(self, value, port_locator=None):
        """
        Fails if CTS is not expected status.
        """
        self._attr_should_be('cts', value, port_locator)

    def dsr_should_be(self, value, port_locator=None):
        """
        Fails if DSR is not expected status.
        """
        self._attr_should_be('dsr', value, port_locator)

    def ri_should_be(self, value, port_locator=None):
        """
        Fails if RI is not expected status.
        """
        self._attr_should_be('ri', value, port_locator)

    def cd_should_be(self, value, port_locator=None):
        """
        Fails if CD is not expected status.
        """
        self._attr_should_be('cd', value, port_locator)

    def set_input_flow_control(self, enable=True, port_locator=None):
        """
        [Unsupported] Sets input flow control status on the port.

        Fails if platforms that does not support the feature.
        """
        self._port(port_locator).set_input_flow_control(is_truthy_on_off(enable))

    def set_output_flow_control(self, enable=True, port_locator=None):
        """
        [Unsupported] Sets input flow control status on the port.

        Fails if the platform that does not support the feature.
        """
        self._port(port_locator).set_output_flow_control(is_truthy_on_off(enable))

    def set_rs485_mode(self, status, port_locator=None):
        """
        Sets RS485 mode on the port.

        Fails if the platform that does not support the feature.
        """
        self._port(port_locator).rs485_mode = is_truthy_on_off(status)

    def write_file_data(self, file_or_path, offset=0, length=-1, port_locator=None):
        """
        Writes content of file into the port.

        File can be specified by file path or opened file-like object.
        In former case, path should be absolute or relative to current directory.
        In latter case, file (or file-like object should support read with
        specified length.
        If offset is non-zero, file is seek()-ed from *current position* 
        (not the beginning of the file). Note that your the file object should
        support seek() method  with SEEK_CUR.
        If length is negative, all content after current input file position is read.
        Otherwise, number of specified bytes are read from the input file.

        Fails if specified file could not be opened.
        """
        infile = file_or_path
        if is_string(file_or_path):
            infile = open(file_or_path, 'rb')
        if is_string(offset):
            offset = int(offset)
        if is_string(length):
            length = int(length)
        if offset > 0:
            infile.seek(offset, SEEK_CUR)
        read_bytes = infile.read(length) if length >= 0 else infile.read()
        self._port(port_locator).write(read_bytes)
