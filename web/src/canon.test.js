// RULE-2 TEST: the JS canon-v1 port must reproduce the SAME frozen vectors the
// Python engine produces. Reads the very same vectors file as the pytest suite.
// If this fails, the fix goes in the canon-v1 spec, not in one language.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { canonicalJson, commit, keccak256Bytes, CANONICALIZATION_VERSION } from "./canon.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const vectorsPath = path.resolve(here, "../../engine/tests/vectors/commitment_vectors.json");
const V = JSON.parse(readFileSync(vectorsPath, "utf-8"));

describe("canon-v1 JS port reproduces the frozen Python vectors", () => {
  it("canonicalization version matches", () => {
    expect(CANONICALIZATION_VERSION).toBe(V.canonicalization_version);
  });

  it("keccak256 is the Ethereum variant (empty-input vector)", () => {
    expect(keccak256Bytes(new Uint8Array(0))).toBe(V.keccak256_empty);
  });

  for (const vec of V.vectors) {
    it(`canonical_json matches: ${vec.name}`, () => {
      expect(canonicalJson(vec.record)).toBe(vec.canonical_json);
    });
    it(`commitment matches: ${vec.name}`, () => {
      expect(commit(vec.record, vec.salt)).toBe(vec.commitment);
    });
  }
});
