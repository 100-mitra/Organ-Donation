const { ethers, network, artifacts } = require("hardhat");
const fs = require("fs");
const path = require("path");

// Deploy AuditLedger and write its address + ABI + allocator to
// deployments/<network>.json, which the FastAPI backend reads at startup.
async function main() {
  const [allocator] = await ethers.getSigners();

  const Ledger = await ethers.getContractFactory("AuditLedger");
  const ledger = await Ledger.deploy();
  await ledger.waitForDeployment();
  const address = await ledger.getAddress();

  const artifact = await artifacts.readArtifact("AuditLedger");
  const out = {
    network: network.name,
    address,
    allocator: allocator.address,
    abi: artifact.abi,
  };

  const dir = path.join(__dirname, "..", "..", "deployments");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${network.name}.json`);
  fs.writeFileSync(file, JSON.stringify(out, null, 2) + "\n");

  console.log(`AuditLedger deployed at ${address} (allocator ${allocator.address})`);
  console.log(`wrote ${file}`);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
