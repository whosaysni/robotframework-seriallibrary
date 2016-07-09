*** Settings
Library    Collections
Library    SerialLibrary

*** Test Cases

Default port is None
    ${ins} =    Get Library Instance    SerialLibrary
    Should Be Equal    ${ins._current_port_locator}   ${NONE}
    
Default encoding is hexlify
    ${ins} =    Get Library Instance    SerialLibrary
    Should Be Equal    ${ins._encoding}   hexlify
    
Default parameters are set as same as a vanilla SerialBase instance
    [Template]    Parameter Matches to SerialBase attributes
    baudrate
    bytesize
    parity
    stopbits
    timeout
    write_timeout
    xonxoff
    rtscts
    dsrdtr
    inter_byte_timeout

Get Encoding should return current encoding
    ${ins} =    Get Library Instance    SerialLibrary
    ${encoding} =    Get Encoding
    Should Be Equal    ${ins._encoding}    ${encoding}
    Should Be Equal    ${encoding}    hexlify

Set Encoding should change current encoding, returning previous value
    ${ins} =    Get Library Instance    SerialLibrary
    ${encoding} =    Set Encoding    hex
    Should Be Equal    ${encoding}    hexlify
    Should Be Equal    ${ins._encoding}    hex
    [TearDown]    Set Encoding    hexlify

List Com Ports should return list of ports
    [Tags]    Bluetooth-osx
    @{ports} =   List Com Ports
    Should Not Be Empty   ${ports}

Com Port Should Exist Regexp should find some port
    [Tags]    Bluetooth-osx
    @{ports} =   Com Port Should Exist Regexp    .
    Should Not Be Empty   ${ports}
    Run Keyword And Expect Error   Matching port does not exist.
    ...    Com Port Should Exist Regexp    __NONEXISTENT__

Set Default Parameters changes internal default dictionary
    ${ins} =    Get Library Instance    SerialLibrary
    Should Be Equal As Integers   ${ins._defaults['baudrate']}    9600
    &{params} =    Create Dictionary    baudrate=128000
    &{prev} =    Set Default Parameters    ${params}
    Should Be Type Of   ${ins._defaults['baudrate']}    int
    Should Be Equal As Integers   ${ins._defaults['baudrate']}    128000
    Reset Default Parameters
    Should Be Equal As Integers   ${ins._defaults['baudrate']}    9600

Get Current Port Locator returns current port locator
    ${ins} =    Get Library Instance    SerialLibrary
    ${locator} =   Get Current Port Locator
    Should Be Equal    ${ins._current_port_locator}    ${locator}

Current Port Should Be confirms current port locator
    ${ins} =    Get Library Instance    SerialLibrary
    ${locator} =   Get Current Port Locator
    Current Port Should Be    ${locator}
    Run Keyword And Expect Error   Port does not match.
    ...   Current Port Should Be    SOMETHING_WRONG

Current Port Should Be Regexp confirms current port locator by regular expression
    ${ins} =    Get Library Instance    SerialLibrary
    # At this point current port is set to None, thus only '' should match
    Current Port Should Be Regexp    ${EMPTY}
    Run Keyword And Expect Error    Port does not match.
    ...    Current Port Should Be Regexp    THIS_NEVER_MATCHES
    Add Port    loop://
    Current Port Should Be Regexp    \\w+://
    Current Port Should Be Regexp    lo..://
    Current Port Should Be Regexp    lo{1,2}p:/{2}
    Run Keyword And Expect Error   Port does not match.
    ...    Current Port Should Be    THIS_NEVER_MATCHES
    [Teardown]    Call Method    ${ins}    delete_port

If no current port is assigned, Add Port will add one and make it current
    ${ins} =    Get Library Instance    SerialLibrary
    Should Be Equal    ${ins._current_port_locator}   ${NONE}
    Add Port    loop://
    Should Be Equal    ${ins._current_port_locator}   loop://
    Port should be open
    [Teardown]    Call Method    ${ins}    delete_port

Add Port fails if invalid or duplicaed port is tried
    ${ins} =    Get Library Instance    SerialLibrary
    Run Keyword And Expect Error    Invalid port locator.
    ...    Add Port    ${NONE}
    Run Keyword And Expect Error    Invalid port locator.
    ...    Add Port    ${EMPTY}
    Run Keyword And Expect Error    Invalid port locator.
    ...    Add Port    _
    Add Port    loop://
    Run Keyword And Expect Error    Port already exists.
    ...    Add Port    loop://
    [Teardown]    Call Method    ${ins}    delete_port

Delete Port deletes specified port (or current port)
    ${ins} =    Get Library Instance    SerialLibrary
    Add Port   loop://
    Should Be Equal    ${ins._current_port_locator}   loop://
    Delete Port   loop://
    Should Be Equal    ${ins._current_port_locator}   ${NONE}
    Add Port   loop://
    Should Be Equal    ${ins._current_port_locator}   loop://
    Delete Port
    Should Be Equal    ${ins._current_port_locator}   ${NONE}
    
Delete All Ports deletes all ports added so far
    ${ins} =    Get Library Instance    SerialLibrary
    Add Port   loop://
    Add Port   loop://debug
    ${n_ports} =    Get Length    ${ins._ports}
    Should Be Equal As Strings    ${n_ports}    2
    Delete All Ports
    Should Be Empty    ${ins._ports}

Open Port should open closed port
    ${ins} =    Get Library Instance    SerialLibrary
    Add Port    loop://    open=False
    Should Not Be True    ${ins._ports['loop://'].is_open}
    Open Port    
    Should Be True    ${ins._ports['loop://'].is_open}
    [Teardown]    Delete All Ports

Port Should Be Open/Closed should pass/fail depending on port status
    ${ins} =    Get Library Instance    SerialLibrary
    Add Port    loop://    open=False
    Run Keyword And Expect Error    Port is closed.    Port Should Be Open
    Port Should Be Closed
    Open Port    
    Run Keyword And Expect Error    Port is open.    Port Should Be Closed
    Port Should Be Open
    [Teardown]    Delete All Ports

Switch Port should switch port    
    ${ins} =    Get Library Instance    SerialLibrary
    Add Port    loop://
    Add Port    loop://debug    make_current=True
    Current Port Should Be    loop://debug
    Switch Port    loop://
    Current Port Should Be    loop://
    [Teardown]    Delete All Ports

Get/Set Port Parameter should get/set specified parameter
    Add Port    loop://
    Add Port    loop://debug
    ${baudrate} =   Get Port Parameter    baudrate
    Should Be Equal As Strings    ${baudrate}    9600
    Set Port Parameter    baudrate    128000    port_locator=loop://debug
    Should Be Equal As Strings    ${baudrate}    9600
    ${baudrate} =   Get Port Parameter    baudrate    port_locator=loop://debug
    Should Be Equal As Strings    ${baudrate}    128000
    # wrong parameter name should fail
    Run Keyword And Expect Error    Wrong parameter name.    Set Port Parameter    NONEXISTENT   1234
    [Teardown]    Delete All Ports

Read All Data should read all data arrived to the port
    Add Port    loop://
    ${bytes} =    Set Variable    01 23 45 67 89 AB CD EF
    Write Data    ${bytes}
    ${read} =    Read All Data
    Should Be Equal As Strings    ${read}    ${bytes}
    [Teardown]    Delete All Ports

Read Data Should Be should fail if read bytes not equals to specified data.
    Add Port    loop://
    ${bytes} =    Set Variable    01 23 45 67 89 AB CD EF
    Write Data    ${bytes}
    Read Data Should Be    ${bytes}
    Write Data    FE DC BA
    Run Keyword And Expect Error    'FE DC BA'(read) != 'AB CD EF'(data)
    ...    Read Data Should Be    AB CD EF
    [Teardown]    Delete All Ports

Read All And Log should write log in specified loglevel.
    Add Port    loop://
    ${bytes} =    Set Variable    01 23 45 67 89 AB CD EF
    Write Data    ${bytes}
    Read All And Log
    Write Data    ${bytes}
    Read All And Log    loglevel=info
    Write Data    ${bytes}
    Read All And Log    loglevel=debug
    Write Data    ${bytes}
    Read All And Log    loglevel=WARN
    Write Data    ${bytes}
    Run Keyword And Expect Error    Invalid loglevel.    Read All And Log    loglevel='MYLEVEL'
    [Teardown]    Delete All Ports

Read Until should read until terminator or size
    Add Port    loop://    timeout=0.1
    ${bytes} =    Set Variable    
    Write Data    01 23 45 0A 67 89 AB CD EF
    ${read} =    Read Until
    Should Be Equal As Strings    ${read}    01 23 45 0A
    ${read} =    Read Until   size=2
    Should Be Equal As Strings    ${read}    67 89
    ${read} =    Read Until   terminator=CD
    Should Be Equal As Strings    ${read}    AB CD
    ${read} =    Read Until
    Should Be Equal As Strings    ${read}    EF
    ${read} =    Read Until
    Should Be Equal As Strings    ${read}    ${EMPTY}
    [Teardown]    Delete All Ports

Port Should (Not) Have Unread Bytes passes/failes according to the in_waiting status
    Add Port    loop://
    ${bytes} =    Set Variable    01 23 45 0A 67 89 AB CD EF
    Port Should Not Have Unread Bytes
    Run Keyword And Expect Error    Port has no in-waiting data.    Port Should Have Unread Bytes
    Write Data    ${bytes}
    Port Should Have Unread Bytes
    Run Keyword And Expect Error    Port has in-waiting data.    Port Should Not Have Unread Bytes
    [Teardown]    Delete All Ports

Read N Bytes should read specified number of bytes
    Add Port    loop://    timeout=0.1
    ${bytes} =    Set Variable    01 23 45 67 89 AB CD EF
    Write Data    ${bytes}
    ${read} =    Read N Bytes
    Should Be Equal As Strings    ${read}    01
    ${read} =    Read N Bytes    4
    Should Be Equal As Strings    ${read}    23 45 67 89
    ${read} =    Read N Bytes    10
    Should Be Equal As Strings    ${read}    AB CD EF
    [Teardown]    Delete All Ports

Flush port should flush i/o (this test just confirm no errors with the keyword).
    Add Port    loop://    timeout=0.1
    ${bytes} =    Set Variable    01 23 45 67 89 AB CD EF
    Write Data    ${bytes}
    ${read} =    Read N Bytes    4
    Should Be Equal As Strings    ${read}    01 23 45 67
    Flush Port
    ${read} =    Read N Bytes    4
    Should Be Equal As Strings    ${read}    89 AB CD EF
    [Teardown]    Delete All Ports

Reset Input Buffer clears input buffer.
    Add Port    loop://    timeout=0.1
    Write Data    01 23 45 67 89 AB CD EF
    ${read} =    Read N Bytes    4
    Should Be Equal As Strings    ${read}    01 23 45 67
    Reset Input Buffer
    Read Data Should Be    ${EMPTY}
    [Teardown]    Delete All Ports

Reset Output Buffer clears output buffer.
    Add Port    loop://    timeout=0.1
    Write Data    01 23 45 67
    Reset Output Buffer
    Write Data    89 AB CD EF
    ${read} =    Read N Bytes    4
    Should Be Equal As Strings    ${read}    89 AB CD EF
    ${read} =    Read N Bytes    4
    Should Be Equal As Strings    ${read}    ${EMPTY}
    [Teardown]    Delete All Ports

Send Break should send break (just comfirms no errors)
    Add Port    loop://    timeout=0.1
    Write Data    01 23 45 67
    Send Break
    Send Break    0.5
    ${read} =    Read N Bytes    4
    Should Be Equal As Strings    ${read}    01 23 45 67
    [Teardown]    Delete All Ports
    
Set/get RTS should set/get RTS status
    Add Port    loop://    timeout=0.1
    Set RTS    On
    RTS Should Be   On
    CTS Should Be   On
    Run Keyword And Expect Error   RTS should be Off but On.   RTS Should Be   Off
    Set RTS    Off
    RTS Should Be   Off
    CTS Should Be   Off
    Run Keyword And Expect Error   RTS should be On but Off.   RTS Should Be   On
    [Teardown]    Delete All Ports
    
Get CTS Status should return CTS status
    Add Port    loop://    timeout=0.1
    ${status} =    Get CTS Status
    Should Be Equal As Strings    ${status}    True
    [Teardown]    Delete All Ports
    
Get DSR Status should return DSR status
    Add Port    loop://    timeout=0.1
    ${status} =    Get DSR Status
    Should Be Equal As Strings    ${status}    True
    [Teardown]    Delete All Ports
    
Get RI Status should return RI status
    Add Port    loop://    timeout=0.1
    ${status} =    Get RI Status
    Should Be Equal As Strings    ${status}    False
    [Teardown]    Delete All Ports
    
Get CD Status should return CD status
    Add Port    loop://    timeout=0.1
    ${status} =    Get CD Status
    Should Be Equal As Strings    ${status}    True
    [Teardown]    Delete All Ports

Set RS485 Mode should be callable
    [Setup]  Add Port    loop://    timeout=0.1
    [Teardown]    Delete All Ports
    [Template]    Set RS485 Mode
    On
    Off
    Yes
    No
    True
    False
    1
    0

Hello serial test
     Add Port    loop://
     Write Data    Hello World    encoding=ascii
     Read Data Should Be    Hello World    encoding=ascii
    [Teardown]    Delete All Ports


*** Keywords

Parameter Matches to SerialBase attributes
    [Arguments]    ${key}
    ${instance} =    Get Library Instance    SerialLibrary
    ${sb} =   Get SerialBase Instance
    Dictionary Should Contain Item    ${instance._defaults}   ${key}   ${sb.${key}}

Get SerialBase Instance
    ${ins} =    Evaluate
    ...    __import__('serial').SerialBase(timeout=1.0, write_timeout=1.0, inter_byte_timeout=0.0)
    [Return]        ${ins}

Should Be Type Of
    [Arguments]    ${object}    ${typestr}
    Should Be Equal    ${object.__class__.__name__}    ${typestr}

Run '${keyword}' If '${attr}' Is Available
    [Arguments]    @{args}
    ${instance} =    Get Library Instance    SerialLibrary
    ${instance.${attr}}
    
