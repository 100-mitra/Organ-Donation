# Threat model

What the system's tamper-evidence **does** and **does not** guarantee (CLAUDE.md §2, §10).
The chain proves the *computation* was faithful to the *committed inputs* — not that the inputs
are *true* (the oracle problem). State the boundary plainly; owning it is the contribution.

## Attacks STOPPED (and where)
| Attack | Stopped by |
|---|---|
| Tampering with a logged ranking after the fact | append-only on-chain `DecisionLogged` + `rankingHash` recompute |
| Swapping the rules / policy version post-hoc | `policyVersion` logged per decision; verifier re-applies the matching `kidney_v1.json` |
| Substituting / fabricating a record (reveal data never committed) | binding: each revealed record must open to a commitment that was `Registered` on-chain (D-013) |
| Hiding a recipient under a bogus `kind`, or a second donor | known-kind + exactly-one-donor checks (D-015) |
| **Silent queue-jumping by dropping a registered candidate (subset-drop)** | the contract requires `candidatePool == active recipient set` (complete, sorted, all-active); the verifier independently reconstructs the active set from the event log and confirms `pool == active` and `revealed == pool` (D-015) |
| Reordering / mis-ranking the eligible pool | independent CAS recompute (integer, deterministic) + `rankingHash` over donor+policy+pool+ranking |
| A non-allocator writing to the ledger | `onlyAllocator` role gate on every state-changing function |

## Attacks NOT stopped (the oracle boundary)
- **False input data.** A corrupt allocator entering a fabricated dialysis date / CPRA / HLA produces a
  commitment that faithfully reflects the lie; the ranking and verification all pass. The ledger makes
  this **attributable** (who attested what, when) but cannot make it **true**. Mitigation is
  *organizational* (multi-party attestation by independent hospitals/NOTTO), not cryptographic.
- **Never-registering a candidate.** Subset-drop covers dropping a *registered* candidate from a
  decision. An allocator who simply never registers someone is the same oracle problem above.
- **Allocator key compromise.** The integrity model rests on the allocator key (node-managed in the
  prototype). Custody / rotation / compromise is a governance concern (LATER.md), not yet hardened.

## Privacy boundaries
- **PII never on-chain.** Only salted commitments + decision events. Off-chain records are encrypted at
  rest (AES-256-GCM, `api/store.py`).
- **`/reveal` is an intentional, ACCESS-CONTROLLED disclosure (D-022).** The verifiable-recompute model
  *requires* an authorized auditor to obtain records + salts to recompute; that is the endpoint's
  purpose, not a leak. It is gated by an allocator/auditor token (`ALLOCATOR_TOKEN`) and **must never be
  public in production**; the prototype runs it open *only* on **synthetic data** (CLAUDE.md §4) for the
  demo. CORS is wildcard in the local prototype and must be narrowed in deployment.
- **Erasure (§14).** `erase()` destroys the per-record salt + ciphertext; the on-chain commitment
  remains (append-only) but is now **unlinkable**. *Documented tension (D-005):* erasing a record makes
  its past decisions unverifiable — auditable XOR erasable, per record.
