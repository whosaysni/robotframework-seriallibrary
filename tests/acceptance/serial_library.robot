*** Settings ***
Documentation    Acceptance tests of SerialLibrary 1.x, run against pySerial's ``loop://`` port.

Library          SerialLibrary

Test Teardown    Delete All Ports


*** Variables ***
${LOOP}         loop://
${LOOP2}        loop://debug
${DEMO_FILE}    ${CURDIR}/demo.dat


*** Test Cases ***
Write And Read Back Hexadecimal Data
    Add Port    ${LOOP}
    Write Data    01 23 AB ff
    ${data} =    Read All Data
    Should Be Equal    ${data}    01 23 AB FF

Write And Read Back Text
    Add Port    ${LOOP}
    Write Data    Bonjour à tous    encoding=utf-8
    Read Data Should Be    Bonjour à tous    encoding=utf-8

Bytes Are Written As Is Whatever The Encoding
    Add Port    ${LOOP}
    ${raw} =    Convert To Bytes    \x01\x02\xff
    Write Data    ${raw}
    Read Data Should Be    01 02 FF
    Write Data    ${raw}
    Read Data Should Be    ${raw}    encoding=ascii

Read Data Should Be Reports Both Values In Hexadecimal
    Add Port    ${LOOP}
    Write Data    FE DC
    Run Keyword And Expect Error    'FE DC'(read) != 'AB'(data)
    ...    Read Data Should Be    AB

Read Until Uses Expected Terminator
    Add Port    ${LOOP}    timeout=0.1
    Write Data    41 0D 0A 42 43 44
    ${line} =    Read Until    0D 0A
    Should Be Equal    ${line}    41 0D 0A
    ${rest} =    Read Until    size=2
    Should Be Equal    ${rest}    42 43

Read Until Keeps Terminator Alias
    Add Port    ${LOOP}    timeout=0.1
    Write Data    OK\r\nNEXT    encoding=ascii
    ${line} =    Read Until    terminator=\r\n    terminator_encoding=ascii    encoding=ascii
    Should Be Equal    ${line}    OK\r\n

Read N Bytes Returns At Most Size Bytes
    Add Port    ${LOOP}    timeout=0.1
    Write Data    01 02 03
    ${data} =    Read N Bytes    2
    Should Be Equal    ${data}    01 02
    ${data} =    Read N Bytes    10
    Should Be Equal    ${data}    03

Read All And Log Returns The Data
    Add Port    ${LOOP}
    Write Data    CA FE
    ${data} =    Read All And Log    loglevel=trace
    Should Be Equal    ${data}    CA FE
    Port Should Not Have Unread Bytes

Boolean Port Parameters Are Converted Properly
    [Documentation]    0.4.x turned the string "False" into True.
    Add Port    ${LOOP}    xonxoff=False    rtscts=off    dsrdtr=yes
    ${xonxoff} =    Get Port Parameter    xonxoff
    ${rtscts} =    Get Port Parameter    rtscts
    ${dsrdtr} =    Get Port Parameter    dsrdtr
    Should Be Equal    ${xonxoff}    ${False}
    Should Be Equal    ${rtscts}    ${False}
    Should Be Equal    ${dsrdtr}    ${True}

Numeric Port Parameters Are Converted
    Add Port    ${LOOP}    baudrate=115200    stopbits=1.5    timeout=None
    ${baudrate} =    Get Port Parameter    baudrate
    ${stopbits} =    Get Port Parameter    stopbits
    ${timeout} =    Get Port Parameter    timeout
    Should Be Equal    ${baudrate}    ${115200}
    Should Be Equal    ${stopbits}    ${1.5}
    Should Be Equal    ${timeout}    ${None}

Unknown Port Parameter Fails
    Run Keyword And Expect Error    Unknown port parameter(s): baud_rate. Valid parameters are: *
    ...    Add Port    ${LOOP}    baud_rate=9600
    Run Keyword And Expect Error    Unknown port parameter(s): *
    ...    Set Default Parameters    parity_bit=E

Invalid Parameter Value Fails
    Run Keyword And Expect Error    *'baudrate'*cannot be converted to integer*
    ...    Add Port    ${LOOP}    baudrate=fast

Set Default Parameters Accepts Named Arguments
    ${previous} =    Set Default Parameters    baudrate=57600    parity=E
    Add Port    ${LOOP}
    ${baudrate} =    Get Port Parameter    baudrate
    ${parity} =    Get Port Parameter    parity
    Should Be Equal    ${baudrate}    ${57600}
    Should Be Equal    ${parity}    E
    Should Be Equal    ${previous}[baudrate]    ${9600}
    [Teardown]    Run Keywords    Reset Default Parameters    AND    Delete All Ports

Set Port Parameter Returns Previous Value
    Add Port    ${LOOP}
    ${previous} =    Set Port Parameter    timeout    0.5
    Should Be Equal    ${previous}    ${1.0}
    ${timeout} =    Get Port Parameter    timeout
    Should Be Equal    ${timeout}    ${0.5}

Unknown Encoding Fails Early
    Run Keyword And Expect Error    Unknown encoding 'klingon'.    Set Encoding    klingon
    ${encoding} =    Get Encoding
    Should Be Equal    ${encoding}    hexlify

Port Can Be Added Closed And Opened Later
    Add Port    ${LOOP}    open=False
    Port Should Be Closed
    Open Port
    Port Should Be Open
    Close Port
    Port Should Be Closed

Current Port Follows Add, Switch And Delete
    Add Port    ${LOOP}
    Add Port    ${LOOP2}
    Current Port Should Be    ${LOOP}
    Switch Port    ${LOOP2}
    Current Port Should Be    ${LOOP2}
    Current Port Should Be Regexp    LOOP://DEB
    Delete Port
    Current Port Should Be    ${LOOP}
    Run Keyword And Expect Error    No such port.    Switch Port    ${LOOP2}

Keywords Accept An Explicit Port Locator
    Add Port    ${LOOP}
    Add Port    ${LOOP2}
    Write Data    11    port_locator=${LOOP2}
    Port Should Not Have Unread Bytes
    Port Should Have Unread Bytes    ${LOOP2}
    Read Data Should Be    11    port_locator=${LOOP2}

Using A Missing Port Fails
    Run Keyword And Expect Error    No such port.    Write Data    00

Modem Lines Accept On/Off And Booleans
    Add Port    ${LOOP}
    Set RTS    On
    RTS Should Be    ${True}
    CTS Should Be    on
    Set DTR    off
    DTR Should Be    Off
    DSR Should Be    Off
    Run Keyword And Expect Error    DTR should be On but Off.    DTR Should Be    On

Invalid Boolean Fails Instead Of Being Treated As True
    Add Port    ${LOOP}
    Run Keyword And Expect Error    Argument 'value' got value 'maybe' that cannot be converted to a boolean.
    ...    Set RTS    maybe

Line Status Keywords Return Booleans
    Add Port    ${LOOP}
    ${cts} =    Get CTS Status
    ${ri} =    Get RI Status
    Should Be Equal    ${cts}    ${True}
    Should Be Equal    ${ri}    ${False}

RS485 Mode Can Be Enabled And Disabled
    ${port} =    Add Port    ${LOOP}
    Set RS485 Mode    rts_level_for_tx=False    delay_before_rx=0.01
    Should Be Equal    ${port.rs485_mode.rts_level_for_tx}    ${False}
    Should Be Equal    ${port.rs485_mode.rts_level_for_rx}    ${False}
    Should Be Equal    ${port.rs485_mode.delay_before_rx}    ${0.01}
    Set RS485 Mode    enabled=True
    Should Be Equal    ${port.rs485_mode.rts_level_for_tx}    ${True}
    Set RS485 Mode
    Should Be Equal    ${port.rs485_mode}    ${None}

Flow Control Is Reported As Unsupported On URL Ports
    Add Port    ${LOOP}
    Run Keyword And Expect Error    Input flow control is not supported by this port.
    ...    Set Input Flow Control    True

Write File Data Writes A Slice Of A File
    Add Port    ${LOOP}
    Write File Data    ${DEMO_FILE}    offset=2    length=3
    Read Data Should Be    02 03 04

Write File Data Accepts An Open File
    Add Port    ${LOOP}
    ${file} =    Evaluate    open($DEMO_FILE, 'rb')
    TRY
        Write File Data    ${file}    length=2
        Write File Data    ${file}    offset=1    length=2
    FINALLY
        Call Method    ${file}    close
    END
    Read Data Should Be    00 01 03 04
