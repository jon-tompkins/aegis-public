"""ERC-20 read helpers used by Tier 1 rules.

`allowance(owner, spender)` — for T1.3 (transferFrom unauthorized).
`balanceOf(owner)`           — for T1.4 (outsized approval).

All calls go through `EthCallClient` and return `None` on any failure —
RPC error, revert, malformed reply. Rules treat `None` as inconclusive
and skip rather than flagging on missing data.
"""

from __future__ import annotations

from .eth_call import EthCallClient

# Function selectors (first 4 bytes of keccak256(signature)).
_ALLOWANCE_SELECTOR = "0xdd62ed3e"  # allowance(address,address)
_BALANCE_OF_SELECTOR = "0x70a08231"  # balanceOf(address)
_IS_APPROVED_FOR_ALL_SELECTOR = "0xe985e9c5"  # isApprovedForAll(address,address)


def _encode_address(addr: str) -> str:
    """Right-pad a 20-byte address into a 32-byte ABI slot, hex only."""
    return addr[2:].lower().rjust(64, "0")


def _decode_uint256(hex_result: str) -> int | None:
    """Decode a 32-byte hex word as a uint256.

    Returns None for empty/malformed results so callers can treat that
    distinctly from a legitimate zero.
    """
    if not hex_result.startswith("0x"):
        return None
    body = hex_result[2:]
    if len(body) == 0:
        return None
    try:
        return int(body, 16)
    except ValueError:
        return None


def _decode_bool(hex_result: str) -> bool | None:
    value = _decode_uint256(hex_result)
    if value is None:
        return None
    return value != 0


class Erc20Reader:
    """Read view-only ERC-20 (and ERC-721 approvals) state via `eth_call`."""

    def __init__(self, eth_call: EthCallClient) -> None:
        self._eth_call = eth_call

    async def allowance(
        self, token: str, owner: str, spender: str
    ) -> int | None:
        """Return `IERC20(token).allowance(owner, spender)` or None on error.

        Reverts on non-ERC20 contracts produce None; callers should treat
        that as "can't tell" and not as zero.
        """
        data = (
            _ALLOWANCE_SELECTOR
            + _encode_address(owner)
            + _encode_address(spender)
        )
        result = await self._eth_call.call(token, data)
        if result is None:
            return None
        return _decode_uint256(result)

    async def balance_of(self, token: str, owner: str) -> int | None:
        """Return `IERC20(token).balanceOf(owner)` or None on error."""
        data = _BALANCE_OF_SELECTOR + _encode_address(owner)
        result = await self._eth_call.call(token, data)
        if result is None:
            return None
        return _decode_uint256(result)

    async def is_approved_for_all(
        self, token: str, owner: str, operator: str
    ) -> bool | None:
        """Return `IERC721(token).isApprovedForAll(owner, operator)` or None.

        Used as a fallback on `transferFrom` when ERC-20 allowance lookup
        is inconclusive — covers the ERC-721 case where transferFrom
        carries a tokenId rather than an amount.
        """
        data = (
            _IS_APPROVED_FOR_ALL_SELECTOR
            + _encode_address(owner)
            + _encode_address(operator)
        )
        result = await self._eth_call.call(token, data)
        if result is None:
            return None
        return _decode_bool(result)
