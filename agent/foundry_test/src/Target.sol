// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Target {
    address public owner;
    uint256 public storedValue;

    // ⚠️ Vulnerable initializer — no access control
    function init(address _owner) external {
        owner = _owner;
    }

    function setValue(uint256 newValue) external {
        require(msg.sender == owner, "Not owner");
        storedValue = newValue;
    }

    // Add a dummy payable function to make tests easier
    receive() external payable {}
}
