"""Unit tests for the Pydantic schemas.

These lock in the wire format: address normalization, tx-hash validation,
canonical JSON determinism, and signature-length gate. The canonical JSON
test is the most important one — its stability protects every prior
attestation.
"""

from __future__ import annotations

import json
from datetime import UTC

import pytest
from pydantic import ValidationError

from aegis_monitor.schemas import (
    Attestation,
    AttestationBody,
    FlagResponse,
    MonitorRequest,
    PendingTx,
    RuleHit,
)

# -----------------------------------------------------------------------------
# MonitorRequest
# -----------------------------------------------------------------------------


def test_monitor_request_lowercases_address() -> None:
    req = MonitorRequest(address="0xAbCdEf0123456789abcdef0123456789ABCDEF01")
    assert req.address == "0xabcdef0123456789abcdef0123456789abcdef01"


def test_monitor_request_rejects_bad_address() -> None:
    with pytest.raises(ValidationError):
        MonitorRequest(address="not-an-address")
    with pytest.raises(ValidationError):
        MonitorRequest(address="0x123")


# -----------------------------------------------------------------------------
# PendingTx
# -----------------------------------------------------------------------------


def _valid_pending_tx_kwargs(**overrides: object) -> dict[str, object]:
    base = {
        "tx_hash": "0x" + "ab" * 32,
        "from_address": "0x" + "cd" * 20,
        "to_address": "0x" + "ef" * 20,
        "value_wei": 0,
        "input_data": "0xa9059cbb",
        "gas": 21000,
        "gas_price": 10**9,
        "nonce": 0,
    }
    base.update(overrides)
    return base


def test_pending_tx_accepts_contract_creation() -> None:
    tx = PendingTx(**_valid_pending_tx_kwargs(to_address=None))
    assert tx.to_address is None


def test_pending_tx_rejects_negative_value() -> None:
    with pytest.raises(ValidationError):
        PendingTx(**_valid_pending_tx_kwargs(value_wei=-1))


def test_pending_tx_rejects_non_hex_input() -> None:
    with pytest.raises(ValidationError):
        PendingTx(**_valid_pending_tx_kwargs(input_data="xyz"))


def test_pending_tx_normalizes_case() -> None:
    tx = PendingTx(**_valid_pending_tx_kwargs(
        tx_hash="0x" + "AB" * 32,
        from_address="0x" + "CD" * 20,
    ))
    assert tx.tx_hash == "0x" + "ab" * 32
    assert tx.from_address == "0x" + "cd" * 20


# -----------------------------------------------------------------------------
# RuleHit
# -----------------------------------------------------------------------------


def test_rule_hit_reason_length_bounds() -> None:
    with pytest.raises(ValidationError):
        RuleHit(
            rule_id="t1.approve_to_eoa",
            rule_version="t1-v0.1",
            severity="high",
            reason_human="",
            reason_structured={},
        )
    with pytest.raises(ValidationError):
        RuleHit(
            rule_id="t1.approve_to_eoa",
            rule_version="t1-v0.1",
            severity="high",
            reason_human="x" * 281,
            reason_structured={},
        )


# -----------------------------------------------------------------------------
# AttestationBody — canonical JSON stability
# -----------------------------------------------------------------------------


def _body(**overrides: object) -> AttestationBody:
    base: dict[str, object] = {
        "tx_hash": "0x" + "ab" * 32,
        "monitored_address": "0x" + "cd" * 20,
        "rule_id": "t1.approve_to_eoa",
        "rule_version": "t1-v0.1",
        "severity": "high",
        "reason_human": "Unlimited approval granted to an address with no contract code",
        "reason_structured": {"spender": "0x" + "ef" * 20, "amount_hex": "0xff"},
        "agent_id": "aegis-monitor-01",
        "ts_ms": 1_713_654_321_000,
    }
    base.update(overrides)
    return AttestationBody(**base)


def test_canonical_json_is_sorted_and_compact() -> None:
    canonical = _body().canonical_json()
    as_str = canonical.decode("utf-8")
    # Must be parseable.
    parsed = json.loads(as_str)
    # Fields are sorted alphabetically at every level.
    assert list(parsed.keys()) == sorted(parsed.keys())
    # No whitespace separators.
    assert ", " not in as_str
    assert ": " not in as_str


def test_canonical_json_deterministic_across_reorderings() -> None:
    a = _body()
    # Re-create with fields in a different kwarg order — Pydantic builds the
    # same object, canonical_json must match byte-for-byte.
    b = AttestationBody(
        agent_id=a.agent_id,
        ts_ms=a.ts_ms,
        severity=a.severity,
        reason_structured=a.reason_structured,
        reason_human=a.reason_human,
        rule_version=a.rule_version,
        rule_id=a.rule_id,
        monitored_address=a.monitored_address,
        tx_hash=a.tx_hash,
    )
    assert a.canonical_json() == b.canonical_json()


def test_canonical_json_ascii_utf8_safe() -> None:
    body = _body(reason_human="Unicode edge — émoji-free for now")
    # UTF-8 bytes, not escaped ASCII.
    canonical = body.canonical_json()
    assert b"\xc3\xa9" in canonical  # 'é' encoded as UTF-8


# -----------------------------------------------------------------------------
# Attestation (body + sig)
# -----------------------------------------------------------------------------


def test_attestation_rejects_wrong_sig_length() -> None:
    with pytest.raises(ValidationError):
        Attestation(
            tx_hash="0x" + "ab" * 32,
            monitored_address="0x" + "cd" * 20,
            rule_id="t1.approve_to_eoa",
            rule_version="t1-v0.1",
            severity="high",
            reason_human="…",
            reason_structured={},
            agent_id="aegis-monitor-01",
            ts_ms=1,
            sig="0xdeadbeef",
        )


def test_attestation_accepts_valid_sig() -> None:
    att = Attestation(
        tx_hash="0x" + "ab" * 32,
        monitored_address="0x" + "cd" * 20,
        rule_id="t1.approve_to_eoa",
        rule_version="t1-v0.1",
        severity="high",
        reason_human="test",
        reason_structured={},
        agent_id="aegis-monitor-01",
        ts_ms=1,
        sig="0x" + "ab" * 65,
    )
    assert att.sig.startswith("0x")
    assert len(att.sig) == 132


# -----------------------------------------------------------------------------
# FlagResponse
# -----------------------------------------------------------------------------


def test_flag_response_roundtrip() -> None:
    from datetime import datetime

    att = Attestation(
        tx_hash="0x" + "ab" * 32,
        monitored_address="0x" + "cd" * 20,
        rule_id="t1.approve_to_eoa",
        rule_version="t1-v0.1",
        severity="high",
        reason_human="test",
        reason_structured={},
        agent_id="aegis-monitor-01",
        ts_ms=1,
        sig="0x" + "ab" * 65,
    )
    resp = FlagResponse(
        id=42,
        attestation=att,
        created_at=datetime(2026, 4, 21, tzinfo=UTC),
    )
    dumped = resp.model_dump(mode="json")
    assert dumped["id"] == 42
    assert dumped["attestation"]["tx_hash"] == att.tx_hash
