"""Realistic Alchemy `alchemy_pendingTransactions` payloads.

Addresses used below are real mainnet contracts / tokens where that
matters for the rule's correctness (the spender's bytecode status is what
determines whether the approve-to-EOA rule fires). The `from` addresses
on the drainer-style fixtures are synthetic — we don't want to publish
any real victim wallets in test data.

Reference addresses:

- USDC              `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` — ERC-20
- WETH              `0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` — ERC-20
- Uniswap V2 Router `0x7a250d5630b4cf539739df2c5dacb4c659f2488d` — contract
- Uniswap V3 Router `0xe592427a0aece92de3edee1f18e0157c05861564` — contract
- Permit2           `0x000000000022d473030f116ddee9f6b43ac78ba3` — contract

The synthetic "drainer" EOA below is chosen to be unambiguously
non-existent / non-coded and bears no relation to any real actor.
"""

from __future__ import annotations

from typing import Any

# ---- canonical addresses (lower-case; inline hex avoids checksum drift) ----

USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
UNISWAP_V2_ROUTER = "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"
UNISWAP_V3_ROUTER = "0xe592427a0aece92de3edee1f18e0157c05861564"
PERMIT2 = "0x000000000022d473030f116ddee9f6b43ac78ba3"

# Synthetic EOA used as the "drainer" in drainer-style fixtures. Has no
# known mainnet activity or bytecode.
SYNTHETIC_DRAINER_EOA = "0x1111111111222222222233333333334444444444"

# Synthetic victim addresses for the `from` field.
SYNTHETIC_VICTIM_A = "0xaa000000000000000000000000000000000000aa"
SYNTHETIC_VICTIM_B = "0xbb000000000000000000000000000000000000bb"


# ---- ABI encoding helpers -------------------------------------------------


def _pad_addr(addr: str) -> str:
    """Right-align a 20-byte address in a 32-byte ABI slot."""
    return addr[2:].lower().rjust(64, "0")


def _uint256(value: int) -> str:
    return hex(value)[2:].rjust(64, "0")


_UINT256_MAX = (1 << 256) - 1


# ---- calldata builders ----------------------------------------------------


def approve_calldata(spender: str, amount: int = _UINT256_MAX) -> str:
    """ERC-20 approve(address,uint256)."""
    return "0x095ea7b3" + _pad_addr(spender) + _uint256(amount)


def increase_allowance_calldata(spender: str, amount: int) -> str:
    """ERC-20 increaseAllowance(address,uint256)."""
    return "0x39509351" + _pad_addr(spender) + _uint256(amount)


def set_approval_for_all_calldata(operator: str, approved: bool = True) -> str:
    """ERC-721 setApprovalForAll(address,bool)."""
    return (
        "0xa22cb465" + _pad_addr(operator) + _uint256(1 if approved else 0)
    )


def transfer_calldata(to: str, amount: int) -> str:
    """ERC-20 transfer(address,uint256) — not an approval; should miss the rule."""
    return "0xa9059cbb" + _pad_addr(to) + _uint256(amount)


# ---- Alchemy subscription envelope ----------------------------------------


def alchemy_pending_tx(
    *,
    tx_hash: str,
    from_addr: str,
    to: str | None,
    input_data: str,
    value_wei: int = 0,
    gas: int = 100_000,
    gas_price: int = 5 * 10**9,
    nonce: int = 42,
    chain_id: int = 1,
) -> dict[str, Any]:
    """Wrap the tx fields in the Alchemy `eth_subscription` JSON-RPC envelope."""
    return {
        "jsonrpc": "2.0",
        "method": "eth_subscription",
        "params": {
            "subscription": "0x" + "a" * 32,
            "result": {
                "hash": tx_hash,
                "from": from_addr,
                "to": to,
                "value": hex(value_wei),
                "input": input_data,
                "gas": hex(gas),
                "gasPrice": hex(gas_price),
                "nonce": hex(nonce),
                "chainId": hex(chain_id),
            },
        },
    }


# ---- Named scenarios ------------------------------------------------------
#
# Each scenario returns (payload, contract_lookup, should_fire).
# `contract_lookup` maps lower-case address -> whether it has contract code.
# The pipeline test uses it to stub the BytecodeChecker.


def scenario_legitimate_usdc_approve_to_uniswap() -> tuple[dict[str, Any], dict[str, bool], bool]:
    """Everyday: approve USDC to Uniswap V2 router. Must NOT fire."""
    payload = alchemy_pending_tx(
        tx_hash="0x" + "a" * 64,
        from_addr=SYNTHETIC_VICTIM_A,
        to=USDC,
        input_data=approve_calldata(UNISWAP_V2_ROUTER),
    )
    return payload, {UNISWAP_V2_ROUTER: True}, False


def scenario_legitimate_weth_approve_to_permit2() -> tuple[dict[str, Any], dict[str, bool], bool]:
    """Permit2 is canonical — approvals here are safe. Must NOT fire."""
    payload = alchemy_pending_tx(
        tx_hash="0x" + "b" * 64,
        from_addr=SYNTHETIC_VICTIM_A,
        to=WETH,
        input_data=approve_calldata(PERMIT2),
    )
    return payload, {PERMIT2: True}, False


def scenario_drainer_unlimited_approval_to_eoa() -> tuple[dict[str, Any], dict[str, bool], bool]:
    """The bad one: unlimited USDC approval to an EOA. MUST fire."""
    payload = alchemy_pending_tx(
        tx_hash="0x" + "c" * 64,
        from_addr=SYNTHETIC_VICTIM_B,
        to=USDC,
        input_data=approve_calldata(SYNTHETIC_DRAINER_EOA),
    )
    return payload, {SYNTHETIC_DRAINER_EOA: False}, True


def scenario_drainer_set_approval_for_all_to_eoa() -> tuple[dict[str, Any], dict[str, bool], bool]:
    """ERC-721 setApprovalForAll to an EOA — classic NFT drainer. MUST fire."""
    nft_contract = "0x1234567890123456789012345678901234567890"
    payload = alchemy_pending_tx(
        tx_hash="0x" + "d" * 64,
        from_addr=SYNTHETIC_VICTIM_B,
        to=nft_contract,
        input_data=set_approval_for_all_calldata(SYNTHETIC_DRAINER_EOA),
    )
    return payload, {SYNTHETIC_DRAINER_EOA: False}, True


def scenario_non_approval_transfer() -> tuple[dict[str, Any], dict[str, bool], bool]:
    """USDC transfer() — not an approval. Must NOT fire; bytecode check skipped."""
    payload = alchemy_pending_tx(
        tx_hash="0x" + "e" * 64,
        from_addr=SYNTHETIC_VICTIM_A,
        to=USDC,
        input_data=transfer_calldata(SYNTHETIC_DRAINER_EOA, 10**6),
    )
    return payload, {}, False


def scenario_increase_allowance_to_eoa() -> tuple[dict[str, Any], dict[str, bool], bool]:
    """increaseAllowance — same pattern as approve. MUST fire."""
    payload = alchemy_pending_tx(
        tx_hash="0x" + "f" * 64,
        from_addr=SYNTHETIC_VICTIM_A,
        to=USDC,
        input_data=increase_allowance_calldata(SYNTHETIC_DRAINER_EOA, 10**18),
    )
    return payload, {SYNTHETIC_DRAINER_EOA: False}, True


ALL_SCENARIOS = [
    ("usdc_to_uniswap_v2", scenario_legitimate_usdc_approve_to_uniswap),
    ("weth_to_permit2", scenario_legitimate_weth_approve_to_permit2),
    ("unlimited_approve_to_eoa", scenario_drainer_unlimited_approval_to_eoa),
    ("set_approval_for_all_to_eoa", scenario_drainer_set_approval_for_all_to_eoa),
    ("non_approval_transfer", scenario_non_approval_transfer),
    ("increase_allowance_to_eoa", scenario_increase_allowance_to_eoa),
]
