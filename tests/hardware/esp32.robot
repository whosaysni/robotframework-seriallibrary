*** Settings ***
Documentation    Tests against a real ESP32 board behind a USB-UART bridge with auto-reset
...              wiring (DTR -> IO0, RTS -> EN). Nothing is written to the board: it is only
...              reset through the modem lines and its boot log is read.
...
...              Run with: robot --variable PORT:/dev/ttyUSB0 tests/hardware

Library          SerialLibrary    encoding=utf-8

Test Setup       Add Port    ${PORT}    baudrate=115200    timeout=0.5
Test Teardown    Delete All Ports

Test Tags        hardware


*** Variables ***
${PORT}            /dev/ttyUSB0
${BOOT_END}        START APPLICATION:
${BOOT_TIMEOUT}    15


*** Test Cases ***
Port Is Listed On The System
    ${names} =    List COM Port Names
    Should Contain    ${names}    ${PORT}
    ${ports} =    COM Port Should Exist Regexp    ${PORT}
    Log    ${ports}[0].description / ${ports}[0].hwid

Port Uses The Requested Settings
    ${baudrate} =    Get Port Parameter    baudrate
    ${parity} =    Get Port Parameter    parity
    Should Be Equal    ${baudrate}    ${115200}
    Should Be Equal    ${parity}    N
    Port Should Be Open

Reset Through RTS Shows The Boot Log
    Reset Board
    ${boot} =    Read Until Text    ${BOOT_END}
    Should Contain    ${boot}    MOUNT DRIVERS
    Should Contain    ${boot}    MODULE WIFI
    Should End With    ${boot}    ${BOOT_END}

Read Until Times Out Without Terminator
    Reset Board
    Read Until Text    ${BOOT_END}
    Reset Input Buffer
    Set Port Parameter    timeout    0.3
    ${data} =    Read Until    NEVER SENT    terminator_encoding=ascii
    Should Not End With    ${data}    NEVER SENT

Modem Lines Can Be Driven
    Set DTR    On
    Set RTS    On
    DTR Should Be    On
    RTS Should Be    On
    Set DTR    Off
    DTR Should Be    Off
    Run Keyword And Expect Error    DTR should be On but Off.    DTR Should Be    On
    [Teardown]    Run Keywords    Set RTS    Off    AND    Delete All Ports

Unread Bytes Are Detected And Discarded
    Reset Board
    Wait Until Keyword Succeeds    3s    100ms    Port Should Have Unread Bytes
    Reset Input Buffer
    Port Should Not Have Unread Bytes
    Port Should Not Have Unsent Bytes

Baudrate Can Be Changed On An Open Port
    ${previous} =    Set Port Parameter    baudrate    9600
    Should Be Equal    ${previous}    ${115200}
    ${baudrate} =    Get Port Parameter    baudrate
    Should Be Equal    ${baudrate}    ${9600}
    Set Port Parameter    baudrate    115200
    Reset Board
    ${boot} =    Read Until Text    ${BOOT_END}
    Should Contain    ${boot}    MOUNT DRIVERS

Closed Port Can Be Reopened
    Close Port
    Port Should Be Closed
    Open Port
    Port Should Be Open
    Reset Board
    ${boot} =    Read Until Text    ${BOOT_END}
    Should Contain    ${boot}    MOUNT DRIVERS

Port Is Exclusive To One Locator
    Run Keyword And Expect Error    Port already exists.    Add Port    ${PORT}


*** Keywords ***
Reset Board
    [Documentation]    Pulses EN low through RTS, IO0 kept high: normal boot.
    Reset Input Buffer
    Set DTR    Off
    Set RTS    On
    Sleep    100ms
    Set RTS    Off

Read Until Text
    [Documentation]    Reads until ``text`` while the board boots, which takes several seconds.
    [Arguments]    ${text}
    ${previous} =    Set Port Parameter    timeout    ${BOOT_TIMEOUT}
    TRY
        ${data} =    Read Until    ${text}    terminator_encoding=utf-8
    FINALLY
        Set Port Parameter    timeout    ${previous}
    END
    Should End With    ${data}    ${text}    Board did not print '${text}' within ${BOOT_TIMEOUT}s.
    RETURN    ${data}
