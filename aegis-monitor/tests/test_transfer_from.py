"""T1.3 — transferFrom unauthorized."""

from __future__ import annotations

import pytest

from aegis_monitor.schemas import PendingTx
from aegis_monitor.screening.rules.transfer_from import (
    TransferFromUnauthorizedRule,
    _decode_transfer_from,
)


# -----------------------------------------------------------------------------
# Fakes + helpers
# -----------------------------------------------------------------------------


class FakeErc20:
    """Stand-in for Erc20Reader with pre-set return values."""

    def __init__(
        self,
        allowance_return: int | None = 0,
        is_approved_for_all_return: bool | None = False,
    ) -> None:
        self._allowance = allowance_return
        self._is_approved = is_approved_for_all_return
        self.allowance_calls: list[tuple[str, str, str]] = []
        self.is_approved_for_all_calls: list[tuple[str, str, str]] = []

    async def allowance(self, token: str, owner: str, spender: str) -> int | None:
        self.allowance_calls.append((token, owner, spender))
        return self._allowance

    async def is_approved_for_all(
        self, token: str, owner: str, operator: str
    ) -> bool | None:
        self.is_approved_for_all_calls.append((token, owner, operator))
        return self._is_approved


def _encode_address_arg(addr: str) -> str:
    return addr[2:].lower().rjust(64, "0")


def _encode_uint256(value: int) -> str:
    return f"{value:064x}"


def _transfer_from_calldata(owner: str, recipient: str, amount: int) -> str:
    return (
        "0x23b872dd"
        + _encode_address_arg(owner)
        + _encode_address_arg(recipient)
        + _encode_uint256(amount)
    )


def _pending_tx(
    input_data: str,
    *,
    from_address: str = "0x" + "33" * 20,
    to: str | None = "0x" + "11" * 20,
) -> PendingTx:
    return PendingTx(
        tx_hash="0x" + "de" * 32,
        from_address=from_address,
        to_address=to,
        value_wei=0,
        input_data=input_data,
        gas=100_000,
        gas_price=0,
        nonce=0,
    )


# -----------------------------------------------------------------------------
# Decoder
# -----------------------------------------------------------------------------


def test_decode_transfer_from_basic() -> None:
    owner = "0x" + "aa" * 20
    recipient = "0x" + "bb" * 20
    amount = 12345
    decoded = _decode_transfer_from(_transfer_from_calldata(owner, recipient, amount))
    assert decoded == (owner.lower(), recipient.lower(), amount)


def test_decode_transfer_from_short_calldata_returns_none() -> None:
    assert _decode_transfer_from("0x23b872dd") is None


# -----------------------------------------------------------------------------
# Rule
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skips_owner_moving_own_tokens() -> None:
    erc20 = FakeErc20(allowance_return=0)
    rule = TransferFromUnauthorizedRule(erc20)
    owner = "0x" + "33" * 20  # same as from_address
    calldata = _transfer_from_calldata(owner, "0x" + "bb" * 20, 100)
    assert await rule.evaluate(_pending_tx(calldata, from_address=owner)) is None
    # Should not call any RPC for this case.
    assert erc20.allowance_calls == []
    assert erc20.is_approved_for_all_calls == []


@pytest.mark.asyncio
async def test_skips_when_allowance_sufficient() -> None:
    erc20 = FakeErc20(allowance_return=1000)
    rule = TransferFromUnauthorizedRule(erc20)
    calldata = _transfer_from_calldata("0x" + "aa" * 20, "0x" + "bb" * 20, 500)
    assert await rule.evaluate(_pending_tx(calldata)) is None
    # isApprovedForAll fallback is not consulted when allowance suffices.
    assert erc20.is_approved_for_all_calls == []


@pytest.mark.asyncio
async def test_fires_when_allowance_zero_and_not_approved_for_all() -> None:
    erc20 = FakeErc20(allowance_return=0, is_approved_for_all_return=False)
    rule = TransferFromUnauthorizedRule(erc20)
    calldata = _transfer_from_calldata("0x" + "aa" * 20, "0x" + "bb" * 20, 500)
    hit = await rule.evaluate(_pending_tx(calldata))
    assert hit is not None
    assert hit.rule_id == "t1.transfer_from_unauthorized"
    assert hit.severity == "critical"
    assert hit.reason_structured["owner"] == "0x" + "aa" * 20
    assert hit.reason_structured["spender"] == "0x" + "33" * 20


@pytest.mark.asyncio
async def test_skips_when_approved_for_all_true_nft_case() -> None:
    erc20 = FakeErc20(allowance_return=0, is_approved_for_all_return=True)
    rule = TransferFromUnauthorizedRule(erc20)
    calldata = _transfer_from_calldata("0x" + "aa" * 20, "0x" + "bb" * 20, 7)  # tokenId
    assert await rule.evaluate(_pending_tx(calldata)) is None


@pytest.mark.asyncio
async def test_skips_when_both_lookups_inconclusive() -> None:
    erc20 = FakeErc20(allowance_return=None, is_approved_for_all_return=None)
    rule = TransferFromUnauthorizedRule(erc20)
    calldata = _transfer_from_calldata("0x" + "aa" * 20, "0x" + "bb" * 20, 100)
    assert await rule.evaluate(_pending_tx(calldata)) is None


@pytest.mark.asyncio
async def test_ignores_non_transfer_from_selectors() -> None:
    erc20 = FakeErc20()
    rule = TransferFromUnauthorizedRule(erc20)
    # transfer(address,uint256)
    calldata = "0xa9059cbb" + _encode_address_arg("0x" + "bb" * 20) + _encode_uint256(1)
    assert await rule.evaluate(_pending_tx(calldata)) is None
    assert erc20.allowance_calls == []


@pytest.mark.asyncio
async def test_ignores_contract_creation() -> None:
    erc20 = FakeErc20()
    rule = TransferFromUnauthorizedRule(erc20)
    calldata = _transfer_from_calldata("0x" + "aa" * 20, "0x" + "bb" * 20, 100)
    assert await rule.evaluate(_pending_tx(calldata, to=None)) is None
    assert erc20.allowance_calls == []
