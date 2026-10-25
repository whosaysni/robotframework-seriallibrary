import io
import json

import pytest
from robot.api import Error, Failure
from robot.libdoc import LibraryDocumentation
from serial import SerialException

from SerialLibrary import SerialLibrary, __version__

LOOP = "loop://"
LOOP2 = "loop://debug"


@pytest.fixture
def lib():
    library = SerialLibrary()
    yield library
    library.delete_all_ports()


def test_hexlify_codec_round_trip():
    assert "01 23 ab".encode("hexlify") == b"\x01\x23\xab"
    assert b"\x01\x23\xab".decode("hexlify") == "01 23 AB"


def test_import_adds_current_port_with_defaults():
    library = SerialLibrary(LOOP, encoding="ascii", baudrate="115200", xonxoff="False")
    try:
        assert library.get_current_port_locator() == LOOP
        assert library.get_encoding() == "ascii"
        assert library.get_port_parameter("baudrate") == 115200
        assert library.get_port_parameter("xonxoff") is False
    finally:
        library.delete_all_ports()


def test_import_rejects_unknown_encoding():
    with pytest.raises(Error, match="Unknown encoding 'nope'"):
        SerialLibrary(encoding="nope")


def test_failed_open_does_not_register_port(lib):
    with pytest.raises(SerialException):
        lib.add_port("/dev/does-not-exist")
    assert lib.get_current_port_locator() is None
    with pytest.raises(Error, match="No such port"):
        lib.port_should_be_open("/dev/does-not-exist")


def test_add_port_closed_never_opens(lib):
    port = lib.add_port(LOOP, open=False)
    assert not port.is_open


def test_deleting_current_port_selects_most_recent(lib):
    for locator in (LOOP, LOOP2, "loop://?logging=info"):
        lib.add_port(locator)
    lib.switch_port(LOOP)
    lib.delete_port()
    assert lib.get_current_port_locator() == "loop://?logging=info"


def test_listener_closes_ports_at_end(lib):
    port = lib.add_port(LOOP)
    lib.ROBOT_LIBRARY_LISTENER.close()
    assert not port.is_open
    assert lib.get_current_port_locator() is None


def test_write_file_data_accepts_str_path_and_stream(lib, tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(bytes(range(10)))
    lib.add_port(LOOP, timeout=0.1)
    lib.write_file_data(str(path), offset=8)
    lib.write_file_data(io.BytesIO(b"\xaa\xbb\xcc"), offset=1, length=1)
    assert lib.read_all_data() == "08 09 BB"


def test_read_data_should_be_failure_message(lib):
    lib.add_port(LOOP)
    lib.write_data("AB")
    with pytest.raises(Failure, match=r"'AB'\(read\) != 'CD'\(data\)"):
        lib.read_data_should_be("CD")


def test_read_until_defaults_to_line_feed(lib):
    lib.add_port(LOOP, timeout=0.1)
    lib.write_data("line1\nline2", encoding="ascii")
    assert lib.read_until(encoding="ascii") == "line1\n"


def test_set_default_parameters_merges_dict_and_kwargs(lib):
    previous = lib.set_default_parameters({"baudrate": "19200"}, timeout="2")
    assert previous["baudrate"] == 9600
    port = lib.add_port(LOOP)
    assert (port.baudrate, port.timeout) == (19200, 2.0)


def test_rs485_enabled_false_wins(lib):
    port = lib.add_port(LOOP)
    lib.set_rs485_mode(enabled=False, loopback=True)
    assert port.rs485_mode is None


def test_libdoc_metadata():
    doc = LibraryDocumentation("SerialLibrary")
    names = {kw.name for kw in doc.keywords}
    assert doc.version == __version__
    assert doc.scope == "GLOBAL"
    assert {"Add Port", "Set RTS", "Get CTS Status", "Set RS485 Mode", "List COM Ports"} <= names
    assert not any(name.startswith("_") for name in names)
    assert all(kw.doc for kw in doc.keywords), "every keyword must be documented"
    add_port = next(kw for kw in doc.keywords if kw.name == "Add Port")
    assert json.loads(doc.to_json())["keywords"]
    assert [arg.name for arg in add_port.args] == ["port_locator", "open", "make_current", "kwargs"]
