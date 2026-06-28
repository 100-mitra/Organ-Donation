"""web3.py glue to the local Hardhat AuditLedger (Phase 3: real ledger).

The Hardhat node manages the allocator's key (account 0), so transactions are sent
with ``transact({"from": allocator})`` and the node signs. Reads the registration /
erasure / decision events back (with block numbers) so an auditor can reconstruct
the active recipient set and confirm a decision's pool completeness (D-015).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from web3 import Web3

RPC_URL = os.environ.get("RPC_URL", "http://127.0.0.1:8545")
NETWORK = os.environ.get("CHAIN_NETWORK", "localhost")
DEPLOYMENTS_DIR = Path(__file__).resolve().parents[1] / "deployments"

KIND_RECIPIENT = 1
KIND_DONOR = 2


def _to_b32(hexstr: str) -> bytes:
    h = hexstr[2:] if hexstr.startswith("0x") else hexstr
    b = bytes.fromhex(h)
    if len(b) != 32:
        raise ValueError(f"expected 32 bytes, got {len(b)} from {hexstr!r}")
    return b


def _to_0x(b: bytes) -> str:
    return "0x" + bytes(b).hex()


def load_deployment(network: str = NETWORK) -> dict:
    f = DEPLOYMENTS_DIR / f"{network}.json"
    if not f.exists():
        raise FileNotFoundError(
            f"deployment {f} not found — run `npx hardhat run scripts/deploy.js "
            f"--network localhost` against a running node first."
        )
    return json.loads(f.read_text(encoding="utf-8"))


class Chain:
    def __init__(self) -> None:
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        dep = load_deployment()
        self.address = Web3.to_checksum_address(dep["address"])
        self.allocator = Web3.to_checksum_address(dep["allocator"])
        self.contract = self.w3.eth.contract(address=self.address, abi=dep["abi"])

    def is_connected(self) -> bool:
        return self.w3.is_connected()

    def _send(self, fn) -> str:
        tx = fn.transact({"from": self.allocator})
        self.w3.eth.wait_for_transaction_receipt(tx)
        return _to_0x(tx)

    def register_recipient(self, commitment: str) -> str:
        return self._send(self.contract.functions.registerRecipient(_to_b32(commitment)))

    def register_donor(self, commitment: str) -> str:
        return self._send(self.contract.functions.registerDonor(_to_b32(commitment)))

    def erase_recipient(self, commitment: str) -> str:
        return self._send(self.contract.functions.eraseRecipient(_to_b32(commitment)))

    def log_decision(
        self,
        donor_commitment: str,
        candidate_pool: list[str],
        ranked_eligible: list[str],
        ranking_hash: str,
        policy_version: str,
    ) -> dict:
        tx = self.contract.functions.logDecision(
            _to_b32(donor_commitment),
            [_to_b32(c) for c in candidate_pool],
            [_to_b32(c) for c in ranked_eligible],
            _to_b32(ranking_hash),
            policy_version,
        ).transact({"from": self.allocator})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx)
        evts = self.contract.events.DecisionLogged().process_receipt(receipt)
        return {"decisionId": int(evts[0]["args"]["decisionId"]), "tx": _to_0x(tx)}

    def read_registrations(self) -> list[dict]:
        logs = self.contract.events.Registered().get_logs(from_block=0)
        return [
            {"commitment": _to_0x(e["args"]["commitment"]), "kind": int(e["args"]["kind"]),
             "block": int(e["blockNumber"])}
            for e in logs
        ]

    def read_erasures(self) -> list[dict]:
        logs = self.contract.events.Erased().get_logs(from_block=0)
        return [{"commitment": _to_0x(e["args"]["commitment"]), "block": int(e["blockNumber"])}
                for e in logs]

    def read_commitments(self) -> list[str]:
        """All registered commitments (recipients + donors) — for the binding check."""
        return [r["commitment"] for r in self.read_registrations()]

    def read_decisions(self) -> list[dict]:
        logs = self.contract.events.DecisionLogged().get_logs(from_block=0)
        out = []
        for e in logs:
            a = e["args"]
            out.append({
                "decisionId": int(a["decisionId"]),
                "donorCommitment": _to_0x(a["donorCommitment"]),
                "rankingHash": _to_0x(a["rankingHash"]),
                "policyVersion": a["policyVersion"],
                "candidatePool": [_to_0x(x) for x in a["candidatePool"]],
                "rankedRecipientCommitments": [_to_0x(x) for x in a["rankedEligible"]],
                "by": a["by"],
                "block": int(e["blockNumber"]),
            })
        out.sort(key=lambda d: d["decisionId"])
        return out
