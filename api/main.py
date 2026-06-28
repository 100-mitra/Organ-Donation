"""FastAPI glue for the Phase 1 walking skeleton.

Orchestrates the loop the whole project is about:
    register -> commit on-chain   (POST /register, POST /seed)
    match    -> rank + log         (POST /match)
    audit    -> read decisions     (GET  /audit)
    reveal   -> records + salts     (GET  /reveal)   <- what an auditor recomputes from

The chain connection is lazy so the app imports without a running node (unit tests,
/health). Real verification happens off this surface: the browser Verify page (and
scripts/e2e.py) read /audit + /reveal and recompute independently.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.chain import Chain
from api.store import OffChainStore
from engine.decision import build_decision
from engine.scoring import POLICY_VERSION, rank_recipients
from engine.skeleton_fixtures import DONOR, RECIPIENTS

app = FastAPI(title="Organ Donation — Audit API (Phase 1 skeleton)")

# Local dev only: the Vite web app calls this from another origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store = OffChainStore()
_chain: Chain | None = None


def chain() -> Chain:
    global _chain
    if _chain is None:
        _chain = Chain()
    return _chain


class RegisterBody(BaseModel):
    record: dict[str, Any]
    kind: str = "recipient"  # "recipient" | "donor"


@app.get("/health")
def health() -> dict:
    info: dict[str, Any] = {"ok": True, "registered": len(store.reveal())}
    try:
        c = chain()
        info["chain_connected"] = c.is_connected()
        info["allocator"] = c.allocator
        info["contract"] = c.address
    except Exception as exc:  # node down / not deployed yet — report, don't 500
        info["chain_connected"] = False
        info["chain_error"] = str(exc)
    return info


@app.post("/register")
def register(body: RegisterBody) -> dict:
    if body.kind not in ("recipient", "donor"):
        raise HTTPException(400, "kind must be 'recipient' or 'donor'")
    entry = store.add(body.record, body.kind)
    tx = chain().register_commitment(entry["commitment"])
    return {
        "id": body.record["id"],
        "kind": body.kind,
        "commitment": entry["commitment"],
        "tx": tx,
    }


@app.post("/seed")
def seed() -> dict:
    """Register the fixed skeleton pool (5 recipients + 1 donor) in one click."""
    store.clear()
    out = []
    for rec in RECIPIENTS:
        e = store.add(rec, "recipient")
        chain().register_commitment(e["commitment"])
        out.append({"id": rec["id"], "commitment": e["commitment"]})
    d = store.add(DONOR, "donor")
    chain().register_commitment(d["commitment"])
    return {
        "donor": {"id": DONOR["id"], "commitment": d["commitment"]},
        "recipients": out,
    }


@app.post("/match")
def match() -> dict:
    """Rank the registered recipients (trivial policy) and log the decision."""
    recips = store.recipients()
    if not recips:
        raise HTTPException(400, "no recipients registered — POST /seed first")
    donor = store.get(DONOR["id"])
    if donor is None:
        raise HTTPException(400, "donor not registered — POST /seed first")

    ranked_records = rank_recipients([e["record"] for e in recips])
    by_id = {e["record"]["id"]: e for e in recips}
    ranked_ids = [r["id"] for r in ranked_records]
    ranked_commitments = [by_id[rid]["commitment"] for rid in ranked_ids]

    decision = build_decision(
        donor["commitment"], ranked_commitments, POLICY_VERSION
    )
    logged = chain().log_decision(
        donor["commitment"],
        ranked_commitments,
        decision["ranking_hash"],
        POLICY_VERSION,
    )
    return {
        "decisionId": logged["decisionId"],
        "tx": logged["tx"],
        "policyVersion": POLICY_VERSION,
        "donorCommitment": donor["commitment"],
        "rankedRecipientIds": ranked_ids,
        "rankedRecipientCommitments": ranked_commitments,
        "rankingHash": decision["ranking_hash"],
    }


@app.get("/audit")
def audit() -> dict:
    return {"decisions": chain().read_decisions()}


@app.get("/commitments")
def commitments() -> dict:
    """The on-chain set of Registered commitments. A verifier binds the revealed
    records against this set so a substituted/fabricated pool is rejected (D-013)."""
    return {"registered": chain().read_commitments()}


@app.get("/reveal")
def reveal() -> dict:
    """Records + salts + commitments — the inputs an auditor recomputes from.

    In production this is access-controlled (the privacy/erasure boundary, §14);
    in the skeleton it is open so the public Verify page can demonstrate recompute.
    """
    return {"revealed": store.reveal(), "policyVersion": POLICY_VERSION}
