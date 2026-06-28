// Exercises the SAME canon.js + verify.js the browser Verify button imports, but
// from Node against the live API — proving the browser verify path is green
// end-to-end without a headless browser. Run from web/: `node verify_e2e.mjs`.
import { verifyDecision } from "./src/verify.js";

const API = process.env.API_URL || "http://127.0.0.1:8010";

async function main() {
  await fetch(`${API}/seed`, { method: "POST" }).then((r) => r.json());
  const d = await fetch(`${API}/match`, { method: "POST" }).then((r) => r.json());
  const audit = await fetch(`${API}/audit`).then((r) => r.json());
  const revealed = await fetch(`${API}/reveal`).then((r) => r.json());

  const latest = audit.decisions.find((x) => x.decisionId === d.decisionId);
  const res = verifyDecision(latest, revealed.revealed);
  for (const c of res.checks) console.log(`  ${c.ok ? "[ok]  " : "[FAIL]"} ${c.name}`);
  if (!res.allOk) {
    console.error("FAIL: browser verify path does not match chain");
    process.exit(1);
  }

  // Negative: a tampered hash must be rejected (compare is not vacuous).
  const tampered = { ...latest, rankingHash: "0x" + "00".repeat(32) };
  if (verifyDecision(tampered, revealed.revealed).allOk) {
    console.error("FAIL: tampered decision still verified");
    process.exit(1);
  }
  console.log("  [ok]  NEGATIVE: tampered decision rejected");
  console.log(`PASS: browser verify path green for decision #${d.decisionId}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
