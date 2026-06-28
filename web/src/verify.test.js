import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { commit, rankingHash } from "./canon.js";
import { rank } from "./cas.js";
import { verifyDecision, activeRecipientSet } from "./verify.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const P = JSON.parse(readFileSync(path.resolve(here, "../../docs/policy/kidney_v1.json"), "utf-8"));
const VERSION = "kidney_v1";
const SALT = "00".repeat(16);

const DONOR = {
  id: "D1", abo: "O", hla: { A: [1, 2], B: [7, 8], DR: [4, 15] },
  age: 35, region: "TN", recovered_at_epoch_day: 20000,
};

function recip(id, o = {}) {
  return {
    id, abo: "O", hla: { A: [1, 2], B: [7, 8], DR: [4, 15] }, age: 45,
    unacceptable_antigens: [], cpra: 0, dialysis_start_epoch_day: 16000,
    prior_living_donor: false, region: "TN", urgent: false, ...o,
  };
}

const RECIPS = [
  recip("R1", { cpra: 10, dialysis_start_epoch_day: 13000 }),
  recip("R2", { abo: "A", age: 12, dialysis_start_epoch_day: 18500 }),
  recip("R3", { abo: "B", cpra: 98, prior_living_donor: true, dialysis_start_epoch_day: 17000 }),
  recip("R4", { unacceptable_antigens: [7] }), // gated: crossmatch
  recip("R5", { age: 95 }), // gated: sanity
];

function build() {
  const donorEntry = { record: DONOR, salt: SALT, commitment: commit(DONOR, SALT), kind: "donor" };
  const revealed = { D1: donorEntry };
  const byId = {};
  for (const r of RECIPS) {
    const e = { record: r, salt: SALT, commitment: commit(r, SALT), kind: "recipient" };
    revealed[r.id] = e;
    byId[r.id] = e;
  }
  const pool = RECIPS.map((r) => byId[r.id].commitment).sort((a, b) => (BigInt(a) < BigInt(b) ? -1 : 1));
  const seed = donorEntry.commitment;
  const { ranked } = rank(DONOR, RECIPS, P, seed);
  const rankedCommitments = ranked.map((e) => byId[e.id].commitment);
  const onchain = {
    donorCommitment: donorEntry.commitment, policyVersion: VERSION,
    candidatePool: pool, rankedRecipientCommitments: rankedCommitments,
    rankingHash: rankingHash(donorEntry.commitment, pool, rankedCommitments, VERSION),
    block: 10,
  };
  const registrations = RECIPS.map((r, i) => ({ commitment: byId[r.id].commitment, kind: 1, block: i + 1 }));
  registrations.push({ commitment: donorEntry.commitment, kind: 2, block: 6 });
  const registered = Object.values(revealed).map((e) => e.commitment);
  return { onchain, revealed, registered, registrations, erasures: [] };
}

describe("activeRecipientSet (block-aware)", () => {
  it("includes recipients registered by the block, minus erasures", () => {
    const regs = [
      { commitment: "0xaa", kind: 1, block: 1 },
      { commitment: "0xbb", kind: 1, block: 2 },
      { commitment: "0xdd", kind: 2, block: 3 },
    ];
    const eras = [{ commitment: "0xaa", block: 5 }];
    expect([...activeRecipientSet(regs, eras, 4)].sort()).toEqual(["0xaa", "0xbb"]);
    expect([...activeRecipientSet(regs, eras, 5)]).toEqual(["0xbb"]);
  });
});

describe("verifyDecision (Phase 3, CAS + pool completeness)", () => {
  it("accepts a faithful decision", () => {
    const { onchain, revealed, registered, registrations, erasures } = build();
    expect(verifyDecision(onchain, revealed, registered, P, registrations, erasures).allOk).toBe(true);
  });

  it("REJECTS subset-drop: a registered recipient dropped from pool/ranking/reveal (D-015)", () => {
    const { onchain, revealed, registered, registrations, erasures } = build();
    const r1c = revealed.R1.commitment;
    delete revealed.R1;
    onchain.candidatePool = onchain.candidatePool.filter((c) => c !== r1c);
    onchain.rankedRecipientCommitments = onchain.rankedRecipientCommitments.filter((c) => c !== r1c);
    onchain.rankingHash = rankingHash(onchain.donorCommitment, onchain.candidatePool, onchain.rankedRecipientCommitments, VERSION);
    const res = verifyDecision(onchain, revealed, registered, P, registrations, erasures);
    expect(res.allOk).toBe(false);
    expect(res.checks.find((c) => c.name.includes("completeness")).ok).toBe(false);
  });

  it("rejects revealing a set different from the pool", () => {
    const { onchain, revealed, registered, registrations, erasures } = build();
    delete revealed.R2;
    const res = verifyDecision(onchain, revealed, registered, P, registrations, erasures);
    expect(res.allOk).toBe(false);
    expect(res.checks.find((c) => c.name.includes("revealed recipients == candidate pool")).ok).toBe(false);
  });

  it("rejects a reordered ranking", () => {
    const { onchain, revealed, registered, registrations, erasures } = build();
    const rc = [...onchain.rankedRecipientCommitments];
    [rc[0], rc[1]] = [rc[1], rc[0]];
    onchain.rankedRecipientCommitments = rc;
    onchain.rankingHash = rankingHash(onchain.donorCommitment, onchain.candidatePool, rc, VERSION);
    expect(verifyDecision(onchain, revealed, registered, P, registrations, erasures).allOk).toBe(false);
  });

  it("rejects an unregistered record (binding)", () => {
    const { onchain, revealed, registered, registrations, erasures } = build();
    const missing = registered.filter((c) => c !== onchain.rankedRecipientCommitments[0]);
    expect(verifyDecision(onchain, revealed, missing, P, registrations, erasures).allOk).toBe(false);
  });
});
