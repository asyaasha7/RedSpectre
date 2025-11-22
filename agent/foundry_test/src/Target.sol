// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

contract Target {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function setOwner(address newOwner) external {
        owner = newOwner;
    }
}
