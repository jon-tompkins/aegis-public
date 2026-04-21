"""Aegis monitor agent — FastAPI entrypoint.

Lifespan wires together the pieces that need shared state:

- `Settings`        — typed env config (fails fast on missing required vars)
- `AddressManager`  — in-memory + DB-backed watch set
- `AlchemyPendingTxListener` — background task feeding the internal queue
- `asyncio.Queue`   — pending-tx stream for the rule engine (consumer TBD)

Per-request state is attached to `app.state` so handlers can resolve the
manager without a dependency-injection dance. The `/health` endpoint
stays env-free so local liveness checks don't require a full config.
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
from .schemas import PendingTx

log = logging.getLogger(__name__)

_QUEUE_MAX = 10_000


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings.from_env()

    queue: asyncio.Queue[PendingTx] = asyncio.Queue(maxsize=_QUEUE_MAX)
    addrs = AddressManager()
    await addrs.load_from_db()

    listener = AlchemyPendingTxListener(settings.alchemy_ws_url, addrs, queue)
    await listener.start()

    app.state.settings = settings
    app.state.queue = queue
    app.state.addrs = addrs
    app.state.listener = listener

    log.info(
        "aegis-monitor up: agent_id=%s monitored=%d",
        settings.agent_id,
        len(addrs.snapshot()),
    )

    try:
        yield
    finally:
        log.info("aegis-monitor shutting down")
        await listener.stop()
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
