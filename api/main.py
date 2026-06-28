"""FastAPI glue (Phase 3: real ledger + encrypted store).

  register -> commit on-chain (recipient/donor)
  match    -> CAS rank over the full active pool + log a pool-complete decision
  erase    -> destroy the off-chain salt+record + mark erased on-chain (§14)
  audit / reveal / commitments / registrations / policy -> what an auditor
            recomputes from and reconstructs the active recipient set with.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.chain import Chain
from api.store import EncryptedStore
from engine.decision import build_decision
from engine.demo_pool import DONOR, RECIPIENTS
from engine.policy import load_policy
from engine.scoring import POLICY_VERSION, rank

app = FastAPI(title="Organ Donation — Audit API (Phase 3 ledger)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

store = EncryptedStore()
_chain: Chain | None = None


def chain() -> Chain:
    global _chain
    if _chain is None:
        _chain = Chain()
    return _chain


def require_auth(authorization: str | None = Header(default=None)) -> None:
    """Access control for PII disclosure (/reveal) and allocator writes. Records +
    salts genuinely must reach an *authorized* auditor for recompute (CLAUDE.md §10,
    D-003), so this is an intentional, gated disclosure — never public in production.
    Demo mode (ALLOCATOR_TOKEN unset) runs open on SYNTHETIC data; set the token to
    require `Authorization: Bearer <token>`. See docs/threat-model.md (D-022)."""
    token = os.environ.get("ALLOCATOR_TOKEN")
    if not token:
        return  # demo mode — open (synthetic data only)
    if authorization != f"Bearer {token}":
        raise HTTPException(401, "missing or invalid allocator token")


AUTH = [Depends(require_auth)]


def _sorted_pool(commitments: list[str]) -> list[str]:
    """Strictly ascending by uint256 — matches the contract's pool ordering."""
    return sorted(commitments, key=lambda c: int(c, 16))


class RegisterBody(BaseModel):
    record: dict[str, Any]
    kind: str = "recipient"


@app.get("/health")
def health() -> dict:
    info: dict[str, Any] = {"ok": True, "registered": len(store.reveal()),
                            "auth_enabled": bool(os.environ.get("ALLOCATOR_TOKEN"))}
    try:
        c = chain()
        info["chain_connected"] = c.is_connected()
        info["allocator"] = c.allocator
        info["contract"] = c.address
    except Exception as exc:
        info["chain_connected"] = False
        info["chain_error"] = str(exc)
    return info


@app.post("/register", dependencies=AUTH)
def register(body: RegisterBody) -> dict:
    if body.kind not in ("recipient", "donor"):
        raise HTTPException(400, "kind must be 'recipient' or 'donor'")
    entry = store.add(body.record, body.kind)
    tx = (chain().register_recipient if body.kind == "recipient" else chain().register_donor)(
        entry["commitment"]
    )
    return {"id": entry["id"], "kind": body.kind, "commitment": entry["commitment"], "tx": tx}


@app.post("/seed", dependencies=AUTH)
def seed() -> dict:
    # Reset the on-chain active recipient set (erase any leftovers) so the next
    # match's pool equals exactly this seed's pool. Old decisions still verify —
    # the auditor reconstructs the active set as-of each decision's block.
    reset = chain().active_recipient_commitments()
    for c in reset:
        chain().erase_recipient(c)
    store.clear()
    out = []
    for rec in RECIPIENTS:
        e = store.add(rec, "recipient")
        chain().register_recipient(e["commitment"])
        out.append({"id": rec["id"], "commitment": e["commitment"]})
    d = store.add(DONOR, "donor")
    chain().register_donor(d["commitment"])
    return {"donor": {"id": DONOR["id"], "commitment": d["commitment"]},
            "recipients": out, "reset_erased": len(reset)}


@app.post("/match", dependencies=AUTH)
def match() -> dict:
    recips = store.recipients()
    if not recips:
        raise HTTPException(400, "no recipients registered — POST /seed first")
    donor = store.get(DONOR["id"])
    if donor is None:
        raise HTTPException(400, "donor not registered — POST /seed first")

    policy = load_policy(POLICY_VERSION)
    seed_hex = donor["commitment"]  # tie-break seed
    by_id = {e["record"]["id"]: e for e in recips}
    pool = _sorted_pool([e["commitment"] for e in recips])  # full active pool
    ranked_eligible, evaluated = rank(
        donor["record"], [e["record"] for e in recips], policy, seed_hex
    )
    ranked_ids = [e["id"] for e in ranked_eligible]
    ranked_commitments = [by_id[rid]["commitment"] for rid in ranked_ids]

    decision = build_decision(donor["commitment"], pool, ranked_commitments, POLICY_VERSION)
    logged = chain().log_decision(
        donor["commitment"], pool, ranked_commitments, decision["ranking_hash"], POLICY_VERSION
    )
    return {
        "decisionId": logged["decisionId"], "tx": logged["tx"], "policyVersion": POLICY_VERSION,
        "donorCommitment": donor["commitment"], "candidatePool": pool,
        "rankedRecipientIds": ranked_ids, "rankedRecipientCommitments": ranked_commitments,
        "rankingHash": decision["ranking_hash"], "explanations": evaluated,
    }


@app.post("/erase/{rid}", dependencies=AUTH)
def erase(rid: str) -> dict:
    """Destroy the off-chain salt + record, then mark erased on-chain (§14)."""
    entry = store.get(rid)
    if entry is None:
        raise HTTPException(404, f"{rid} not found or already erased")
    if entry["kind"] != "recipient":
        raise HTTPException(400, "only recipient commitments are erasable on-chain")
    commitment = store.erase(rid)
    tx = chain().erase_recipient(commitment)
    return {"id": rid, "erased": True, "commitment": commitment, "tx": tx}


@app.get("/audit")
def audit() -> dict:
    return {"decisions": chain().read_decisions()}


@app.get("/commitments")
def commitments() -> dict:
    """All registered commitments — for the binding check (D-013)."""
    return {"registered": chain().read_commitments()}


@app.get("/registrations")
def registrations() -> dict:
    """Registration + erasure events (with block numbers) so a verifier can
    reconstruct the active recipient set and confirm pool completeness (D-015)."""
    return {"registrations": chain().read_registrations(), "erasures": chain().read_erasures()}


@app.get("/policy")
def policy() -> dict:
    return load_policy(POLICY_VERSION)


@app.get("/reveal", dependencies=AUTH)
def reveal() -> dict:
    """Records + salts an auditor recomputes from (erased records are absent)."""
    return {"revealed": store.reveal(), "policyVersion": POLICY_VERSION}
