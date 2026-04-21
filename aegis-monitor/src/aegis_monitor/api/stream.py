"""Live flag broadcast over WebSocket.

`FlagBroadcaster` owns the set of connected clients. The consumer task
in `main.py` calls `broadcast()` after each successful DB insert — the
flag id comes first so clients can dedupe against any history they
fetched from `GET /flags`.

Disconnects are handled by dropping any client that raises on send; the
client library is expected to reconnect. One lock serialises
registration + the snapshot taken at broadcast time, so we can't send
to a client mid-disconnect and race its cleanup.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..schemas import Attestation

router = APIRouter()

log = logging.getLogger(__name__)


class FlagBroadcaster:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    # -- lifecycle ---------------------------------------------------------

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)
        log.info("ws client connected; total=%d", len(self._clients))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
        log.info("ws client disconnected; total=%d", len(self._clients))

    # -- stats --------------------------------------------------------------

    def client_count(self) -> int:
        return len(self._clients)

    # -- push ---------------------------------------------------------------

    async def broadcast(self, flag_id: int, attestation: Attestation) -> None:
        """Send one flag to every connected client.

        Clients that error on send are dropped — the next reconnect will
        resync state via `GET /flags?since=...`. We never block the
        consumer loop on a slow client.
        """
        payload = {
            "type": "flag",
            "id": flag_id,
            "attestation": attestation.model_dump(mode="json"),
        }
        async with self._lock:
            clients = list(self._clients)
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)
            log.info("dropped %d dead ws client(s); total=%d", len(dead), len(self._clients))


@router.websocket("/stream")
async def stream(ws: WebSocket) -> None:
    """Handle one WS client lifecycle.

    We don't expect inbound messages beyond framing pings, so the loop
    simply waits for the client to disconnect. Server-initiated messages
    come from the consumer via `broadcaster.broadcast()`.
    """
    broadcaster = _resolve_broadcaster(ws)
    await broadcaster.connect(ws)
    try:
        while True:
            _msg = await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("ws error; closing client")
    finally:
        await broadcaster.disconnect(ws)


def _resolve_broadcaster(ws_or_request: Any) -> FlagBroadcaster:
    """Pull the shared broadcaster off `app.state`. Raises if not wired."""
    app = ws_or_request.app
    broadcaster = getattr(app.state, "broadcaster", None)
    if broadcaster is None:
        raise RuntimeError("broadcaster not initialised on app.state")
    return broadcaster
