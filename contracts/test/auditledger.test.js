const { expect } = require("chai");
const { ethers } = require("hardhat");

// Phase 3: role-gated lifecycle (register recipient/donor, erase) + the pool-
// completeness enforcement that closes subset-drop (D-015).
describe("AuditLedger", function () {
  // Three recipient commitments already in strict ascending order, a donor, and a
  // never-registered commitment.
  const C1 = "0x" + "11".repeat(32);
  const C2 = "0x" + "22".repeat(32);
  const C3 = "0x" + "33".repeat(32);
  const DONOR = "0x" + "dd".repeat(32);
  const STRANGER = "0x" + "99".repeat(32);
  const RHASH = "0x" + "ee".repeat(32);
  const POLICY = "kidney_v1";

  async function deploy() {
    const [allocator, outsider] = await ethers.getSigners();
    const Ledger = await ethers.getContractFactory("AuditLedger");
    const ledger = await Ledger.deploy();
    await ledger.waitForDeployment();
    return { ledger, allocator, outsider };
  }

  async function seeded() {
    const { ledger, allocator, outsider } = await deploy();
    await ledger.registerRecipient(C1);
    await ledger.registerRecipient(C2);
    await ledger.registerRecipient(C3);
    await ledger.registerDonor(DONOR);
    return { ledger, allocator, outsider };
  }

  it("sets the deployer as the allocator", async function () {
    const { ledger, allocator } = await deploy();
    expect(await ledger.allocator()).to.equal(allocator.address);
  });

  it("registers recipients (active set grows) and donors (kind tagged)", async function () {
    const { ledger, allocator } = await deploy();
    await expect(ledger.registerRecipient(C1))
      .to.emit(ledger, "Registered").withArgs(C1, 1, allocator.address);
    await ledger.registerDonor(DONOR);
    expect(await ledger.activeRecipientCount()).to.equal(1n);
    expect(await ledger.activeRecipient(C1)).to.equal(true);
    expect(await ledger.kindOf(DONOR)).to.equal(2n);
  });

  it("rejects re-registering the same commitment", async function () {
    const { ledger } = await deploy();
    await ledger.registerRecipient(C1);
    await expect(ledger.registerRecipient(C1)).to.be.revertedWithCustomError(ledger, "AlreadyRegistered");
  });

  it("role-gates every write", async function () {
    const { ledger, outsider } = await deploy();
    await expect(ledger.connect(outsider).registerRecipient(C1)).to.be.revertedWithCustomError(ledger, "NotAllocator");
    await expect(ledger.connect(outsider).registerDonor(DONOR)).to.be.revertedWithCustomError(ledger, "NotAllocator");
    await expect(ledger.connect(outsider).logDecision(DONOR, [C1], [], RHASH, POLICY)).to.be.revertedWithCustomError(ledger, "NotAllocator");
  });

  it("erases a recipient (shrinks the active set; emits Erased)", async function () {
    const { ledger, allocator } = await seeded();
    await expect(ledger.eraseRecipient(C2)).to.emit(ledger, "Erased").withArgs(C2, allocator.address);
    expect(await ledger.activeRecipient(C2)).to.equal(false);
    expect(await ledger.activeRecipientCount()).to.equal(2n);
    await expect(ledger.eraseRecipient(C2)).to.be.revertedWithCustomError(ledger, "NotActiveRecipient");
  });

  it("logs a decision when the pool equals the full active set", async function () {
    const { ledger, allocator } = await seeded();
    await expect(ledger.logDecision(DONOR, [C1, C2, C3], [C3, C1, C2], RHASH, POLICY))
      .to.emit(ledger, "DecisionLogged")
      .withArgs(0n, DONOR, RHASH, POLICY, [C1, C2, C3], [C3, C1, C2], allocator.address);
    expect(await ledger.decisionCount()).to.equal(1n);
  });

  it("REJECTS an incomplete pool — closes subset-drop (D-015)", async function () {
    const { ledger } = await seeded();
    // dropping C2 from the pool: length 2 != activeRecipientCount 3
    await expect(ledger.logDecision(DONOR, [C1, C3], [C1, C3], RHASH, POLICY))
      .to.be.revertedWithCustomError(ledger, "PoolNotComplete");
  });

  it("rejects an unsorted / duplicate pool", async function () {
    const { ledger } = await seeded();
    await expect(ledger.logDecision(DONOR, [C2, C1, C3], [C1], RHASH, POLICY))
      .to.be.revertedWithCustomError(ledger, "PoolNotStrictlySorted");
    await expect(ledger.logDecision(DONOR, [C1, C1, C3], [C1], RHASH, POLICY))
      .to.be.revertedWithCustomError(ledger, "PoolNotStrictlySorted");
  });

  it("rejects a pool member that is not active (right length, wrong member)", async function () {
    const { ledger } = await seeded();
    await ledger.eraseRecipient(C3); // active set now {C1,C2}, count 2
    await expect(ledger.logDecision(DONOR, [C1, STRANGER], [C1], RHASH, POLICY))
      .to.be.revertedWithCustomError(ledger, "PoolMemberNotActive");
  });

  it("rejects a ranked commitment that is not active", async function () {
    const { ledger } = await seeded();
    await expect(ledger.logDecision(DONOR, [C1, C2, C3], [C1, STRANGER], RHASH, POLICY))
      .to.be.revertedWithCustomError(ledger, "RankedNotActive");
  });

  it("rejects a decision whose donor was never registered", async function () {
    const { ledger } = await seeded();
    await expect(ledger.logDecision(STRANGER, [C1, C2, C3], [C1], RHASH, POLICY))
      .to.be.revertedWithCustomError(ledger, "DonorNotRegistered");
  });
});
