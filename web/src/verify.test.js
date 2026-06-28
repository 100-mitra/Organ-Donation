import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { commit, rankingHash } from "./canon.js";
import { rank } from "./cas.js";
import { verifyDecision } from "./verify.js";

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
  const seed = donorEntry.commitment;
  const { ranked } = rank(DONOR, RECIPS, P, seed);
  const rankedCommitments = ranked.map((e) => byId[e.id].commitment);
  const onchain = {
    donorCommitment: donorEntry.commitment,
    policyVersion: VERSION,
    rankedRecipientCommitments: rankedCommitments,
    rankingHash: rankingHash(donorEntry.commitment, rankedCommitments, VERSION),
  };
  const registered = Object.values(revealed).map((e) => e.commitment);
  return { onchain, revealed, registered, rankedIds: ranked.map((e) => e.id) };
}

describe("verifyDecision (CAS)", () => {
  it("accepts a faithful CAS decision", () => {
    const { onchain, revealed, registered } = build();
    expect(verifyDecision(onchain, revealed, registered, P).allOk).toBe(true);
  });

  it("excludes gated recipients (R4 crossmatch, R5 sanity)", () => {
    expect(new Set(build().rankedIds)).toEqual(new Set(["R1", "R2", "R3"]));
  });

  it("rejects a reordered ranking", () => {
    const { onchain, revealed, registered } = build();
    const rc = [...onchain.rankedRecipientCommitments];
    [rc[0], rc[1]] = [rc[1], rc[0]];
    const tampered = { ...onchain, rankedRecipientCommitments: rc, rankingHash: rankingHash(onchain.donorCommitment, rc, VERSION) };
    expect(verifyDecision(tampered, revealed, registered, P).allOk).toBe(false);
  });

  it("rejects including an ineligible (gated) recipient", () => {
    const { onchain, revealed, registered } = build();
    const rc = [...onchain.rankedRecipientCommitments, revealed.R4.commitment];
    const tampered = { ...onchain, rankedRecipientCommitments: rc, rankingHash: rankingHash(onchain.donorCommitment, rc, VERSION) };
    expect(verifyDecision(tampered, revealed, registered, P).allOk).toBe(false);
  });

  it("rejects an unregistered record (D-013 binding)", () => {
    const { onchain, revealed, registered } = build();
    const missing = registered.filter((c) => c !== onchain.rankedRecipientCommitments[0]);
    expect(verifyDecision(onchain, revealed, missing, P).allOk).toBe(false);
  });

  it("rejects a recipient hidden under an unknown kind (D-015)", () => {
    const { onchain, revealed, registered } = build();
    const mut = { ...revealed, R1: { ...revealed.R1, kind: "ghost" } };
    const res = verifyDecision(onchain, mut, registered, P);
    expect(res.allOk).toBe(false);
    expect(res.checks.find((c) => c.name.includes("kinds are recognized")).ok).toBe(false);
  });
});
