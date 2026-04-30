"""Outbox-driven Arweave writer task.

The writer drains rows where `arweave_tx_id IS NULL` (the
`ix_flags_arweave_pending` partial index = our queue), rebuilds the
canonical body bytes, calls the configured uploader, and writes the
returned tx id back. The hot path never blocks on Arweave; if the
writer is paused (network, wallet empty, uploader down) flags stay
queryable via `/flags` immediately, just without an Arweave receipt.

Concurrency safety:

- `SELECT ... FOR UPDATE SKIP LOCKED` ensures multiple writer instances
  (e.g. a future sidecar deploy) won't double-upload a row.
- The row update happens in the same transaction as the lock, so if the
  uploader call succeeds but the DB commit fails the next iteration
  re-uploads — duplicates are tolerated (Arweave permanence is fine
  with multiple identical records).

Backoff:

- Empty queue → poll every `poll_interval_s`.
- Upload exception → exponential delay capped at `max_backoff_s`,
  reset on next success.
- The task is cancellation-safe: `asyncio.CancelledError` propagates
  cleanly so the lifespan shutdown path doesn't hang.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..db.models import Flag
from ..schemas import AttestationBody
from .uploader import ArweaveUploader, build_flag_tags

log = logging.getLogger(__name__)


class ArweaveWriter:
    def __init__(
        self,
        uploader: ArweaveUploader,
        session_factory: async_sessionmaker,
        *,
        batch_size: int = 25,
        poll_interval_s: float = 2.0,
        max_backoff_s: float = 300.0,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        self._uploader = uploader
        self._session_factory = session_factory
        self._batch_size = batch_size
        self._poll_interval_s = poll_interval_s
        self._max_backoff_s = max_backoff_s

    async def run(self) -> None:
        """Loop forever. Designed to be run via `asyncio.create_task`."""
        log.info(
            "arweave writer started: batch=%d poll=%.1fs",
            self._batch_size,
            self._poll_interval_s,
        )
        backoff = self._poll_interval_s
        while True:
            try:
                processed = await self._drain_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("arweave writer iteration failed; backing off %.1fs", backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self._max_backoff_s)
                continue
            backoff = self._poll_interval_s
            if processed == 0:
                await asyncio.sleep(self._poll_interval_s)

    async def _drain_once(self) -> int:
        """One pass over the outbox. Returns rows processed."""
        async with self._session_factory() as session, session.begin():
            stmt = (
                select(Flag)
                .where(Flag.arweave_tx_id.is_(None))
                .order_by(Flag.id.asc())
                .limit(self._batch_size)
                .with_for_update(skip_locked=True)
            )
            result = await session.execute(stmt)
            rows = list(result.scalars().all())
            if not rows:
                return 0

            for row in rows:
                tx_id = await self._upload_one(row)
                await session.execute(
                    update(Flag)
                    .where(Flag.id == row.id)
                    .values(
                        arweave_tx_id=tx_id,
                        arweave_confirmed_at=datetime.now(UTC),
                    )
                )
            return len(rows)

    async def _upload_one(self, row: Flag) -> str:
        body = AttestationBody(
            tx_hash=row.tx_hash,
            monitored_address=row.monitored_address,
            rule_id=row.rule_id,
            rule_version=row.rule_version,
            severity=row.severity,  # type: ignore[arg-type]
            reason_human=row.reason_human,
            reason_structured=row.reason_structured,
            agent_id=row.agent_id,
            ts_ms=row.ts_ms,
            supersedes=row.supersedes,
        )
        # Re-derive bytes from the persisted fields (not from a cached
        # `canonical_body` column) so an upgrade that adds a field can't
        # publish a stale serialisation. The `sig` is already locked
        # against the canonical bytes, so a body that doesn't recompute
        # to the same shape would have been unverifiable anyway.
        payload_obj = body.model_dump(mode="json", exclude_none=True)
        payload_obj["sig"] = row.sig
        # Same canonical rules as `AttestationBody.canonical_json` so the
        # on-Arweave bytes match what a verifier reconstructs.
        import json

        payload = json.dumps(
            payload_obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        tags = build_flag_tags(
            agent_id=row.agent_id,
            tx_hash=row.tx_hash,
            monitored_address=row.monitored_address,
            rule_id=row.rule_id,
            rule_version=row.rule_version,
            severity=row.severity,
            ts_ms=row.ts_ms,
        )
        return await self._uploader.upload(payload, tags)
