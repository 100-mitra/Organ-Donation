# Verifiable Organ Allocation — Phase 1 (walking skeleton)

> A *verifiable-allocation* prototype for deceased-donor kidney matching. An off-chain engine
> ranks candidates by a transparent, deterministic policy; a permissioned smart contract logs every
> decision so anyone with the revealed inputs can **recompute the ranking and confirm it faithfully
> executed the published policy**. See [`CLAUDE.md`](CLAUDE.md) for the full project spec and
> [`docs/decisions.md`](docs/decisions.md) for the design-decision log.

**Phase 1 status:** the thin end-to-end slice is complete — `commit → log → recompute → compare`
runs green across all layers with a *trivial* one-factor ranking (waiting time). The real Composite
Allocation Score is Phase 2. This is intentionally minimal.

## What the loop proves
1. **commit** — each record's salted commitment (`canon-v1`, [`docs/canonicalization.md`](docs/canonicalization.md)) is written on-chain. PII stays off-chain.
2. **log** — the decision (donor commitment, ordered ranked commitments, `rankingHash`, policy version) is logged as a role-gated on-chain event.
3. **recompute** — an auditor independently re-ranks the *revealed* records with the same deterministic engine.
4. **compare** — the recomputed ranking + hash must equal what was logged. A tampered ranking fails (the comparison is not vacuous).

The recompute exists in **two independent implementations** — Python ([`engine/`](engine/)) and
JavaScript ([`web/src/canon.js`](web/src/canon.js)) — and both reproduce the same frozen commitment
vectors ([`engine/tests/vectors/commitment_vectors.json`](engine/tests/vectors/commitment_vectors.json)).

## Prerequisites
- Python 3.11+ (verified on 3.14), Node 18+ (verified on 24).

## Install
```bash
pip install -r requirements.txt
( cd contracts && npm install )
( cd web && npm install )
```

## Run the stack (4 terminals, or background)
```bash
# 1) local chain
cd contracts && npx hardhat node

# 2) deploy AuditLedger (writes deployments/localhost.json that the API reads)
cd contracts && npx hardhat run scripts/deploy.js --network localhost

# 3) API  (port 8010; the web app defaults to this — override with VITE_API_URL)
python -m uvicorn api.main:app --host 127.0.0.1 --port 8010

# 4) web UI
cd web && npm run dev        # open the printed URL, click Register -> Match -> Verify
```

## Verify the loop is green (with the stack running)
```bash
bash scripts/check_e2e.sh        # Python recompute + the exact browser verify path (Node)
```

## Tests
```bash
python -m pytest engine api -q          # engine + API unit tests
( cd contracts && npx hardhat test )    # AuditLedger role-gating + events
( cd web && npm test )                  # canon-v1 JS port reproduces the frozen vectors
```

## Scope guardrails
Trivial ranking only; `AuditLedger` is minimal; the off-chain store is in-memory and `/reveal` is
open — these harden in later phases. Nothing here is pulled from [`docs/LATER.md`](docs/LATER.md).
