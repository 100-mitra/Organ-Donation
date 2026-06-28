// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title AuditLedger — tamper-evident, role-gated log of allocation commitments
///        and decisions.
/// @notice Phase 1 walking skeleton: deliberately MINIMAL. Stores NO personal
///         data — only salted commitments (fingerprints) and decision events.
///         Only the `allocator` may write (CLAUDE.md §5, §10). This is a single
///         local node that *simulates* a NOTTO + hospitals consortium; it does
///         not claim decentralization.
contract AuditLedger {
    /// @notice The only address authorized to attest data and log decisions.
    address public immutable allocator;

    /// @notice Monotonic id assigned to each logged decision.
    uint256 public decisionCount;

    /// @notice A record's salted commitment was recorded on-chain.
    event Registered(bytes32 indexed commitment, address indexed by);

    /// @notice An allocation decision was logged. The ordered
    ///         `rankedRecipientCommitments` plus `rankingHash` let an auditor
    ///         recompute and confirm policy-faithful execution.
    event DecisionLogged(
        uint256 indexed decisionId,
        bytes32 donorCommitment,
        bytes32 rankingHash,
        string policyVersion,
        bytes32[] rankedRecipientCommitments,
        address indexed by
    );

    error NotAllocator(address caller);

    modifier onlyAllocator() {
        if (msg.sender != allocator) revert NotAllocator(msg.sender);
        _;
    }

    constructor() {
        allocator = msg.sender;
    }

    /// @notice Record a record's salted commitment on-chain (tamper-evident).
    function registerCommitment(bytes32 commitment) external onlyAllocator {
        emit Registered(commitment, msg.sender);
    }

    /// @notice Log an allocation decision; returns its assigned id.
    function logDecision(
        bytes32 donorCommitment,
        bytes32[] calldata rankedRecipientCommitments,
        bytes32 rankingHash,
        string calldata policyVersion
    ) external onlyAllocator returns (uint256 decisionId) {
        decisionId = decisionCount;
        emit DecisionLogged(
            decisionId,
            donorCommitment,
            rankingHash,
            policyVersion,
            rankedRecipientCommitments,
            msg.sender
        );
        decisionCount = decisionId + 1;
    }
}
