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
  const registered = await fetch(`${API}/commitments`).then((r) => r.json());
  const policy = await fetch(`${API}/policy`).then((r) => r.json());
  const reg = await fetch(`${API}/registrations`).then((r) => r.json());

  const latest = audit.decisions.find((x) => x.decisionId === d.decisionId);
  const cs = registered.registered;
  const V = (oc, rv = revealed.revealed) =>
    verifyDecision(oc, rv, cs, policy, reg.registrations, reg.erasures);

  const res = V(latest);
  for (const c of res.checks) console.log(`  ${c.ok ? "[ok]  " : "[FAIL]"} ${c.name}`);
  if (!res.allOk) {
    console.error("FAIL: browser verify path does not match chain");
    process.exit(1);
  }

  // N1: a tampered hash must be rejected.
  if (V({ ...latest, rankingHash: "0x" + "00".repeat(32) }).allOk) {
    console.error("FAIL: tampered decision still verified");
    process.exit(1);
  }
  console.log("  [ok]  NEGATIVE N1: tampered ranking hash rejected");

  // N2: an unregistered commitment must be rejected (binding).
  const csMissing = cs.filter((c) => c !== latest.rankedRecipientCommitments[0]);
  if (verifyDecision(latest, revealed.revealed, csMissing, policy, reg.registrations, reg.erasures).allOk) {
    console.error("FAIL: unregistered/substituted commitment still verified");
    process.exit(1);
  }
  console.log("  [ok]  NEGATIVE N2: unregistered/substituted commitment rejected (binding real)");

  // N3 (D-015): a subset-drop decision — drop a registered recipient from the pool,
  // ranking and reveal — must fail the completeness check.
  const dropped = latest.candidatePool[0];
  const droppedRid = Object.keys(revealed.revealed).find(
    (k) => revealed.revealed[k].commitment === dropped
  );
  const rv2 = { ...revealed.revealed };
  delete rv2[droppedRid];
  const tamperedPool = {
    ...latest,
    candidatePool: latest.candidatePool.filter((c) => c !== dropped),
    rankedRecipientCommitments: latest.rankedRecipientCommitments.filter((c) => c !== dropped),
  };
  if (V(tamperedPool, rv2).allOk) {
    console.error("FAIL: subset-drop decision still verified");
    process.exit(1);
  }
  console.log("  [ok]  NEGATIVE N3: subset-drop (dropped registered recipient) rejected (completeness, D-015)");

  // N4 (UI tamper demo): edit a revealed record after the fact -> commitment no longer opens.
  const rv3 = structuredClone(revealed.revealed);
  const rrid = Object.keys(rv3).find((k) => rv3[k].kind === "recipient");
  rv3[rrid].record.dialysis_start_epoch_day -= 2000;
  if (V(latest, rv3).allOk) {
    console.error("FAIL: edited record still verified");
    process.exit(1);
  }
  console.log("  [ok]  NEGATIVE N4: edited record fails its binding (UI tamper demo)");

  console.log(`PASS: browser verify path green for decision #${d.decisionId}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
