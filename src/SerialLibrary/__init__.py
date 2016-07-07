import codecs
import re
from collections import OrderedDict
from serial import Serial, SerialBase, serial_for_url
from serial.serialutil import LF
from serial.tools.list_ports import comports, grep
from serial.tools import hexlify_codec

from robot.api import logger
from robot.utils import asserts, is_truthy, is_string
from robot.utils.encoding import system_encode, system_decode
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


class SerialLibrary:
    """Serial Library."""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'
    ROBOT_LIBRARY_VERSION = __version__
    
    def __init__(self, port_locator=None, encoding='hexlify', **kwargs):
        """\
        SerialLibrary
        ==============

        SerialLibrary can be imported with various arguments.

        Those all arguments correspond to parameters of Serial' constructor.
        If `port_locator` is given the library instance attempt to add the port
        as current port.
        `encoding` specifies default encoding to interpret bytes/string between
        serial device I/O and keyword argument/return values.

        Default Parameters
        -------------------
        
        Default parameter values except timeouts are set as same as SerialBase.
        Default value or timeout and writer_timeout are set to 0.1.

        """
        args = [port_locator]
        self._encoding = encoding
        self._ports = OrderedDict()
        self._defaults = dict(DEFAULT_SETTINGS)
        self.set_default_parameters(kwargs)
        self._current_port_locator = None
        if port_locator is not None:
            self.add_port(port_locator)
            self._current_port_str = port_locator

    def _encode(self, ustring, encoding=None):
        """
        Encode (unicode) string into raw bytes.

        If encoding is not specified, instance's default encoding will be used.
        """
        return ustring.encode(encoding or self._encoding, 'ignore')

    def _decode(self, bstring, encoding=None):
        """
        Decode raw bytes to (unicode) string.
        """
        return bstring.decode(encoding or self._encoding, 'replace')

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
        asserts.assert_true(len(found)>0, 'Matching port does not exist.')
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
        except (AttributeError, ValueError) as exc:
            port = Serial(port_locator, **serial_kw)
        asserts.assert_not_none(port, 'Port initialization failed.')
        self._ports[port_locator] = port
        if port.is_open and is_truthy(open) == False:
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
        self._port(port_locator).reset_input_buffer(duration)

    def reset_output_buffer(self, port_locator=None):
        """
        Clears outout buffer.

        All data in the port's output buffer will be descarded.
        Fails if the port is closed.
        """
        self._port(port_locator).reset_outpur_buffer(duration)

    def send_break(self, duration=0.25, port_locator=None):
        """
        Sends BREAK to port.

        The semantics of duration is same as pySerial's send_break.
        """
        self._port(port_locator).send_break(duration)

    def get_cts_status(self, port_locator=None):
        """
        Returns CTS (Clear To Send) status.
        """
        return self._port(port_locator).cts()

    def get_dsr_status(self, port_locator=None):
        """
        Returns DSR (Data Set Ready) status.
        """
        return self._port(port_locator).rsr()

    def get_ri_status(self, port_locator=None):
        """
        Returns RI (Ring Indicator) status.
        """
        return self._port(port_locator).ri()

    def get_cd_status(self, port_locator=None):
        """
        Returns CD (Carrier Detect) status.
        """
        return self._port(port_locator).cd()

    def cts_should_be_on(self, port_locator=None):
        """
        Fails if CTS is OFF.
        """
        asserts.assert_true(
            self.get_cts_status(port_locator),
            'CTS is OFF.')

    def cts_should_be_off(self, port_locator=None):
        """
        Fails if CTS is ON.
        """
        asserts.assert_false(
            self.get_cts_status(port_locator),
            'CTS is ON.')

    def dsr_should_be_on(self, port_locator=None):
        """
        Fails if DSR is OFF.
        """
        asserts.assert_true(
            self.get_dsr_status(port_locator),
            'DSR is OFF.')

    def dsr_should_be_off(self, port_locator=None):
        """
        Fails if DSR is OFF.
        """
        asserts.assert_false(
            self.get_dsr_status(port_locator),
            'DSR is OFF.')

    def ri_should_be_on(self, port_locator=None):
        """
        Fails if RI is OFF.
        """
        asserts.assert_true(
            self.get_ri_status(port_locator),
            'RI is OFF.')

    def ri_should_be_off(self, port_locator=None):
        """
        Fails if RI is ON.
        """
        asserts.assert_false(
            self.get_ri_status(port_locator),
            'RI is ON.')

    def cd_should_be_on(self, port_locator=None):
        """
        Fails if CD is OFF.
        """
        asserts.assert_true(
            self.get_cd_status(port_locator),
            'CD is OFF.')

    def cd_should_be_off(self, port_locator=None):
        """
        Fails if CD is ON.
        """
        asserts.assert_false(
            self.get_cd_status(port_locator),
            'CD is ON.')

    def set_input_flow_control(self, enable=True, port_locator=None):
        """
        Sets input flow control status on the port.

        Fails if platforms that does not support the feature.
        """
        self._port(port_locator).set_input_flow_control(is_truthy(enable))
      
    def set_output_flow_control(self, enable=True, port_locator=None):
        """
        Sets input flow control status on the port.

        Fails if the platform that does not support the feature.
        """
        self._port(port_locator).set_output_flow_control(is_truthy(enable))

    def set_rs485_mode(self, status, port_locator=None):
        """
        Sets RS485 mode on the port.

        Fails if the platform that does not support the feature.
        """
        self._port(port_locator).rs485_mode = status
