// canon-v1 — INDEPENDENT JavaScript port of engine/commitments.py.
//
// This is the second implementation the verifiability thesis depends on: the
// browser recomputes commitments + the ranking hash here, with no help from the
// Python engine. It MUST reproduce the frozen vectors in
// engine/tests/vectors/commitment_vectors.json byte-for-byte (proved by
// canon.test.js). Project rule: if JS and Python ever disagree, fix the
// canon-v1 SPEC (docs/canonicalization.md), not one language.

import sha3 from "js-sha3";

// Default-import then read the method — robust across CJS/ESM interop.
const keccakHex = sha3.keccak256; // Ethereum Keccak-256, NOT NIST sha3_256.

export const CANONICALIZATION_VERSION = "canon-v1";

function assertNoFloat(value, path = "$") {
  if (typeof value === "number") {
    if (!Number.isInteger(value)) {
      throw new Error(`float found at ${path}: ${value} (integer-only required)`);
    }
  } else if (Array.isArray(value)) {
    value.forEach((v, i) => assertNoFloat(v, `${path}[${i}]`));
  } else if (value && typeof value === "object") {
    for (const k of Object.keys(value)) assertNoFloat(value[k], `${path}.${k}`);
  }
}

// Recursively rebuild objects with keys in sorted (code-point) order. ASCII-only
// keys (canon-v1 constraint) => JS UTF-16 sort == Python code-point sort.
function sortDeep(value) {
  if (Array.isArray(value)) return value.map(sortDeep);
  if (value && typeof value === "object") {
    const out = {};
    for (const k of Object.keys(value).sort()) out[k] = sortDeep(value[k]);
    return out;
  }
  return value;
}

export function canonicalJson(record) {
  assertNoFloat(record);
  // Default JSON.stringify has no insignificant whitespace and leaves non-ASCII
  // as raw UTF-8 — matching Python json.dumps(separators=(",",":"),
  // ensure_ascii=False).
  return JSON.stringify(sortDeep(record));
}

function hexToBytes(hex) {
  const h = hex.startsWith("0x") ? hex.slice(2) : hex;
  const out = new Uint8Array(h.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(h.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

// keccak256 over raw bytes -> 0x-hex (for the empty-input conformance check).
export function keccak256Bytes(bytes) {
  return "0x" + keccakHex(bytes);
}

// keccak256 over the canon-v1 serialization of an object (no salt).
export function hashCanonical(obj) {
  const msg = new TextEncoder().encode(canonicalJson(obj));
  return "0x" + keccakHex(msg);
}

// commitment = keccak256( utf8(canonical_json(record)) || saltBytes )
export function commit(record, saltHex) {
  const msg = new TextEncoder().encode(canonicalJson(record));
  const salt = hexToBytes(saltHex);
  const combined = new Uint8Array(msg.length + salt.length);
  combined.set(msg, 0);
  combined.set(salt, msg.length);
  return "0x" + keccakHex(combined);
}

// Mirrors engine/decision.py: bind donor + policy + ordered ranked commitments.
export function rankingHash(donorCommitment, rankedRecipientCommitments, policyVersion) {
  return hashCanonical({
    donor_commitment: donorCommitment,
    policy_version: policyVersion,
    ranked_recipient_commitments: rankedRecipientCommitments,
  });
}
