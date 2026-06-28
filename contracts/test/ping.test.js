const { expect } = require("chai");
const { ethers } = require("hardhat");

// Phase 0 toolchain smoke test: compile + deploy + read. Replaced by real
// AuditLedger tests (role-gating, decision events) in Phase 1.
describe("Ping (Phase 0 toolchain smoke test)", function () {
  it("deploys and answers", async function () {
    const Ping = await ethers.getContractFactory("Ping");
    const ping = await Ping.deploy();
    await ping.waitForDeployment();

    expect(await ping.answer()).to.equal(42n); // ethers v6 returns BigInt
    expect(await ping.ledgerName()).to.equal("organ-donation-audit-ledger");
  });
});
