"""Tests for the Arweave writer task.

The DB-drain loop needs a real Postgres to exercise `FOR UPDATE SKIP
LOCKED`, so it's covered at the deploy smoke-test level. These tests
focus on the unit-testable surface: canonical-byte construction (must
exactly match what `AttestationBody.canonical_json()` would produce) and
the cooperative-cancellation contract that the lifespan handler depends
on.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from aegis_monitor.arweave.uploader import Tag
from aegis_monitor.arweave.writer import ArweaveWriter
from aegis_monitor.db.models import Flag
from aegis_monitor.schemas import AttestationBody


class _RecordingUploader:
    def __init__(self) -> None:
        self.calls: list[tuple[bytes, list[Tag]]] = []

    async def upload(self, payload: bytes, tags: list[Tag]) -> str:
        self.calls.append((payload, tags))
        return "fake-tx-id"


def _flag(**overrides: Any) -> Flag:
    base: dict[str, Any] = {
        "id": 1,
        "tx_hash": "0x" + "ab" * 32,
        "monitored_address": "0x" + "cd" * 20,
        "rule_id": "t1.approve_to_eoa",
        "rule_version": "t1-v0.1",
        "severity": "high",
        "reason_human": "test reason",
        "reason_structured": {"spender": "0x" + "ef" * 20},
        "agent_id": "aegis-monitor-01",
        "ts_ms": 1_700_000_000_000,
        "sig": "0x" + "ab" * 65,
        "supersedes": None,
        "arweave_tx_id": None,
        "arweave_confirmed_at": None,
    }
    base.update(overrides)
    return Flag(**base)


def test_writer_payload_matches_canonical_body_plus_sig() -> None:
    """The bytes uploaded to Arweave must be the canonical body merged
    with `sig`. Any drift here breaks third-party verification because
    the on-Arweave bytes wouldn't recompute to the EIP-191-signed form.
    """
    flag = _flag()
    writer = ArweaveWriter(uploader=_RecordingUploader(), session_factory=None)  # type: ignore[arg-type]
    uploader = writer._uploader  # type: ignore[attr-defined]

    asyncio.run(writer._upload_one(flag))  # type: ignore[attr-defined]

    payload, _tags = uploader.calls[0]  # type: ignore[attr-defined]
    parsed = json.loads(payload)

    body = AttestationBody(
        tx_hash=flag.tx_hash,
        monitored_address=flag.monitored_address,
        rule_id=flag.rule_id,
        rule_version=flag.rule_version,
        severity=flag.severity,  # type: ignore[arg-type]
        reason_human=flag.reason_human,
        reason_structured=flag.reason_structured,
        agent_id=flag.agent_id,
        ts_ms=flag.ts_ms,
    )
    expected_body = json.loads(body.canonical_json())
    expected_body["sig"] = flag.sig
    assert parsed == expected_body
    # And the bytes are sorted-key compact — same canonical rules.
    assert b": " not in payload and b", " not in payload


def test_writer_includes_supersedes_when_set() -> None:
    flag = _flag(supersedes=42)
    writer = ArweaveWriter(uploader=_RecordingUploader(), session_factory=None)  # type: ignore[arg-type]

    asyncio.run(writer._upload_one(flag))  # type: ignore[attr-defined]

    uploader = writer._uploader  # type: ignore[attr-defined]
    payload, tags = uploader.calls[0]  # type: ignore[attr-defined]
    assert json.loads(payload)["supersedes"] == 42
    # Tags drive third-party discovery — the rule + agent + addr triple
    # has to make it through.
    tag_pairs = {t.name: t.value for t in tags}
    assert tag_pairs["Aegis-Agent-Id"] == flag.agent_id
    assert tag_pairs["Aegis-Rule-Id"] == flag.rule_id


def test_writer_run_is_cancellation_safe() -> None:
    """`asyncio.CancelledError` must propagate cleanly so the lifespan
    handler can shut us down without the process hanging."""

    class _IdleSessionFactory:
        def __call__(self) -> Any:
            class _S:
                async def __aenter__(self) -> _S:
                    return self

                async def __aexit__(self, *_a: Any) -> None:
                    return None

                def begin(self) -> Any:
                    class _Tx:
                        async def __aenter__(self_) -> None:
                            return None

                        async def __aexit__(self_, *_a: Any) -> None:
                            return None

                    return _Tx()

                async def execute(self, _stmt: Any) -> Any:
                    class _Result:
                        def scalars(self_) -> Any:
                            class _Sc:
                                def all(self__) -> list[Any]:
                                    return []

                            return _Sc()

                    return _Result()

            return _S()

    writer = ArweaveWriter(
        uploader=_RecordingUploader(),
        session_factory=_IdleSessionFactory(),  # type: ignore[arg-type]
        poll_interval_s=0.01,
    )

    async def _go() -> None:
        task = asyncio.create_task(writer.run())
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(_go())


def test_writer_rejects_nonsense_batch_size() -> None:
    with pytest.raises(ValueError):
        ArweaveWriter(
            uploader=_RecordingUploader(),
            session_factory=None,  # type: ignore[arg-type]
            batch_size=0,
        )
