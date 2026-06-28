// PARITY: the JS rankingHash (binds donor + policy + pool + ranking) must
// reproduce the SAME frozen vectors as engine/decision.py. Same file as pytest.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { rankingHash } from "./canon.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const V = JSON.parse(
  readFileSync(path.resolve(here, "../../engine/tests/vectors/decision_hash_vectors.json"), "utf-8")
);

describe("decision ranking_hash JS port reproduces the frozen Python vectors", () => {
  for (const c of V.cases) {
    it(`ranking_hash matches: ${c.name}`, () => {
      expect(
        rankingHash(c.donor_commitment, c.candidate_pool, c.ranked_recipient_commitments, c.policy_version)
      ).toBe(c.ranking_hash);
    });
  }
});
