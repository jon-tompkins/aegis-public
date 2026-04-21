"""EIP-191 signer tests — correctness, recoverability, determinism.

Uses a fixed private key (`_TEST_KEY`) so the recoverable address is
stable and tests can assert exact values without relying on randomness.
"""

from __future__ import annotations

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct

from aegis_monitor.attestation.signer import AttestationSigner
from aegis_monitor.schemas import AttestationBody, PendingTx, RuleHit


# Deterministic test key — DO NOT reuse on any real network.
_TEST_KEY = "0x" + "11" * 32


def _body(**overrides) -> AttestationBody:
    base = {
        "tx_hash": "0x" + "ab" * 32,
        "monitored_address": "0x" + "cd" * 20,
        "rule_id": "t1.approve_to_eoa",
        "rule_version": "t1-v0.1",
        "severity": "high",
        "reason_human": "unit-test",
        "reason_structured": {"spender": "0x" + "ef" * 20},
        "agent_id": "aegis-monitor-test",
        "ts_ms": 1_713_654_321_000,
    }
    base.update(overrides)
    return AttestationBody(**base)


def test_signer_address_matches_key() -> None:
    signer = AttestationSigner(_TEST_KEY, agent_id="t")
    expected = Account.from_key(bytes.fromhex(_TEST_KEY[2:])).address
    assert signer.address == expected


def test_sign_produces_valid_attestation() -> None:
    signer = AttestationSigner(_TEST_KEY, agent_id="t")
    att = signer.sign(_body())
    # Sig must satisfy the Attestation validator (132 chars, 0x prefix, hex).
    assert att.sig.startswith("0x")
    assert len(att.sig) == 132


def test_sign_recovers_to_signer_address() -> None:
    """Round-trip: sign with key, verify with public address via EIP-191 recovery."""
    signer = AttestationSigner(_TEST_KEY, agent_id="t")
    body = _body()
    att = signer.sign(body)

    # Independent verification — what a third party would do.
    canonical = body.canonical_json()
    message = encode_defunct(canonical)
    recovered = Account.recover_message(message, signature=att.sig)
    assert recovered.lower() == signer.address.lower()


def test_same_body_produces_same_signature() -> None:
    signer = AttestationSigner(_TEST_KEY, agent_id="t")
    a = signer.sign(_body())
    b = signer.sign(_body())
    assert a.sig == b.sig


def test_different_body_produces_different_signature() -> None:
    signer = AttestationSigner(_TEST_KEY, agent_id="t")
    a = signer.sign(_body())
    b = signer.sign(_body(ts_ms=1))
    assert a.sig != b.sig


def test_accepts_key_without_0x_prefix() -> None:
    key_no_prefix = _TEST_KEY[2:]
    signer = AttestationSigner(key_no_prefix, agent_id="t")
    assert signer.address == Account.from_key(bytes.fromhex(key_no_prefix)).address


def test_rejects_bad_key_length() -> None:
    with pytest.raises(ValueError):
        AttestationSigner("0xdeadbeef", agent_id="t")


def test_build_and_sign_stamps_timestamp_if_absent() -> None:
    signer = AttestationSigner(_TEST_KEY, agent_id="t")
    tx = PendingTx(
        tx_hash="0x" + "ab" * 32,
        from_address="0x" + "cd" * 20,
        to_address="0x" + "ef" * 20,
        value_wei=0,
        input_data="0x095ea7b3",
        gas=21000,
        gas_price=0,
        nonce=0,
    )
    hit = RuleHit(
        rule_id="t1.approve_to_eoa",
        rule_version="t1-v0.1",
        severity="high",
        reason_human="x",
        reason_structured={},
    )
    att = signer.build_and_sign(tx=tx, monitored_address=tx.from_address, hit=hit)
    # Stamp is wall-clock ms; just sanity check it's a 13-digit-ish int.
    assert att.ts_ms > 1_600_000_000_000  # after 2020


def test_build_and_sign_respects_explicit_timestamp() -> None:
    signer = AttestationSigner(_TEST_KEY, agent_id="t")
    tx = PendingTx(
        tx_hash="0x" + "ab" * 32,
        from_address="0x" + "cd" * 20,
        to_address="0x" + "ef" * 20,
        value_wei=0,
        input_data="0x095ea7b3",
        gas=21000,
        gas_price=0,
        nonce=0,
    )
    hit = RuleHit(
        rule_id="t1.approve_to_eoa",
        rule_version="t1-v0.1",
        severity="high",
        reason_human="x",
        reason_structured={},
    )
    att = signer.build_and_sign(
        tx=tx, monitored_address=tx.from_address, hit=hit, ts_ms=42
    )
    assert att.ts_ms == 42
