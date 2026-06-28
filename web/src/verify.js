// Independent recompute-and-compare — the browser Verify logic (Phase 3).
//
// Mirrors engine/verifier.py. It reconstructs the active recipient set from the
// on-chain registration/erasure events (block-aware), confirms the decision's
// candidate pool equals that set and the revealed recipients equal the pool, then
// recomputes the full CAS ranking — closing subset-drop (D-015) without trusting
// the contract's own enforcement. CAS lives in cas.js (twin of engine/scoring.py).

import { commit, rankingHash } from "./canon.js";
import { rank as casRank } from "./cas.js";

const KNOWN_KINDS = new Set(["recipient", "donor"]);
const KIND_RECIPIENT = 1; // matches AuditLedger.KIND_RECIPIENT

export function activeRecipientSet(registrations, erasures, asOfBlock) {
  const active = new Set();
  for (const r of registrations) if (r.kind === KIND_RECIPIENT && r.block <= asOfBlock) active.add(r.commitment);
  for (const e of erasures) if (e.block <= asOfBlock) active.delete(e.commitment);
  return active;
}

const sameSet = (a, b) => a.size === b.size && [...a].every((x) => b.has(x));

export function verifyDecision(
  onchain,
  revealed,
  registeredCommitments = [],
  policy = null,
  registrations = null,
  erasures = null
) {
  const checks = [];
  const registered = new Set(registeredCommitments);
  const pool = onchain.candidatePool || [];

  // 1. BINDING: each revealed record opens + was Registered on-chain (D-013).
  for (const [id, e] of Object.entries(revealed)) {
    const opens = commit(e.record, e.salt) === e.commitment;
    checks.push({ name: `revealed ${id}: opens + registered on-chain`, ok: opens && registered.has(e.commitment) });
  }

  // 2. known kinds + 3. exactly one donor (D-015).
  const unknown = Object.entries(revealed).filter(([, e]) => !KNOWN_KINDS.has(e.kind));
  checks.push({ name: "all revealed kinds are recognized", ok: unknown.length === 0 });
  const donors = Object.values(revealed).filter((e) => e.kind === "donor");
  const oneDonor = donors.length === 1 && donors[0].commitment === onchain.donorCommitment;
  checks.push({ name: "exactly one donor, matching on-chain", ok: oneDonor });

  // 4. POOL COMPLETENESS: logged pool == active registered recipient set (D-015).
  let poolComplete = false;
  if (registrations && erasures) {
    const active = activeRecipientSet(registrations, erasures, onchain.block);
    const poolSet = new Set(pool);
    poolComplete = poolSet.size === pool.length && sameSet(poolSet, active);
  }
  checks.push({ name: "candidate pool == active registered recipients (completeness, D-015)", ok: poolComplete });

  // 5. the revealed recipients are EXACTLY the candidate pool.
  const recips = Object.values(revealed).filter((e) => e.kind === "recipient");
  checks.push({
    name: "revealed recipients == candidate pool",
    ok: sameSet(new Set(recips.map((e) => e.commitment)), new Set(pool)),
  });

  // 6. recompute the CAS ranking over the revealed pool and compare.
  let recomputedRanked = [];
  let rankedOk = false;
  let coverageOk = false;
  if (oneDonor && policy) {
    const byId = Object.fromEntries(recips.map((e) => [e.record.id, e]));
    const { ranked } = casRank(donors[0].record, recips.map((e) => e.record), policy, onchain.donorCommitment);
    recomputedRanked = ranked.map((e) => byId[e.id].commitment);
    rankedOk = JSON.stringify(recomputedRanked) === JSON.stringify(onchain.rankedRecipientCommitments);
    coverageOk = sameSet(new Set(recomputedRanked), new Set(onchain.rankedRecipientCommitments));
  }
  checks.push({ name: "recomputed CAS ranking == on-chain ranked commitments", ok: rankedOk });
  checks.push({ name: "ranked set == eligible revealed recipients (coverage)", ok: coverageOk });

  // 7. ranking hash (binds donor + policy + pool + ranking).
  const recomputedHash = rankingHash(onchain.donorCommitment, pool, recomputedRanked, onchain.policyVersion);
  checks.push({ name: "recomputed ranking hash == on-chain", ok: recomputedHash === onchain.rankingHash });

  return { allOk: checks.every((c) => c.ok), checks, recomputedHash };
}
