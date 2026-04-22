"""Generic `eth_call` JSON-RPC helper.

Used by rules that need to read view-only contract state on the candidate
tx's destination — e.g. `allowance(owner, spender)` for T1.3 or
`balanceOf(owner)` for T1.4.

Failure mode is uniform: any RPC error returns `None` so callers can decide
whether to skip the rule (cautious) or treat as zero (aggressive). Rules
that flag on "no allowance" should treat None as inconclusive and skip,
not as zero.
"""

from __future__ import annotations

import logging

import httpx

log = logging.getLogger(__name__)


class EthCallClient:
    """Minimal `eth_call` client over JSON-RPC.

    One `httpx.AsyncClient` is reused across calls. `close()` is idempotent
    and safe to call from FastAPI's lifespan teardown.
    """

    def __init__(self, rpc_url: str, *, request_timeout_s: float = 5.0) -> None:
        self._rpc_url = rpc_url
        self._timeout = request_timeout_s
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def call(self, to: str, data: str) -> str | None:
        """Issue `eth_call` and return the raw 0x-prefixed hex result.

        Returns None on any error — connection, HTTP status, JSON-RPC
        error field, or missing result. Rules treat None as "could not
        determine" and skip rather than firing on guesswork.
        """
        client = await self._get_client()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": to, "data": data}, "latest"],
        }
        try:
            response = await client.post(self._rpc_url, json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError:
            log.exception("eth_call HTTP failure to=%s", to)
            return None
        if "error" in body:
            # Reverts and other RPC errors land here. Common for non-ERC20
            # contracts being asked an ERC20 question; not actionable.
            log.debug("eth_call returned error: %s", body["error"])
            return None
        result = body.get("result")
        if not isinstance(result, str) or not result.startswith("0x"):
            return None
        return result
