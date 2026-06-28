// Independent recompute-and-compare — the browser Verify logic.
//
// Mirrors engine/scoring.py (trivial policy) + scripts/e2e.py (recompute). Given
// an on-chain decision and the revealed records+salts, it re-derives the ranking
// from scratch and checks it equals what was logged.

import { commit, rankingHash } from "./canon.js";

// Trivial Phase 1 policy: waiting_days desc, id asc. Must match engine/scoring.py.
export function rankRecipients(records) {
  return [...records].sort((a, b) => {
    if (b.waiting_days !== a.waiting_days) return b.waiting_days - a.waiting_days;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  });
}

// onchain: { donorCommitment, rankingHash, policyVersion, rankedRecipientCommitments }
// revealed: { id: { record, salt, commitment, kind } }
export function verifyDecision(onchain, revealed) {
  const checks = [];

  // 1. every revealed record's commitment must open to its stored commitment
  for (const [id, e] of Object.entries(revealed)) {
    checks.push({ name: `commitment opens: ${id}`, ok: commit(e.record, e.salt) === e.commitment });
  }

  // 2. independently re-rank the revealed recipients
  const recips = Object.values(revealed).filter((e) => e.kind === "recipient");
  const ranked = rankRecipients(recips.map((e) => e.record));
  const byId = Object.fromEntries(recips.map((e) => [e.record.id, e]));
  const recomputedRanked = ranked.map((r) => byId[r.id].commitment);
  checks.push({
    name: "recomputed ranking == on-chain ranked commitments",
    ok: JSON.stringify(recomputedRanked) === JSON.stringify(onchain.rankedRecipientCommitments),
  });

  // 3. donor commitment + ranking hash
  const donor = Object.values(revealed).find((e) => e.kind === "donor");
  checks.push({
    name: "donor commitment == on-chain",
    ok: !!donor && donor.commitment === onchain.donorCommitment,
  });
  const recomputedHash = rankingHash(onchain.donorCommitment, recomputedRanked, onchain.policyVersion);
  checks.push({ name: "recomputed ranking hash == on-chain", ok: recomputedHash === onchain.rankingHash });

  return { allOk: checks.every((c) => c.ok), checks, recomputedHash };
}
