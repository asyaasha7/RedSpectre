// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/Target.sol";

contract SampleTest is Test {
    Target target;

    function setUp() public {
        target = new Target();
    }

    function testInitSetsOwner() public {
        address attacker = address(0xBEEF);
        target.init(attacker);
        assertEq(target.owner(), attacker);
    }

    function testSetValueOnlyByOwner() public {
        address attacker = address(0xBEEF);
        target.init(attacker);

        vm.prank(attacker);
        target.setValue(1337);

        assertEq(target.storedValue(), 1337);
    }
}
