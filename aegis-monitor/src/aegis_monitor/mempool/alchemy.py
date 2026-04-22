"""Alchemy `alchemy_pendingTransactions` WebSocket listener.

Design:

- One background task owns the connection.
- On each connect, we snapshot the monitored address set and subscribe
  once with the whole set in the `fromAddress` filter.
- On address-set change (`AddressManager.wait_for_change()` fires), we
  close and reconnect. That's a few hundred ms of listener downtime per
  mutation, which is acceptable at demo scale and simpler than managing
  multiple subscriptions in flight.
- On disconnect: exponential backoff, capped at 60 s.
- Parsed `PendingTx` objects go on an `asyncio.Queue` that the rule
  engine (separate task) will consume.

The listener is cooperative — `stop()` cancels the task and waits for
cleanup. Callers should own the queue and consumer task lifecycles
separately.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from ..address_manager import AddressManager
from ..schemas import PendingTx
from .parser import ParseError, parse_pending_tx

log = logging.getLogger(__name__)

_MAX_BACKOFF_SECONDS = 60.0
_SUBSCRIBE_ID = 1


class AlchemyPendingTxListener:
    def __init__(
        self,
        ws_url: str,
        address_manager: AddressManager,
        out_queue: asyncio.Queue[PendingTx],
    ) -> None:
        self._ws_url = ws_url
        self._addrs = address_manager
        self._queue = out_queue
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        if self._task is not None:
            raise RuntimeError("listener already started")
        self._running = True
        self._task = asyncio.create_task(self._run(), name="alchemy-listener")

    async def stop(self) -> None:
        self._running = False
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await self._task
        self._task = None

    # ---- internals -------------------------------------------------------

    async def _run(self) -> None:
        backoff = 1.0
        while self._running:
            try:
                async with connect(self._ws_url) as ws:
                    log.info("alchemy ws connected")
                    backoff = 1.0
                    await self._subscribe_and_consume(ws)
            except asyncio.CancelledError:
                raise
            except ConnectionClosed as e:
                log.warning("alchemy ws closed: %s", e)
            except Exception:
                log.exception("alchemy ws listener error")
            if not self._running:
                return
            sleep_for = min(backoff, _MAX_BACKOFF_SECONDS)
            log.info("reconnecting in %.1fs", sleep_for)
            await asyncio.sleep(sleep_for)
            backoff *= 2

    async def _subscribe_and_consume(self, ws: Any) -> None:
        addresses = self._addrs.snapshot()
        if not addresses:
            log.info("no monitored addresses — idling until one is added")
            await self._addrs.wait_for_change()
            return

        sub_req = {
            "jsonrpc": "2.0",
            "id": _SUBSCRIBE_ID,
            "method": "eth_subscribe",
            "params": [
                "alchemy_pendingTransactions",
                {"fromAddress": sorted(addresses)},
            ],
        }
        await ws.send(json.dumps(sub_req))

        ack_raw = await ws.recv()
        try:
            ack = json.loads(ack_raw)
        except json.JSONDecodeError:
            log.error("subscription ack not valid JSON: %r", ack_raw[:200])
            return
        if ack.get("id") == _SUBSCRIBE_ID and "result" in ack:
            log.info("subscribed; sub_id=%s fromAddress=%d", ack["result"], len(addresses))
        else:
            log.error("subscription failed: %s", ack)
            return

        change_task = asyncio.create_task(self._addrs.wait_for_change())
        try:
            while True:
                recv_task = asyncio.create_task(ws.recv())
                done, _ = await asyncio.wait(
                    [recv_task, change_task], return_when=asyncio.FIRST_COMPLETED
                )
                if change_task in done:
                    log.info("address set changed; reconnecting to re-subscribe")
                    recv_task.cancel()
                    return
                msg = recv_task.result()
                try:
                    payload = json.loads(msg)
                    tx = parse_pending_tx(payload)
                    await self._queue.put(tx)
                except ParseError:
                    log.debug("unparseable payload: %r", str(msg)[:200])
                except Exception:
                    log.exception("dropping message after parse error")
        finally:
            change_task.cancel()
