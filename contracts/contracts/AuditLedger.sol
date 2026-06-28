// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title AuditLedger — tamper-evident, role-gated ledger of allocation
///        commitments and decisions (Phase 3: the real ledger).
/// @notice Stores NO personal data — only salted commitments (fingerprints) and
///         decision events. Only the `allocator` may write (CLAUDE.md §5, §10).
///         A single local node *simulating* a NOTTO + hospitals consortium.
///
/// The Phase 3 innovation closes the carried-forward subset-drop gap (D-015): the
/// ledger tracks the ACTIVE RECIPIENT SET, and `logDecision` requires the
/// submitted candidate pool to equal that full set (complete, strictly sorted, all
/// active). A registered recipient therefore CANNOT be silently excluded from a
/// decision's pool — the chain rejects an incomplete pool.
contract AuditLedger {
    uint8 public constant KIND_RECIPIENT = 1;
    uint8 public constant KIND_DONOR = 2;

    address public immutable allocator;
    uint256 public decisionCount;

    /// kind of a commitment: 0 unregistered, 1 recipient, 2 donor.
    mapping(bytes32 => uint8) public kindOf;
    /// a recipient commitment that is currently active (registered, not erased).
    mapping(bytes32 => bool) public activeRecipient;
    /// size of the active recipient set — a decision's pool must match this.
    uint256 public activeRecipientCount;

    event Registered(bytes32 indexed commitment, uint8 kind, address indexed by);
    event Erased(bytes32 indexed commitment, address indexed by);
    event DecisionLogged(
        uint256 indexed decisionId,
        bytes32 donorCommitment,
        bytes32 rankingHash,
        string policyVersion,
        bytes32[] candidatePool,
        bytes32[] rankedEligible,
        address indexed by
    );

    error NotAllocator(address caller);
    error AlreadyRegistered(bytes32 commitment);
    error NotActiveRecipient(bytes32 commitment);
    error DonorNotRegistered(bytes32 commitment);
    error PoolNotComplete(uint256 got, uint256 expected);
    error PoolNotStrictlySorted(bytes32 commitment);
    error PoolMemberNotActive(bytes32 commitment);
    error RankedNotActive(bytes32 commitment);

    modifier onlyAllocator() {
        if (msg.sender != allocator) revert NotAllocator(msg.sender);
        _;
    }

    constructor() {
        allocator = msg.sender;
    }

    /// @notice Register a recipient candidate's commitment (joins the active set).
    function registerRecipient(bytes32 commitment) external onlyAllocator {
        if (kindOf[commitment] != 0) revert AlreadyRegistered(commitment);
        kindOf[commitment] = KIND_RECIPIENT;
        activeRecipient[commitment] = true;
        activeRecipientCount += 1;
        emit Registered(commitment, KIND_RECIPIENT, msg.sender);
    }

    /// @notice Register a donor's commitment (not part of the candidate pool).
    function registerDonor(bytes32 commitment) external onlyAllocator {
        if (kindOf[commitment] != 0) revert AlreadyRegistered(commitment);
        kindOf[commitment] = KIND_DONOR;
        emit Registered(commitment, KIND_DONOR, msg.sender);
    }

    /// @notice Erase a recipient (the on-chain marker; the off-chain salt + record
    ///         are destroyed separately, making the commitment unlinkable — §14).
    ///         Removes the recipient from the active set / future pools.
    function eraseRecipient(bytes32 commitment) external onlyAllocator {
        if (!activeRecipient[commitment]) revert NotActiveRecipient(commitment);
        activeRecipient[commitment] = false;
        activeRecipientCount -= 1;
        emit Erased(commitment, msg.sender);
    }

    /// @notice Log an allocation decision. The candidate pool MUST equal the full
    ///         active recipient set (complete, strictly ascending, all active), so
    ///         no registered recipient can be silently dropped (D-015). The ranked
    ///         eligible list is a subset of the active pool (eligibility is checked
    ///         off-chain and re-verified by the auditor).
    function logDecision(
        bytes32 donorCommitment,
        bytes32[] calldata candidatePool,
        bytes32[] calldata rankedEligible,
        bytes32 rankingHash,
        string calldata policyVersion
    ) external onlyAllocator returns (uint256 decisionId) {
        if (kindOf[donorCommitment] != KIND_DONOR) revert DonorNotRegistered(donorCommitment);

        // POOL COMPLETENESS: length match + strictly ascending (no dups) + all
        // active  ⇒  candidatePool == the active recipient set.
        if (candidatePool.length != activeRecipientCount) {
            revert PoolNotComplete(candidatePool.length, activeRecipientCount);
        }
        for (uint256 i = 0; i < candidatePool.length; i++) {
            if (!activeRecipient[candidatePool[i]]) revert PoolMemberNotActive(candidatePool[i]);
            if (i > 0 && uint256(candidatePool[i]) <= uint256(candidatePool[i - 1])) {
                revert PoolNotStrictlySorted(candidatePool[i]);
            }
        }
        for (uint256 j = 0; j < rankedEligible.length; j++) {
            if (!activeRecipient[rankedEligible[j]]) revert RankedNotActive(rankedEligible[j]);
        }

        decisionId = decisionCount;
        emit DecisionLogged(
            decisionId, donorCommitment, rankingHash, policyVersion, candidatePool, rankedEligible, msg.sender
        );
        decisionCount = decisionId + 1;
    }
}
