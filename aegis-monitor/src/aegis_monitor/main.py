"""Aegis monitor agent — FastAPI entrypoint.

Lifespan wires the pieces that share state:

- `Settings`        — typed env config (fails fast on missing required vars)
- `AddressManager`  — in-memory + DB-backed watch set
- `AlchemyPendingTxListener` — background task feeding the tx queue
- `BytecodeChecker` — async LRU cache for `eth_getCode` lookups
- `RuleRegistry`    — the Tier 1 rules registered at boot
- `screen_tx_consumer` — drains the queue, runs rules, logs hits

Persistence of the hits (EIP-191 signing + DB insert + WS broadcast)
arrives in the next task. For now, hits are logged at INFO so we can
eyeball the pipeline end-to-end locally.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .address_manager import AddressManager
from .api import routes as api_routes
from .config import Settings
from .db.session import dispose_engine
from .mempool.alchemy import AlchemyPendingTxListener
from .schemas import PendingTx, RuleHit
from .screening import BytecodeChecker, RuleRegistry
from .screening.rules import ApproveToEoaRule

log = logging.getLogger(__name__)

_QUEUE_MAX = 10_000


def _ws_to_http(ws_url: str) -> str:
    """Derive the Alchemy HTTP endpoint from the WS URL.

    Alchemy serves `wss://…` and `https://…` from the same host + API key
    prefix, so string replacement is sufficient. Callers that need a
    different RPC endpoint can introduce a dedicated env var later.
    """
    if ws_url.startswith("wss://"):
        return "https://" + ws_url[len("wss://"):]
    if ws_url.startswith("ws://"):
        return "http://" + ws_url[len("ws://"):]
    return ws_url


async def _screen_tx_consumer(
    queue: asyncio.Queue[PendingTx],
    registry: RuleRegistry,
) -> None:
    """Drain the pending-tx queue, run rules, log any hits.

    Persistence will replace the logging in the next task.
    """
    log.info("screen_tx_consumer running with %d rules", len(registry))
    while True:
        tx = await queue.get()
        try:
            hits = await registry.run_all(tx)
            for hit in hits:
                _log_hit(tx, hit)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("consumer loop error for tx %s", tx.tx_hash)
        finally:
            queue.task_done()


def _log_hit(tx: PendingTx, hit: RuleHit) -> None:
    log.info(
        "FLAG %s tx=%s addr=%s rule=%s severity=%s reason=%s",
        hit.rule_id,
        tx.tx_hash,
        tx.from_address,
        hit.rule_version,
        hit.severity,
        hit.reason_human,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings.from_env()

    queue: asyncio.Queue[PendingTx] = asyncio.Queue(maxsize=_QUEUE_MAX)
    addrs = AddressManager()
    await addrs.load_from_db()

    bytecode = BytecodeChecker(_ws_to_http(settings.alchemy_ws_url))
    registry = RuleRegistry([ApproveToEoaRule(bytecode)])

    listener = AlchemyPendingTxListener(settings.alchemy_ws_url, addrs, queue)
    await listener.start()

    consumer_task = asyncio.create_task(
        _screen_tx_consumer(queue, registry), name="screen-consumer"
    )

    app.state.settings = settings
    app.state.queue = queue
    app.state.addrs = addrs
    app.state.listener = listener
    app.state.bytecode = bytecode
    app.state.registry = registry
    app.state.consumer_task = consumer_task

    log.info(
        "aegis-monitor up: agent_id=%s monitored=%d rules=%s",
        settings.agent_id,
        len(addrs.snapshot()),
        registry.ids(),
    )

    try:
        yield
    finally:
        log.info("aegis-monitor shutting down")
        await listener.stop()
        consumer_task.cancel()
        try:
            await consumer_task
        except (asyncio.CancelledError, Exception):
            pass
        await bytecode.close()
        await dispose_engine()


app = FastAPI(title="Aegis Monitor Agent", version="0.1.0", lifespan=lifespan)
app.include_router(api_routes.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — always returns OK if the process is up.

    Deliberately decoupled from Alchemy / DB state so the HEALTHCHECK in
    the Dockerfile doesn't churn on transient upstream issues. `/ready`
    (to be added) will gate on both.
    """
    return {"status": "ok"}
