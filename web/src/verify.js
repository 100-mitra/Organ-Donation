// Independent recompute-and-compare — the browser Verify logic.
//
// Mirrors engine/scoring.py (trivial policy) + scripts/e2e.py (recompute). Given
// an on-chain decision and the revealed records+salts, it re-derives the ranking
// from scratch and checks it equals what was logged.

import { commit, rankingHash } from "./canon.js";

// A revealed record may only be one of these; an unrecognized kind is a hard
// failure (D-015 kind-mislabel). Must match engine/verifier.py KNOWN_KINDS.
const KNOWN_KINDS = new Set(["recipient", "donor"]);

// Trivial Phase 1 policy: waiting_days desc, id asc. Must match engine/scoring.py.
export function rankRecipients(records) {
  return [...records].sort((a, b) => {
    if (b.waiting_days !== a.waiting_days) return b.waiting_days - a.waiting_days;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  });
}

// onchain: { donorCommitment, rankingHash, policyVersion, rankedRecipientCommitments }
// revealed: { id: { record, salt, commitment, kind } }
// registeredCommitments: the on-chain Registered set (from GET /commitments)
export function verifyDecision(onchain, revealed, registeredCommitments = []) {
  const checks = [];
  const registered = new Set(registeredCommitments);

  // 1. BINDING (before re-ranking): each revealed record must (a) open to its
  //    stored commitment and (b) that commitment must have been Registered
  //    on-chain. A substituted/fabricated record fails (b) (D-013).
  for (const [id, e] of Object.entries(revealed)) {
    const opens = commit(e.record, e.salt) === e.commitment;
    const isRegistered = registered.has(e.commitment);
    checks.push({ name: `revealed ${id}: opens + registered on-chain`, ok: opens && isRegistered });
  }

  // 2. KNOWN KINDS: an unrecognized kind is a hard failure (D-015 kind-mislabel).
  const unknown = Object.entries(revealed).filter(([, e]) => !KNOWN_KINDS.has(e.kind));
  checks.push({ name: "all revealed kinds are recognized", ok: unknown.length === 0 });

  // 3. exactly ONE donor, matching on-chain (blocks relabelling a recipient as donor).
  const donors = Object.values(revealed).filter((e) => e.kind === "donor");
  checks.push({
    name: "exactly one donor, matching on-chain",
    ok: donors.length === 1 && donors[0].commitment === onchain.donorCommitment,
  });

  // 4. independently re-rank the revealed recipients
  const recips = Object.values(revealed).filter((e) => e.kind === "recipient");
  const ranked = rankRecipients(recips.map((e) => e.record));
  const byId = Object.fromEntries(recips.map((e) => [e.record.id, e]));
  const recomputedRanked = ranked.map((r) => byId[r.id].commitment);
  checks.push({
    name: "recomputed ranking == on-chain ranked commitments",
    ok: JSON.stringify(recomputedRanked) === JSON.stringify(onchain.rankedRecipientCommitments),
  });

  // 5. COVERAGE: ranking must cover EXACTLY the revealed recipients (closes omission).
  const revealedSet = new Set(recips.map((e) => e.commitment));
  const rankedSet = new Set(onchain.rankedRecipientCommitments);
  const coverage = revealedSet.size === rankedSet.size && [...revealedSet].every((c) => rankedSet.has(c));
  checks.push({ name: "ranked set == revealed recipient set (coverage)", ok: coverage });

  // 6. ranking hash
  const recomputedHash = rankingHash(onchain.donorCommitment, recomputedRanked, onchain.policyVersion);
  checks.push({ name: "recomputed ranking hash == on-chain", ok: recomputedHash === onchain.rankingHash });

  return { allOk: checks.every((c) => c.ok), checks, recomputedHash };
}
