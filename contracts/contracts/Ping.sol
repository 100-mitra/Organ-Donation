// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Ping — Phase 0 toolchain smoke test.
/// @notice Exists only to prove solc 0.8.24 + hardhat-ethers + deploy work
///         end-to-end. Replaced by AuditLedger.sol in Phase 1.
contract Ping {
    string public constant ledgerName = "organ-donation-audit-ledger";

    function answer() external pure returns (uint256) {
        return 42;
    }
}
