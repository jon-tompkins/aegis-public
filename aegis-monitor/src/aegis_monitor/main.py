"""Aegis monitor agent — FastAPI entrypoint.

Lifespan wires the pieces that share state:

- `Settings`           — typed env config (fails fast on missing required vars)
- `AddressManager`     — in-memory + DB-backed watch set
- `AlchemyPendingTxListener` — background task feeding the tx queue
- `BytecodeChecker`    — async LRU cache for `eth_getCode` lookups
- `RuleRegistry`       — Tier 1 rules registered at boot
- `AttestationSigner`  — EIP-191 signer bound to the agent key
- `screen_tx_consumer` — drains the queue, runs rules, signs + persists hits

Persistence path: on rule hit the consumer builds an `AttestationBody`,
signs it with the agent key, and writes a row to `flags`. WS /stream
broadcast lands in the next task.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .address_manager import AddressManager
from .api import flags as flags_routes
from .api import identity as identity_routes
from .api import ready as ready_routes
from .api import routes as api_routes
from .api import stream as stream_routes
from .api.identity import load_identity_tx_id
from .api.stream import FlagBroadcaster
from .arweave import ArweaveWriter, DryRunUploader
from .attestation import AttestationSigner, insert_attestation
from .config import Settings
from .db.session import dispose_engine, get_sessionmaker, session_scope
from .mempool.alchemy import AlchemyPendingTxListener
from .schemas import Attestation, PendingTx, RuleHit
from .screening import (
    BytecodeChecker,
    Erc20Reader,
    EthCallClient,
    InteractionState,
    RuleRegistry,
)
from .screening.rules import (
    ApproveToEoaRule,
    FreshApprovalNewContractRule,
    TransferFromUnauthorizedRule,
    UnlimitedApprovalRule,
)

log = logging.getLogger(__name__)

_QUEUE_MAX = 10_000


def _ws_to_http(ws_url: str) -> str:
    """Derive the Alchemy HTTP endpoint from the WS URL."""
    if ws_url.startswith("wss://"):
        return "https://" + ws_url[len("wss://"):]
    if ws_url.startswith("ws://"):
        return "http://" + ws_url[len("ws://"):]
    return ws_url


async def _screen_tx_consumer(
    queue: asyncio.Queue[PendingTx],
    registry: RuleRegistry,
    signer: AttestationSigner,
    addrs: AddressManager,
    broadcaster: FlagBroadcaster,
) -> None:
    """Drain the pending-tx queue, run rules, sign + persist + broadcast hits.

    If the monitored watch set shrinks between the Alchemy filter update
    and the tx landing on the queue, we skip the persist — an
    attestation for an unwatched address would be noise.
    """
    log.info("screen_tx_consumer running with %d rules", len(registry))
    while True:
        tx = await queue.get()
        try:
            hits = await registry.run_all(tx)
            if hits:
                await _handle_hits(tx, hits, signer, addrs, broadcaster)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("consumer loop error for tx %s", tx.tx_hash)
        finally:
            queue.task_done()


async def _handle_hits(
    tx: PendingTx,
    hits: list[RuleHit],
    signer: AttestationSigner,
    addrs: AddressManager,
    broadcaster: FlagBroadcaster,
) -> None:
    # Our Alchemy filter subscribes on `fromAddress`, so tx.from_address is
    # the canonical monitored address for each hit.
    monitored = tx.from_address
    if not await addrs.is_monitored(monitored):
        log.debug(
            "tx %s from %s dropped — no longer monitored",
            tx.tx_hash,
            monitored,
        )
        return

    # Persist first so the broadcast always carries a valid id — we never
    # stream a flag that isn't queryable via GET /flags.
    signed_hits: list[tuple[int, Attestation]] = []
    async with session_scope() as session:
        for hit in hits:
            attestation = signer.build_and_sign(
                tx=tx, monitored_address=monitored, hit=hit
            )
            flag_id = await insert_attestation(session, attestation)
            signed_hits.append((flag_id, attestation))
            log.info(
                "FLAG id=%d tx=%s addr=%s rule=%s severity=%s",
                flag_id,
                tx.tx_hash,
                monitored,
                hit.rule_id,
                hit.severity,
            )

    for flag_id, attestation in signed_hits:
        await broadcaster.broadcast(flag_id, attestation)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings.from_env()

    queue: asyncio.Queue[PendingTx] = asyncio.Queue(maxsize=_QUEUE_MAX)
    addrs = AddressManager()
    await addrs.load_from_db()

    rpc_url = _ws_to_http(settings.alchemy_ws_url)
    bytecode = BytecodeChecker(rpc_url)
    eth_call = EthCallClient(rpc_url)
    erc20 = Erc20Reader(eth_call)
    interaction_state = InteractionState()
    registry = RuleRegistry(
        [
            ApproveToEoaRule(bytecode),
            TransferFromUnauthorizedRule(erc20),
            UnlimitedApprovalRule(erc20),
            FreshApprovalNewContractRule(interaction_state),
        ]
    )
    signer = AttestationSigner(settings.agent_signing_key, settings.agent_id)
    broadcaster = FlagBroadcaster()
    arweave_identity_tx_id = load_identity_tx_id()

    listener = AlchemyPendingTxListener(settings.alchemy_ws_url, addrs, queue)
    await listener.start()

    consumer_task = asyncio.create_task(
        _screen_tx_consumer(queue, registry, signer, addrs, broadcaster),
        name="screen-consumer",
    )

    # Arweave writer: drains the outbox queue (rows with NULL arweave_tx_id)
    # async, so the hot path is never gated on Arweave latency. Currently
    # uses DryRunUploader by default — production Irys integration is
    # tracked in docs/specs/arweave-flag-storage.md §"Bundler choice".
    arweave_writer = ArweaveWriter(
        uploader=DryRunUploader(),
        session_factory=get_sessionmaker(),
    )
    arweave_task = asyncio.create_task(arweave_writer.run(), name="arweave-writer")

    app.state.settings = settings
    app.state.queue = queue
    app.state.addrs = addrs
    app.state.listener = listener
    app.state.bytecode = bytecode
    app.state.eth_call = eth_call
    app.state.erc20 = erc20
    app.state.interaction_state = interaction_state
    app.state.registry = registry
    app.state.signer = signer
    app.state.broadcaster = broadcaster
    app.state.consumer_task = consumer_task
    app.state.arweave_writer = arweave_writer
    app.state.arweave_task = arweave_task
    app.state.arweave_identity_tx_id = arweave_identity_tx_id

    log.info(
        "aegis-monitor up: agent_id=%s signer=%s monitored=%d rules=%s",
        settings.agent_id,
        signer.address,
        len(addrs.snapshot()),
        registry.ids(),
    )

    try:
        yield
    finally:
        log.info("aegis-monitor shutting down")
        await listener.stop()
        consumer_task.cancel()
        arweave_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await consumer_task
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await arweave_task
        await bytecode.close()
        await eth_call.close()
        await dispose_engine()


app = FastAPI(title="Aegis Monitor Agent", version="0.1.0", lifespan=lifespan)

# CORS is a boot-time concern (CORSMiddleware can't be mutated after startup),
# so read origins directly from env rather than routing through Settings. "*"
# is fine for dev and the demo monitor site; tighten to an explicit list in
# prod via AEGIS_ALLOWED_ORIGINS.
_cors_origins_raw = os.environ.get("AEGIS_ALLOWED_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_routes.router)
app.include_router(flags_routes.router)
app.include_router(stream_routes.router)
app.include_router(ready_routes.router)
app.include_router(identity_routes.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — always returns OK if the process is up.

    Deliberately decoupled from Alchemy / DB state so the HEALTHCHECK in
    the Dockerfile doesn't churn on transient upstream issues. `/ready`
    gates on both.
    """
    return {"status": "ok"}
