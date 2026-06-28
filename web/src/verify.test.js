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
  const onchain = {
    donorCommitment: revealed.D1.commitment,
    policyVersion: policy,
    rankedRecipientCommitments: ranked,
    rankingHash: rankingHash(revealed.D1.commitment, ranked, policy),
  };

  it("accepts a faithful decision", () => {
    const res = verifyDecision(onchain, revealed);
    expect(res.allOk).toBe(true);
  });

  it("rejects a tampered ranking (swapped order)", () => {
    const tampered = { ...onchain, rankedRecipientCommitments: [ranked[1], ranked[0]] };
    const res = verifyDecision(tampered, revealed);
    expect(res.allOk).toBe(false);
  });

  it("rejects a tampered ranking hash", () => {
    const tampered = { ...onchain, rankingHash: "0x" + "00".repeat(32) };
    const res = verifyDecision(tampered, revealed);
    expect(res.allOk).toBe(false);
  });
});
