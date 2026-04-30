"""Tests for the agent-identity loader.

`load_identity_tx_id` is the boot-time read for `/agent-identity`. It
must tolerate a missing or malformed file (Phase 1a doesn't gate on
Arweave anchoring being complete) but must surface the tx id when the
file is well-formed.
"""

from __future__ import annotations

import json
from pathlib import Path

from aegis_monitor.api.identity import load_identity_tx_id


def test_load_identity_tx_id_missing_file(tmp_path: Path) -> None:
    assert load_identity_tx_id(str(tmp_path / "nope.json")) is None


def test_load_identity_tx_id_well_formed(tmp_path: Path) -> None:
    p = tmp_path / "arweave-identity.json"
    p.write_text(
        json.dumps(
            {
                "agent_id": "aegis-monitor-prod",
                "signer_address": "0xabc",
                "arweave_tx_id": "fakeTxId123",
            }
        )
    )
    assert load_identity_tx_id(str(p)) == "fakeTxId123"


def test_load_identity_tx_id_malformed_json(tmp_path: Path) -> None:
    p = tmp_path / "broken.json"
    p.write_text("{ not valid json")
    # Tolerant by design — boot must not crash on a corrupt file.
    assert load_identity_tx_id(str(p)) is None


def test_load_identity_tx_id_missing_field(tmp_path: Path) -> None:
    p = tmp_path / "no-field.json"
    p.write_text(json.dumps({"agent_id": "x"}))
    assert load_identity_tx_id(str(p)) is None


def test_load_identity_tx_id_empty_string(tmp_path: Path) -> None:
    p = tmp_path / "empty.json"
    p.write_text(json.dumps({"arweave_tx_id": ""}))
    # An empty string is a write-mistake, not a real tx id. Treat as missing.
    assert load_identity_tx_id(str(p)) is None
