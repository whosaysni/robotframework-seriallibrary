====================================
SerialLibrary for Robot Framework
====================================

This is a serial port test library for Robot Framework.


Example::

    *** settings ***
    Library    SerialLibrary    loop://    encoding=ascii

    *** test cases ***
    Hello serial test
         Write Data    Hello World
         Read Data Should Be    Hello World


Another Example::

    *** settings ***
    Library    SerialLibrary

    *** test cases ***
    Read Until should read until terminator or size
        [Setup]    Add Port    loop://    timeout=0.1
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
