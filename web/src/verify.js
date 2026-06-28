// Independent recompute-and-compare — the browser Verify logic (Phase 2: full CAS).
//
// Mirrors engine/verifier.py. Given an on-chain decision, the revealed
// records+salts, the on-chain Registered set, and the policy, it re-derives the
// CAS ranking from scratch (gates + integer scoring + tie-breaks) and checks it
// equals what was logged. The CAS itself lives in cas.js (twin of engine/scoring.py).

import { commit, rankingHash } from "./canon.js";
import { rank as casRank } from "./cas.js";

// A revealed record may only be one of these (D-015 kind-mislabel).
const KNOWN_KINDS = new Set(["recipient", "donor"]);

// onchain: { donorCommitment, rankingHash, policyVersion, rankedRecipientCommitments }
// revealed: { id: { record, salt, commitment, kind } }
// registeredCommitments: the on-chain Registered set (GET /commitments)
// policy: the versioned policy JSON (GET /policy) — required for the CAS recompute
export function verifyDecision(onchain, revealed, registeredCommitments = [], policy = null) {
  const checks = [];
  const registered = new Set(registeredCommitments);

  // 1. BINDING (before re-ranking): each revealed record opens + was Registered (D-013).
  for (const [id, e] of Object.entries(revealed)) {
    const opens = commit(e.record, e.salt) === e.commitment;
    checks.push({
      name: `revealed ${id}: opens + registered on-chain`,
      ok: opens && registered.has(e.commitment),
    });
  }

  // 2. KNOWN KINDS (D-015).
  const unknown = Object.entries(revealed).filter(([, e]) => !KNOWN_KINDS.has(e.kind));
  checks.push({ name: "all revealed kinds are recognized", ok: unknown.length === 0 });

  // 3. exactly ONE donor matching on-chain (D-015).
  const donors = Object.values(revealed).filter((e) => e.kind === "donor");
  const oneDonor = donors.length === 1 && donors[0].commitment === onchain.donorCommitment;
  checks.push({ name: "exactly one donor, matching on-chain", ok: oneDonor });

  // 4. recompute the CAS ranking (gates + integer scoring + tie-break) and compare.
  const recips = Object.values(revealed).filter((e) => e.kind === "recipient");
  let recomputedRanked = [];
  let rankedOk = false;
  let coverageOk = false;
  if (oneDonor && policy) {
    const byId = Object.fromEntries(recips.map((e) => [e.record.id, e]));
    const { ranked } = casRank(
      donors[0].record,
      recips.map((e) => e.record),
      policy,
      onchain.donorCommitment
    );
    recomputedRanked = ranked.map((e) => byId[e.id].commitment);
    rankedOk =
      JSON.stringify(recomputedRanked) === JSON.stringify(onchain.rankedRecipientCommitments);
    const elig = new Set(recomputedRanked);
    const logged = new Set(onchain.rankedRecipientCommitments);
    coverageOk = elig.size === logged.size && [...elig].every((c) => logged.has(c));
  }
  checks.push({ name: "recomputed CAS ranking == on-chain ranked commitments", ok: rankedOk });
  checks.push({ name: "ranked set == eligible revealed recipients (coverage)", ok: coverageOk });

  // 5. ranking hash.
  const recomputedHash = rankingHash(onchain.donorCommitment, recomputedRanked, onchain.policyVersion);
  checks.push({ name: "recomputed ranking hash == on-chain", ok: recomputedHash === onchain.rankingHash });

  return { allOk: checks.every((c) => c.ok), checks, recomputedHash };
}
