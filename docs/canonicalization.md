# Canonicalization spec — `canon-v1`

> **Why this document exists.** The whole project rests on one promise: an *independent*
> party can recompute an allocation and get a bit-for-bit identical result. That only works
> if everyone serializes a record to the *same bytes* before hashing. The Python engine
> (`engine/commitments.py`) and the JavaScript browser verifier (Phase 1) are two independent
> implementations — they MUST agree. This spec pins the rules; the frozen vectors in
> [`../engine/tests/vectors/commitment_vectors.json`](../engine/tests/vectors/commitment_vectors.json)
> are the executable contract that proves they agree.

## Scope
Defines how a **record** (a JSON object) is turned into:
1. its **canonical JSON string**, and
2. its **salted commitment** (the on-chain `bytes32`).

## Hard constraints on records
- **Integer / fixed-point values only.** No floats — anywhere, at any depth. Floats are
  *rejected* (raise), not coerced. Float text formatting differs across languages/platforms and
  would silently break recompute. Money/ratios are represented as scaled integers (e.g. CPRA as
  an integer 0–100, points as integers).
- **Integers MUST be within `[-(2^53-1), 2^53-1]`** (i.e. `±9007199254740991`,
  `Number.MAX_SAFE_INTEGER`). Beyond this a JS `number` is a double that silently loses precision
  (and may switch to exponent form), so it would diverge from Python's exact `int`. Both ports
  reject out-of-range integers. Need a bigger value? Encode it as a **string**.
- **Float *type* vs integer *value* (the `2.0`/`2` rule).** Python additionally rejects the float
  *type* outright (so `2.0` raises), as producer-side discipline. JavaScript cannot distinguish
  `2.0` from `2` at runtime, so it validates by *value*: `Number.isSafeInteger` accepts integer
  values and rejects fractional ones. This is an input-validation asymmetry only — **there is no
  output divergence**: every value both ports accept canonicalizes to identical bytes (a fractional
  value is rejected by both; an integer value serializes the same in both). Producers must supply
  integer types; the engine (Python) is the stricter gate and is the only thing that mints
  commitments.
- **Object keys are strings**, and in `canon-v1` are restricted to **ASCII**. (Rationale:
  Python sorts keys by Unicode code point; JS `Array.prototype.sort` sorts by UTF-16 code unit.
  These agree for all ASCII keys, so restricting keys to ASCII removes the one place the two
  ecosystems could diverge. Values may contain non-ASCII; keys may not.)
- Allowed value types: object, array, string, integer, boolean, `null`.

## Canonical JSON rules
1. **Sort object keys** ascending by Unicode code point (ASCII-only keys ⇒ plain byte order).
2. **No insignificant whitespace** — element separator `,`, key/value separator `:`.
3. **Arrays preserve order.** Order is *significant*. If a list is semantically a set (e.g. HLA
   antigens), it must be normalized (sorted/deduped) by the engine *before* canonicalization —
   canonicalization never reorders array elements.
4. **Strings** are emitted as raw UTF-8 (no `\uXXXX` escaping of non-ASCII), matching JS
   `JSON.stringify`. Only the JSON-mandatory escapes (`"`, `\`, control chars) are applied.
5. **Integers** are bare decimal, no leading zeros, `-` only for negatives, and within the safe
   range above (no exponent form ever).
6. **Booleans / null** → `true` / `false` / `null`.
7. Output is then **UTF-8 encoded** to bytes.

Reference impl: `engine.commitments.canonical_json` —
`json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` after
`_assert_canon_valid` (rejects floats, out-of-range integers, and non-string keys). The JS twin is
`web/src/canon.js` (`assertCanonValid` + `JSON.stringify(sortDeep(...))`).

> Equivalent to [RFC 8785 JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785)
> *restricted to the integer-only subset* (we deliberately exclude RFC 8785's float/ECMAScript
> number formatting, since we forbid floats outright — removing the spec's hardest, most
> bug-prone clause).

## Commitment rule
```
salt        : per-record random bytes, stored OFF-CHAIN, hex-encoded
message     = utf8( canonical_json(record) )  ||  bytes_from_hex(salt)
commitment  = keccak256( message )            # Ethereum Keccak-256, NOT NIST SHA3-256
on-chain    = "0x" + hex(commitment)          # 32-byte bytes32
```
- `keccak256` is the **Ethereum variant**. Sanity check: `keccak256("") =
  c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470` (NIST SHA3-256 differs).
- The **salt** is the privacy + erasure lever (CLAUDE.md §14): it prevents on-chain enumeration
  of patients, and destroying it makes the commitment permanently unlinkable.
  - ⚠️ **Documented tension (decisions.md D-004):** destroying a salt to honour erasure also makes
    every past decision that referenced that record *unverifiable*. Auditable XOR erasable.

## Versioning
- This algorithm is `canon-v1` (`CANONICALIZATION_VERSION` in `engine/commitments.py`).
- Any change to the rules above is a **new version** and requires regenerating the frozen vectors
  in a deliberate, reviewed commit. The version travels with the vectors so a verifier always
  knows which rules produced a given commitment.

## Conformance
An implementation conforms to `canon-v1` iff it reproduces **every** value in
`commitment_vectors.json`: `keccak256_empty`, and for each vector its `canonical_json` and
`commitment`. Python conformance is enforced by `engine/tests/test_commitments.py`; JS
conformance will be enforced by the Verify page's tests in Phase 1.
