import { describe, it, expect } from "vitest";
import { rankRecipients, verifyDecision } from "./verify.js";
import { commit, rankingHash } from "./canon.js";

describe("trivial ranking JS port", () => {
  it("ranks by waiting_days desc, id tiebreak (matches engine/scoring.py)", () => {
    const recs = [
      { id: "R1", waiting_days: 1200 },
      { id: "R2", waiting_days: 1800 },
      { id: "R4", waiting_days: 1800 },
      { id: "R5", waiting_days: 300 },
    ];
    expect(rankRecipients(recs).map((r) => r.id)).toEqual(["R2", "R4", "R1", "R5"]);
  });
});

describe("verifyDecision", () => {
  const policy = "skeleton-waiting-time-v0";
  // Build a tiny consistent fixture entirely in JS.
  const donorRec = { id: "D1", abo: "O" };
  const r1 = { id: "R1", waiting_days: 1000 };
  const r2 = { id: "R2", waiting_days: 2000 };
  const revealed = {
    D1: { record: donorRec, salt: "00", commitment: commit(donorRec, "00"), kind: "donor" },
    R1: { record: r1, salt: "01", commitment: commit(r1, "01"), kind: "recipient" },
    R2: { record: r2, salt: "02", commitment: commit(r2, "02"), kind: "recipient" },
  };
  // Correct ranking: R2 (2000) before R1 (1000).
  const ranked = [revealed.R2.commitment, revealed.R1.commitment];
  const registered = Object.values(revealed).map((e) => e.commitment);
  const onchain = {
    donorCommitment: revealed.D1.commitment,
    policyVersion: policy,
    rankedRecipientCommitments: ranked,
    rankingHash: rankingHash(revealed.D1.commitment, ranked, policy),
  };

  it("accepts a faithful decision", () => {
    const res = verifyDecision(onchain, revealed, registered);
    expect(res.allOk).toBe(true);
  });

  it("rejects a tampered ranking (swapped order)", () => {
    const tampered = { ...onchain, rankedRecipientCommitments: [ranked[1], ranked[0]] };
    const res = verifyDecision(tampered, revealed, registered);
    expect(res.allOk).toBe(false);
  });

  it("rejects a tampered ranking hash", () => {
    const tampered = { ...onchain, rankingHash: "0x" + "00".repeat(32) };
    const res = verifyDecision(tampered, revealed, registered);
    expect(res.allOk).toBe(false);
  });

  it("rejects when a decision commitment was never registered (binding, D-013)", () => {
    // ISOLATES THE BINDING: ranking still recomputes correctly, but R1's commitment
    // is absent from the on-chain Registered set -> must reject.
    const regMissing = registered.filter((c) => c !== revealed.R1.commitment);
    const res = verifyDecision(onchain, revealed, regMissing);
    expect(res.allOk).toBe(false);
    const binding = res.checks.find((c) => c.name.startsWith("revealed R1"));
    const ranking = res.checks.find((c) => c.name.startsWith("recomputed ranking =="));
    expect(binding.ok).toBe(false); // binding caught it
    expect(ranking.ok).toBe(true); // ranking alone would have passed
  });

  it("rejects a substituted unregistered record", () => {
    const fake = { id: "R1", waiting_days: 9999 };
    const mutated = {
      ...revealed,
      R1: { record: fake, salt: "01", commitment: commit(fake, "01"), kind: "recipient" },
    };
    const res = verifyDecision(onchain, mutated, registered);
    expect(res.allOk).toBe(false);
  });

  it("rejects a recipient hidden under an unknown kind (D-015)", () => {
    // R1 registered + revealed but tagged "ghost" and dropped from the ranking.
    const mutated = { ...revealed, R1: { ...revealed.R1, kind: "ghost" } };
    const ranked = [revealed.R2.commitment];
    const tampered = {
      ...onchain,
      rankedRecipientCommitments: ranked,
      rankingHash: rankingHash(revealed.D1.commitment, ranked, policy),
    };
    const res = verifyDecision(tampered, mutated, registered);
    expect(res.allOk).toBe(false);
    expect(res.checks.find((c) => c.name.includes("kinds are recognized")).ok).toBe(false);
  });

  it("rejects a recipient relabeled as a second donor", () => {
    const mutated = { ...revealed, R1: { ...revealed.R1, kind: "donor" } };
    const ranked = [revealed.R2.commitment];
    const tampered = {
      ...onchain,
      rankedRecipientCommitments: ranked,
      rankingHash: rankingHash(revealed.D1.commitment, ranked, policy),
    };
    const res = verifyDecision(tampered, mutated, registered);
    expect(res.allOk).toBe(false);
    expect(res.checks.find((c) => c.name.includes("exactly one donor")).ok).toBe(false);
  });
});
