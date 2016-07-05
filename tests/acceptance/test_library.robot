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

If no current port is assigned, add port will add one and make it current
    ${ins} =    Get Library Instance    SerialLibrary
    Should Be Equal    ${ins._current_port_locator}   ${NONE}
    Add Port    loop://
    Should Be Equal    ${ins._current_port_locator}   loop://
    Port should be open




*** Keywords

Parameter Matches to SerialBase attributes
    [Arguments]    ${key}
    ${instance} =    Get Library Instance    SerialLibrary
    ${sb} =   Get SerialBase Instance
    Dictionary Should Contain Item    ${instance._defaults}   ${key}   ${sb.${key}}

Get SerialBase Instance
    ${ins} =    Evaluate    __import__('serial').SerialBase()
    [Return]        ${ins}