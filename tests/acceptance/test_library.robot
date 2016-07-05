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


*** Keywords

Parameter Matches to SerialBase attributes
    [Arguments]    ${key}
    ${instance} =    Get Library Instance    SerialLibrary
    ${sb} =   Get SerialBase Instance
    Dictionary Should Contain Item    ${instance._defaults}   ${key}   ${sb.${key}}

Get SerialBase Instance
    ${ins} =    Evaluate    __import__('serial').SerialBase()
    [Return]        ${ins}

Should Be Type Of
    [Arguments]    ${object}    ${typestr}
    Should Be Equal    ${object.__class__.__name__}    ${typestr}

