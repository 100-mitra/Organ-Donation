const { expect } = require("chai");
const { ethers } = require("hardhat");

// Phase 1: prove the ledger is role-gated and emits faithful decision events.
describe("AuditLedger", function () {
  const C1 = "0x" + "a1".repeat(32);
  const C2 = "0x" + "b2".repeat(32);
  const DONOR = "0x" + "dd".repeat(32);
  const RHASH = "0x" + "ee".repeat(32);
  const POLICY = "skeleton-waiting-time-v0";

  async function deploy() {
    const [allocator, outsider] = await ethers.getSigners();
    const Ledger = await ethers.getContractFactory("AuditLedger");
    const ledger = await Ledger.deploy();
    await ledger.waitForDeployment();
    return { ledger, allocator, outsider };
  }

  it("sets the deployer as the allocator", async function () {
    const { ledger, allocator } = await deploy();
    expect(await ledger.allocator()).to.equal(allocator.address);
  });

  it("lets the allocator register a commitment (emits Registered)", async function () {
    const { ledger, allocator } = await deploy();
    await expect(ledger.registerCommitment(C1))
      .to.emit(ledger, "Registered")
      .withArgs(C1, allocator.address);
  });

  it("rejects registerCommitment from a non-allocator", async function () {
    const { ledger, outsider } = await deploy();
    await expect(ledger.connect(outsider).registerCommitment(C1))
      .to.be.revertedWithCustomError(ledger, "NotAllocator")
      .withArgs(outsider.address);
  });

  it("rejects logDecision from a non-allocator", async function () {
    const { ledger, outsider } = await deploy();
    await expect(
      ledger.connect(outsider).logDecision(DONOR, [C1, C2], RHASH, POLICY)
    )
      .to.be.revertedWithCustomError(ledger, "NotAllocator")
      .withArgs(outsider.address);
  });

  it("emits DecisionLogged with exact ordered args and bumps decisionCount", async function () {
    const { ledger, allocator } = await deploy();
    expect(await ledger.decisionCount()).to.equal(0n);

    await expect(ledger.logDecision(DONOR, [C1, C2], RHASH, POLICY))
      .to.emit(ledger, "DecisionLogged")
      .withArgs(0n, DONOR, RHASH, POLICY, [C1, C2], allocator.address);

    expect(await ledger.decisionCount()).to.equal(1n);
  });

  it("assigns monotonically increasing decision ids", async function () {
    const { ledger } = await deploy();
    await ledger.logDecision(DONOR, [C1], RHASH, POLICY);
    await expect(ledger.logDecision(DONOR, [C2], RHASH, POLICY))
      .to.emit(ledger, "DecisionLogged")
      .withArgs(1n, DONOR, RHASH, POLICY, [C2], (await ledger.allocator()));
    expect(await ledger.decisionCount()).to.equal(2n);
  });
});
