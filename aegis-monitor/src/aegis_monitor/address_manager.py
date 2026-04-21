"""In-memory set of monitored addresses, backed by Postgres.

On startup: loads the active set from the `monitored_addresses` table.
On `add()` / `remove()`: writes through to the DB, updates the in-memory
set, and signals any waiter via an `asyncio.Event` so the mempool
listener can re-subscribe with the new filter.

Design note: the spec allows ~O(tens) of monitored addresses in v1, so
an in-memory `set[str]` is the right shape. The Event isn't a queue —
one fire coalesces many concurrent adds/removes, which is fine because
the listener always reads a fresh snapshot when it re-subscribes.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from .db.models import MonitoredAddress
from .db.session import session_scope


class AddressManager:
    def __init__(self) -> None:
        self._addrs: set[str] = set()
        self._lock = asyncio.Lock()
        self._change = asyncio.Event()

    # -- lifecycle ---------------------------------------------------------

    async def load_from_db(self) -> None:
        """Populate the in-memory set from `monitored_addresses` (active rows)."""
        async with session_scope() as s:
            result = await s.execute(
                select(MonitoredAddress.address).where(
                    MonitoredAddress.active.is_(True)
                )
            )
            self._addrs = {row[0] for row in result.all()}

    # -- reads -------------------------------------------------------------

    def snapshot(self) -> set[str]:
        """Thread-unsafe copy. Callers should treat this as a point-in-time view."""
        return set(self._addrs)

    async def list_active(self) -> list[str]:
        return sorted(self._addrs)

    async def is_monitored(self, address: str) -> bool:
        return address.lower() in self._addrs

    # -- mutations ---------------------------------------------------------

    async def add(self, address: str) -> None:
        """Add an address to the watch set. Idempotent.

        Reactivates a previously soft-deleted row rather than stacking a
        second entry, so history in `flags` stays joinable on a single
        canonical row.
        """
        address = address.lower()
        async with self._lock:
            async with session_scope() as s:
                existing = await s.get(MonitoredAddress, address)
                if existing is None:
                    s.add(MonitoredAddress(address=address, active=True))
                elif not existing.active:
                    existing.active = True
                    existing.removed_at = None
                # else: already active; no-op.
            self._addrs.add(address)
            self._change.set()

    async def remove(self, address: str) -> bool:
        """Soft-delete an address. Returns True on a real removal, False if not watched."""
        address = address.lower()
        async with self._lock:
            async with session_scope() as s:
                existing = await s.get(MonitoredAddress, address)
                if existing is None or not existing.active:
                    return False
                existing.active = False
                existing.removed_at = datetime.now(timezone.utc)
            self._addrs.discard(address)
            self._change.set()
            return True

    # -- coordination with the listener ------------------------------------

    async def wait_for_change(self) -> None:
        """Block until the next add/remove. One event coalesces many changes."""
        await self._change.wait()
        self._change.clear()
