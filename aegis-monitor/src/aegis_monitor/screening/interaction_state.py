"""In-memory tracker for T1.5: fresh-approval → first-touch correlation.

Process-local for v1. Persistence (so the signal survives restart) is a
follow-up — see issue #21 task list. Two pieces of state:

- `last_approval_ms[monitored]` — wallclock when this address last
  approved any spender (EOA or contract).
- `seen_destinations[monitored]` — set of contract addresses this
  address has previously called.

Both are bounded by `max_addresses` (LRU on monitored address) so a
long-running process with churn doesn't grow unbounded. Per-address
`seen_destinations` is also LRU-bounded by `max_destinations_per_addr`.
"""

from __future__ import annotations

from collections import OrderedDict


class InteractionState:
    def __init__(
        self,
        *,
        max_addresses: int = 5_000,
        max_destinations_per_addr: int = 2_000,
    ) -> None:
        self._max_addrs = max_addresses
        self._max_dests = max_destinations_per_addr
        self._last_approval_ms: OrderedDict[str, int] = OrderedDict()
        self._seen_destinations: OrderedDict[str, OrderedDict[str, None]] = OrderedDict()

    # -- approval bookkeeping ---------------------------------------------

    def record_approval(self, monitored: str, ts_ms: int) -> None:
        addr = monitored.lower()
        self._last_approval_ms[addr] = ts_ms
        self._last_approval_ms.move_to_end(addr)
        self._evict(self._last_approval_ms, self._max_addrs)

    def last_approval_ms(self, monitored: str) -> int | None:
        return self._last_approval_ms.get(monitored.lower())

    # -- destination bookkeeping ------------------------------------------

    def has_seen_destination(self, monitored: str, destination: str) -> bool:
        addr = monitored.lower()
        dest = destination.lower()
        bucket = self._seen_destinations.get(addr)
        if bucket is None:
            return False
        if dest in bucket:
            bucket.move_to_end(dest)
            return True
        return False

    def record_destination(self, monitored: str, destination: str) -> None:
        addr = monitored.lower()
        dest = destination.lower()
        bucket = self._seen_destinations.get(addr)
        if bucket is None:
            bucket = OrderedDict()
            self._seen_destinations[addr] = bucket
        bucket[dest] = None
        bucket.move_to_end(dest)
        self._evict(bucket, self._max_dests)
        self._seen_destinations.move_to_end(addr)
        self._evict(self._seen_destinations, self._max_addrs)

    # -- inspection (used by tests + /ready stats) -------------------------

    def known_addresses(self) -> int:
        return len(self._seen_destinations)

    def destination_count(self, monitored: str) -> int:
        bucket = self._seen_destinations.get(monitored.lower())
        return 0 if bucket is None else len(bucket)

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _evict(od: OrderedDict, limit: int) -> None:
        while len(od) > limit:
            od.popitem(last=False)
