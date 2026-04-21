"""Tests for the Alchemy pending-tx payload parser.

Covers the wire-format surface the listener relies on: required fields,
EIP-1559 gasPrice fallback, nullable `to`, malformed payloads.
"""

from __future__ import annotations

import pytest

from aegis_monitor.mempool.parser import ParseError, parse_pending_tx
from aegis_monitor.schemas import PendingTx


def _subscription_envelope(tx: dict) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "eth_subscription",
        "params": {"subscription": "0x" + "a" * 32, "result": tx},
    }


def _legacy_tx(**overrides) -> dict:
    tx = {
        "hash": "0x" + "ab" * 32,
        "from": "0x" + "cd" * 20,
        "to": "0x" + "ef" * 20,
        "value": "0x10",
        "input": "0xa9059cbb",
        "gas": "0x5208",
        "gasPrice": "0x3b9aca00",  # 1 gwei
        "nonce": "0x5",
        "chainId": "0x1",
    }
    tx.update(overrides)
    return tx


# -----------------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------------


def test_parses_legacy_tx() -> None:
    tx = parse_pending_tx(_subscription_envelope(_legacy_tx()))
    assert isinstance(tx, PendingTx)
    assert tx.tx_hash == "0x" + "ab" * 32
    assert tx.from_address == "0x" + "cd" * 20
    assert tx.to_address == "0x" + "ef" * 20
    assert tx.value_wei == 0x10
    assert tx.gas_price == 1_000_000_000
    assert tx.nonce == 5
    assert tx.chain_id == 1


def test_accepts_null_to_for_contract_creation() -> None:
    tx = parse_pending_tx(_subscription_envelope(_legacy_tx(to=None)))
    assert tx.to_address is None


def test_eip1559_falls_back_to_max_fee_per_gas() -> None:
    # Type-2 txs have no gasPrice; we should see maxFeePerGas instead.
    inner = _legacy_tx()
    inner.pop("gasPrice")
    inner["maxFeePerGas"] = "0x77359400"  # 2 gwei
    inner["maxPriorityFeePerGas"] = "0x3b9aca00"
    tx = parse_pending_tx(_subscription_envelope(inner))
    assert tx.gas_price == 2_000_000_000


def test_defaults_input_to_0x_when_missing() -> None:
    inner = _legacy_tx()
    inner.pop("input")
    tx = parse_pending_tx(_subscription_envelope(inner))
    assert tx.input_data == "0x"


def test_preserves_raw_payload() -> None:
    inner = _legacy_tx()
    tx = parse_pending_tx(_subscription_envelope(inner))
    # Raw is normalised to lower-case via PendingTx validators for hex
    # strings, but field-preserving otherwise.
    assert tx.raw.get("nonce") == "0x5"
    assert tx.raw.get("chainId") == "0x1"


# -----------------------------------------------------------------------------
# Error path
# -----------------------------------------------------------------------------


def test_rejects_non_subscription_payload() -> None:
    with pytest.raises(ParseError):
        parse_pending_tx({"jsonrpc": "2.0", "id": 1, "result": "0xabc"})


def test_rejects_hash_only_result() -> None:
    # hashesOnly mode sends a bare hash string; we're in full-object mode.
    payload = _subscription_envelope(_legacy_tx())
    payload["params"]["result"] = "0xdead"
    with pytest.raises(ParseError):
        parse_pending_tx(payload)


def test_rejects_missing_hash() -> None:
    inner = _legacy_tx()
    inner.pop("hash")
    with pytest.raises(ParseError):
        parse_pending_tx(_subscription_envelope(inner))


def test_rejects_missing_from() -> None:
    inner = _legacy_tx()
    inner.pop("from")
    with pytest.raises(ParseError):
        parse_pending_tx(_subscription_envelope(inner))


def test_rejects_missing_params() -> None:
    with pytest.raises(ParseError):
        parse_pending_tx({"jsonrpc": "2.0", "method": "eth_subscription"})
