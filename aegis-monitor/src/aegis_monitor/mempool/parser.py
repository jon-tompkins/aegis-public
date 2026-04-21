"""Parse Alchemy `alchemy_pendingTransactions` WS payloads into `PendingTx`.

The full-object form of the subscription returns a JSON-RPC notification
shaped like:

```
{
  "jsonrpc": "2.0",
  "method": "eth_subscription",
  "params": {
    "subscription": "0x…",
    "result": {
      "hash": "0x…", "from": "0x…", "to": "0x…" | null,
      "value": "0x…", "input": "0x…", "gas": "0x…",
      "gasPrice": "0x…" | (EIP-1559: "maxFeePerGas"/"maxPriorityFeePerGas"),
      "nonce": "0x…", "chainId": "0x1", …
    }
  }
}
```

EIP-1559 txs don't carry `gasPrice`; we fall back to `maxFeePerGas` so
downstream rules see a usable number rather than zero. The raw payload is
preserved on `PendingTx.raw` for rule-level forensics.
"""

from __future__ import annotations

from typing import Any

from ..schemas import PendingTx


class ParseError(ValueError):
    """Raised when a payload doesn't match the Alchemy pending-tx shape."""


def _hex_to_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 16) if value.startswith("0x") else int(value)
    raise ParseError(f"cannot convert {value!r} to int")


def _hex_to_int_opt(value: Any) -> int | None:
    if value is None:
        return None
    return _hex_to_int(value)


def parse_pending_tx(payload: dict[str, Any]) -> PendingTx:
    """Extract a `PendingTx` from a subscription notification.

    Raises `ParseError` on anything that isn't the expected shape. Callers
    should catch and log rather than crash the listener — the WS feed
    occasionally includes non-tx administrative messages we want to ignore.
    """

    if payload.get("method") != "eth_subscription":
        raise ParseError("not an eth_subscription payload")
    params = payload.get("params")
    if not isinstance(params, dict):
        raise ParseError("missing or malformed params")
    result = params.get("result")
    # `hashesOnly` mode returns a bare hash string; we run in full-object mode.
    if not isinstance(result, dict):
        raise ParseError("result is not a full tx object")

    try:
        tx_hash = result["hash"]
        from_addr = result["from"]
    except KeyError as e:
        raise ParseError(f"missing required field: {e.args[0]}") from e

    gas_price = result.get("gasPrice")
    if gas_price is None:
        # EIP-1559 fallback — use maxFeePerGas so rules have a ceiling to
        # reason about, not zero.
        gas_price = result.get("maxFeePerGas")

    return PendingTx(
        tx_hash=tx_hash,
        from_address=from_addr,
        to_address=result.get("to"),
        value_wei=_hex_to_int(result.get("value")),
        input_data=result.get("input") or "0x",
        gas=_hex_to_int(result.get("gas")),
        gas_price=_hex_to_int(gas_price),
        nonce=_hex_to_int(result.get("nonce")),
        chain_id=_hex_to_int_opt(result.get("chainId")),
        raw=result,
    )
