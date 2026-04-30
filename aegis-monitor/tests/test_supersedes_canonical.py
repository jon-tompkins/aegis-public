"""Lock down the canonical-JSON contract under the `supersedes` extension.

The hard rule (`docs/specs/arweave-flag-storage.md`): adding optional
fields must NEVER change the canonical bytes for an attestation that
doesn't carry them. If this test breaks, every previously-signed flag
becomes unverifiable.

`exclude_none=True` in `AttestationBody.canonical_json()` is what
makes this safe — a sibling test asserts the same property at the byte
level so a future drift away from `exclude_none=True` is caught.
"""

from __future__ import annotations

import json

from aegis_monitor.schemas import Attestation, AttestationBody


def _legacy_kwargs() -> dict[str, object]:
    return {
        "tx_hash": "0x" + "ab" * 32,
        "monitored_address": "0x" + "cd" * 20,
        "rule_id": "t1.approve_to_eoa",
        "rule_version": "t1-v0.1",
        "severity": "high",
        "reason_human": "test",
        "reason_structured": {},
        "agent_id": "aegis-monitor-01",
        "ts_ms": 1,
    }


def test_canonical_omits_supersedes_when_unset() -> None:
    body = AttestationBody(**_legacy_kwargs())
    canonical = body.canonical_json()
    assert b"supersedes" not in canonical
    parsed = json.loads(canonical)
    assert "supersedes" not in parsed


def test_canonical_emits_supersedes_when_set() -> None:
    body = AttestationBody(**_legacy_kwargs(), supersedes=42)
    canonical = body.canonical_json()
    parsed = json.loads(canonical)
    assert parsed["supersedes"] == 42


def test_canonical_legacy_attestation_byte_stable_across_field_addition() -> None:
    """The exact bytes for a `supersedes=None` body must equal what a
    pre-`supersedes` codebase would have produced."""
    body = AttestationBody(**_legacy_kwargs())
    expected = (
        b'{"agent_id":"aegis-monitor-01",'
        b'"monitored_address":"0xcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd",'
        b'"reason_human":"test",'
        b'"reason_structured":{},'
        b'"rule_id":"t1.approve_to_eoa",'
        b'"rule_version":"t1-v0.1",'
        b'"severity":"high",'
        b'"ts_ms":1,'
        b'"tx_hash":"0xabababababababababababababababababababababababababababababababab"}'
    )
    assert body.canonical_json() == expected


def test_attestation_supersedes_optional_in_envelope() -> None:
    """The `Attestation` envelope (body + sig) accepts `supersedes` but
    doesn't require it — both forms round-trip cleanly."""
    sig_hex = "0x" + "ab" * 65
    plain = Attestation(**_legacy_kwargs(), sig=sig_hex)
    correction = Attestation(**_legacy_kwargs(), sig=sig_hex, supersedes=7)
    assert plain.supersedes is None
    assert correction.supersedes == 7
