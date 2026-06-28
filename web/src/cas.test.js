// PARITY TEST: the JS CAS scorer must reproduce the SAME frozen ranking vectors
// the Python engine produces. Reads the very same vectors file as the pytest suite.
// If this fails, Python and JS have diverged — fix the spec, not one language.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { rank } from "./cas.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const V = JSON.parse(
  readFileSync(path.resolve(here, "../../engine/tests/vectors/cas_ranking_vectors.json"), "utf-8")
);
const P = JSON.parse(
  readFileSync(path.resolve(here, "../../docs/policy/kidney_v1.json"), "utf-8")
);

function comparable(evaluated) {
  return evaluated.map((e) =>
    e.eligible
      ? {
          id: e.id,
          eligible: true,
          cas: e.cas,
          points: Object.fromEntries(Object.entries(e.breakdown).map(([k, v]) => [k, v.points])),
        }
      : { id: e.id, eligible: false, cas: null, points: null }
  );
}

describe("CAS JS port reproduces the frozen Python ranking vectors", () => {
  for (const c of V.cases) {
    it(`ranking matches: ${c.name}`, () => {
      const { ranked } = rank(c.donor, c.recipients, P, c.decision_seed);
      expect(ranked.map((e) => e.id)).toEqual(c.expected.ranking);
    });
    it(`scored (eligibility + cas + points) matches: ${c.name}`, () => {
      const { evaluated } = rank(c.donor, c.recipients, P, c.decision_seed);
      expect(comparable(evaluated)).toEqual(c.expected.scored);
    });
  }
});
