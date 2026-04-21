"""Cached async check for whether an address has contract code.

Hot path: every approval the mempool surfaces gets a bytecode lookup on
the spender. Uncached, that's 1 RPC call per approval — at mainnet
approval rates this is fine for demo scale but worth caching anyway.

Cache policy:

- **Positives** (`has_code=True`) are cached forever. A contract can't
  become an EOA; once code is deployed to an address it stays deployed.
  SELFDESTRUCT was removed in the Cancun upgrade, and even in older EVMs
  the address retains its contract status for the duration of our
  process lifetime.
- **Negatives** (`has_code=False`) are cached with a TTL. CREATE2 can
  deploy to a previously-empty address, so a false-now isn't necessarily
  false-forever. Default 10 minutes is a balance between RPC pressure
  and detection latency for a new deploy.

Bounded LRU size (default 10k) keeps memory sane in long-running
processes. Eviction uses `OrderedDict` insertion/move-to-end ordering.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict

import httpx

log = logging.getLogger(__name__)


class BytecodeChecker:
    def __init__(
        self,
        rpc_url: str,
        *,
        negative_ttl_s: float = 600.0,
        max_entries: int = 10_000,
        request_timeout_s: float = 5.0,
    ) -> None:
        self._rpc_url = rpc_url
        self._negative_ttl = negative_ttl_s
        self._max = max_entries
        self._timeout = request_timeout_s
        self._positives: OrderedDict[str, bool] = OrderedDict()
        self._negatives: OrderedDict[str, float] = OrderedDict()  # addr -> expiry (monotonic)
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None

    # -- cache stats (exposed for /ready or metrics) -----------------------

    @property
    def positive_cache_size(self) -> int:
        return len(self._positives)

    @property
    def negative_cache_size(self) -> int:
        return len(self._negatives)

    # -- lifecycle ---------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # -- main entry --------------------------------------------------------

    async def has_code(self, address: str) -> bool:
        """Returns True if the address has any contract bytecode.

        Cache-first. On miss, issues an `eth_getCode` JSON-RPC call and
        records the result under the appropriate policy (permanent for
        positives, TTL for negatives).
        """
        address = address.lower()

        # Fast path: cache hit.
        async with self._lock:
            if address in self._positives:
                self._positives.move_to_end(address)
                return True
            if address in self._negatives:
                expiry = self._negatives[address]
                if expiry > time.monotonic():
                    self._negatives.move_to_end(address)
                    return False
                del self._negatives[address]

        # Miss — do the RPC outside the lock so concurrent lookups don't
        # serialise through it.
        has_code = await self._fetch_has_code(address)

        async with self._lock:
            if has_code:
                self._positives[address] = True
                self._trim(self._positives)
            else:
                self._negatives[address] = time.monotonic() + self._negative_ttl
                self._trim(self._negatives)

        return has_code

    async def _fetch_has_code(self, address: str) -> bool:
        client = await self._get_client()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getCode",
            "params": [address, "latest"],
        }
        try:
            response = await client.post(self._rpc_url, json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            log.exception("eth_getCode failed for %s; assuming has_code=False", address)
            return False
        code = data.get("result", "0x")
        # Treat the empty responses as "no code"; anything with >= 2 bytes (4 hex
        # chars past the 0x prefix) is a real contract.
        return isinstance(code, str) and code not in ("0x", "", "0x0") and len(code) > 2

    def _trim(self, od: OrderedDict[str, object]) -> None:
        while len(od) > self._max:
            od.popitem(last=False)
