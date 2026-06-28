// Illustrative on-chain gas per AuditLedger op (in-process Hardhat network).
// Run: npx hardhat run scripts/gas.js
const { ethers } = require("hardhat");

const h = (n) => "0x" + BigInt(n).toString(16).padStart(64, "0");

async function gasOf(txPromise) {
  const r = await (await txPromise).wait();
  return Number(r.gasUsed);
}

async function main() {
  const L = await (await ethers.getContractFactory("AuditLedger")).deploy();
  await L.waitForDeployment();

  const pool = [h(1), h(2), h(3), h(4), h(5)]; // already strictly ascending
  const donor = h(0xd0);

  const reg1 = await gasOf(L.registerRecipient(pool[0]));
  for (let i = 1; i < pool.length; i++) await (await L.registerRecipient(pool[i])).wait();
  const regDonor = await gasOf(L.registerDonor(donor));
  const dec = await gasOf(L.logDecision(donor, pool, [pool[2], pool[0]], h(0xdead), "kidney_v1"));
  const erase = await gasOf(L.eraseRecipient(pool[4]));

  console.log(JSON.stringify({
    deploy_note: "one-time",
    registerRecipient: reg1,
    registerDonor: regDonor,
    "logDecision(pool=5)": dec,
    eraseRecipient: erase,
  }, null, 2));
}

main().catch((e) => { console.error(e); process.exit(1); });
