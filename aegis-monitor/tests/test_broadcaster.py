"""FlagBroadcaster tests — connect, disconnect, broadcast, failure cleanup.

Uses an in-process FakeWebSocket to exercise the broadcast loop without
binding a real socket.
"""

from __future__ import annotations

import pytest

from aegis_monitor.api.stream import FlagBroadcaster
from aegis_monitor.schemas import Attestation


class FakeWebSocket:
    """Stand-in for starlette's WebSocket. Only the methods the broadcaster uses."""

    def __init__(self, *, fail_on_send: bool = False) -> None:
        self.accepted = False
        self.sent: list[dict] = []
        self.fail_on_send = fail_on_send

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload: dict) -> None:
        if self.fail_on_send:
            raise RuntimeError("simulated network error")
        self.sent.append(payload)


def _attestation() -> Attestation:
    return Attestation(
        tx_hash="0x" + "ab" * 32,
        monitored_address="0x" + "cd" * 20,
        rule_id="t1.approve_to_eoa",
        rule_version="t1-v0.1",
        severity="high",
        reason_human="t",
        reason_structured={"x": 1},
        agent_id="aegis-monitor-test",
        ts_ms=1,
        sig="0x" + "ab" * 65,
    )


@pytest.mark.asyncio
async def test_connect_accepts_and_tracks() -> None:
    b = FlagBroadcaster()
    ws = FakeWebSocket()
    await b.connect(ws)
    assert ws.accepted
    assert b.client_count() == 1


@pytest.mark.asyncio
async def test_disconnect_removes_client() -> None:
    b = FlagBroadcaster()
    ws = FakeWebSocket()
    await b.connect(ws)
    await b.disconnect(ws)
    assert b.client_count() == 0


@pytest.mark.asyncio
async def test_broadcast_reaches_all_clients() -> None:
    b = FlagBroadcaster()
    ws1, ws2 = FakeWebSocket(), FakeWebSocket()
    await b.connect(ws1)
    await b.connect(ws2)
    att = _attestation()
    await b.broadcast(flag_id=42, attestation=att)
    assert len(ws1.sent) == 1 and len(ws2.sent) == 1
    payload = ws1.sent[0]
    assert payload["type"] == "flag"
    assert payload["id"] == 42
    assert payload["attestation"]["tx_hash"] == att.tx_hash


@pytest.mark.asyncio
async def test_dead_client_is_dropped_and_others_still_receive() -> None:
    b = FlagBroadcaster()
    good = FakeWebSocket()
    bad = FakeWebSocket(fail_on_send=True)
    await b.connect(good)
    await b.connect(bad)
    assert b.client_count() == 2

    await b.broadcast(flag_id=1, attestation=_attestation())

    assert b.client_count() == 1  # dead client dropped
    assert len(good.sent) == 1
    assert good.sent[0]["id"] == 1


@pytest.mark.asyncio
async def test_broadcast_with_no_clients_is_noop() -> None:
    b = FlagBroadcaster()
    # Does not raise.
    await b.broadcast(flag_id=1, attestation=_attestation())
    assert b.client_count() == 0
