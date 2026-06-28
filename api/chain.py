"""web3.py glue to the local Hardhat AuditLedger.

The Hardhat node manages the allocator's key (account 0), so we send transactions
with ``transact({"from": allocator})`` and the node signs — no local key handling
in the skeleton. Reads decisions back from on-chain events.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from web3 import Web3

RPC_URL = os.environ.get("RPC_URL", "http://127.0.0.1:8545")
NETWORK = os.environ.get("CHAIN_NETWORK", "localhost")
DEPLOYMENTS_DIR = Path(__file__).resolve().parents[1] / "deployments"


def _to_b32(hexstr: str) -> bytes:
    """0x-hex commitment string -> 32 raw bytes for an on-chain bytes32 arg."""
    h = hexstr[2:] if hexstr.startswith("0x") else hexstr
    b = bytes.fromhex(h)
    if len(b) != 32:
        raise ValueError(f"expected 32 bytes, got {len(b)} from {hexstr!r}")
    return b


def _to_0x(b: bytes) -> str:
    """Raw bytes from an event -> lowercase 0x-hex (matches engine output)."""
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

    def register_commitment(self, commitment_hex: str) -> str:
        tx = self.contract.functions.registerCommitment(
            _to_b32(commitment_hex)
        ).transact({"from": self.allocator})
        self.w3.eth.wait_for_transaction_receipt(tx)
        return _to_0x(tx)

    def log_decision(
        self,
        donor_commitment: str,
        ranked_commitments: list[str],
        ranking_hash: str,
        policy_version: str,
    ) -> dict:
        tx = self.contract.functions.logDecision(
            _to_b32(donor_commitment),
            [_to_b32(c) for c in ranked_commitments],
            _to_b32(ranking_hash),
            policy_version,
        ).transact({"from": self.allocator})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx)
        evts = self.contract.events.DecisionLogged().process_receipt(receipt)
        decision_id = int(evts[0]["args"]["decisionId"])
        return {"decisionId": decision_id, "tx": _to_0x(tx)}

    def read_decisions(self) -> list[dict]:
        logs = self.contract.events.DecisionLogged().get_logs(from_block=0)
        out = []
        for e in logs:
            a = e["args"]
            out.append(
                {
                    "decisionId": int(a["decisionId"]),
                    "donorCommitment": _to_0x(a["donorCommitment"]),
                    "rankingHash": _to_0x(a["rankingHash"]),
                    "policyVersion": a["policyVersion"],
                    "rankedRecipientCommitments": [
                        _to_0x(x) for x in a["rankedRecipientCommitments"]
                    ],
                    "by": a["by"],
                }
            )
        out.sort(key=lambda d: d["decisionId"])
        return out

    def read_commitments(self) -> list[str]:
        """The on-chain set of Registered commitments — the population an auditor
        binds the revealed records against (closes the substitution attack)."""
        logs = self.contract.events.Registered().get_logs(from_block=0)
        return [_to_0x(e["args"]["commitment"]) for e in logs]
