"""T1.4 — unlimited / outsized approval."""

from __future__ import annotations

import pytest

from aegis_monitor.schemas import PendingTx
from aegis_monitor.screening.rules.unlimited_approval import (
    _UINT256_MAX,
    UnlimitedApprovalRule,
    _decode_approve_amount,
    _decode_permit,
)

# -----------------------------------------------------------------------------
# Fakes + helpers
# -----------------------------------------------------------------------------


class FakeErc20:
    def __init__(self, balance_return: int | None = 0) -> None:
        self._balance = balance_return
        self.balance_calls: list[tuple[str, str]] = []

    async def balance_of(self, token: str, owner: str) -> int | None:
        self.balance_calls.append((token, owner))
        return self._balance

    async def allowance(self, token: str, owner: str, spender: str) -> int | None:
        return None

    async def is_approved_for_all(
        self, token: str, owner: str, operator: str
    ) -> bool | None:
        return None


def _encode_address_arg(addr: str) -> str:
    return addr[2:].lower().rjust(64, "0")


def _encode_uint256(value: int) -> str:
    return f"{value:064x}"


def _approve_calldata(spender: str, amount: int) -> str:
    return "0x095ea7b3" + _encode_address_arg(spender) + _encode_uint256(amount)


def _increase_allowance_calldata(spender: str, amount: int) -> str:
    return "0x39509351" + _encode_address_arg(spender) + _encode_uint256(amount)


def _permit_calldata(owner: str, spender: str, value: int) -> str:
    return (
        "0xd505accf"
        + _encode_address_arg(owner)
        + _encode_address_arg(spender)
        + _encode_uint256(value)
        + _encode_uint256(0)  # deadline
        + _encode_uint256(0)  # v
        + _encode_uint256(0)  # r
        + _encode_uint256(0)  # s
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
# Decoders
# -----------------------------------------------------------------------------


def test_decode_approve_amount() -> None:
    spender = "0x" + "ab" * 20
    decoded = _decode_approve_amount(_approve_calldata(spender, 7777))
    assert decoded == (spender.lower(), 7777)


def test_decode_permit_owner_and_spender_and_value() -> None:
    owner = "0x" + "aa" * 20
    spender = "0x" + "bb" * 20
    decoded = _decode_permit(_permit_calldata(owner, spender, 999))
    assert decoded == (owner.lower(), spender.lower(), 999)


# -----------------------------------------------------------------------------
# Rule — unlimited tier
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fires_high_on_uint256_max_approve() -> None:
    erc20 = FakeErc20()
    rule = UnlimitedApprovalRule(erc20)
    calldata = _approve_calldata("0x" + "ab" * 20, _UINT256_MAX)
    hit = await rule.evaluate(_pending_tx(calldata))
    assert hit is not None
    assert hit.severity == "high"
    assert hit.reason_structured["trigger"] == "uint256_max"
    # Did not consult balance.
    assert erc20.balance_calls == []


@pytest.mark.asyncio
async def test_fires_high_on_uint256_max_permit() -> None:
    erc20 = FakeErc20()
    rule = UnlimitedApprovalRule(erc20)
    owner = "0x" + "aa" * 20
    spender = "0x" + "bb" * 20
    calldata = _permit_calldata(owner, spender, _UINT256_MAX)
    hit = await rule.evaluate(_pending_tx(calldata))
    assert hit is not None
    assert hit.severity == "high"
    assert hit.reason_structured["owner"] == owner.lower()
    assert hit.reason_structured["spender"] == spender.lower()


# -----------------------------------------------------------------------------
# Rule — outsized tier
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fires_medium_when_amount_exceeds_10x_balance() -> None:
    erc20 = FakeErc20(balance_return=100)
    rule = UnlimitedApprovalRule(erc20)
    calldata = _approve_calldata("0x" + "ab" * 20, 1500)  # 15× balance
    hit = await rule.evaluate(_pending_tx(calldata))
    assert hit is not None
    assert hit.severity == "medium"
    assert hit.reason_structured["trigger"] == "outsized_vs_balance"
    assert hit.reason_structured["owner_balance"] == "100"


@pytest.mark.asyncio
async def test_skips_when_amount_within_10x_balance() -> None:
    erc20 = FakeErc20(balance_return=100)
    rule = UnlimitedApprovalRule(erc20)
    calldata = _approve_calldata("0x" + "ab" * 20, 500)  # 5× balance
    assert await rule.evaluate(_pending_tx(calldata)) is None


@pytest.mark.asyncio
async def test_skips_when_balance_zero() -> None:
    erc20 = FakeErc20(balance_return=0)
    rule = UnlimitedApprovalRule(erc20)
    calldata = _approve_calldata("0x" + "ab" * 20, 1_000_000)
    assert await rule.evaluate(_pending_tx(calldata)) is None


@pytest.mark.asyncio
async def test_skips_when_balance_lookup_fails() -> None:
    erc20 = FakeErc20(balance_return=None)
    rule = UnlimitedApprovalRule(erc20)
    calldata = _approve_calldata("0x" + "ab" * 20, 1_000_000)
    assert await rule.evaluate(_pending_tx(calldata)) is None


@pytest.mark.asyncio
async def test_ignores_non_approval_selectors() -> None:
    erc20 = FakeErc20(balance_return=100)
    rule = UnlimitedApprovalRule(erc20)
    # transfer(address,uint256)
    calldata = "0xa9059cbb" + _encode_address_arg("0x" + "bb" * 20) + _encode_uint256(_UINT256_MAX)
    assert await rule.evaluate(_pending_tx(calldata)) is None
    assert erc20.balance_calls == []


@pytest.mark.asyncio
async def test_ignores_set_approval_for_all() -> None:
    erc20 = FakeErc20(balance_return=100)
    rule = UnlimitedApprovalRule(erc20)
    # setApprovalForAll(address,bool) — out of scope for T1.4.
    calldata = "0xa22cb465" + _encode_address_arg("0x" + "bb" * 20) + _encode_uint256(1)
    assert await rule.evaluate(_pending_tx(calldata)) is None


@pytest.mark.asyncio
async def test_ignores_contract_creation() -> None:
    erc20 = FakeErc20(balance_return=100)
    rule = UnlimitedApprovalRule(erc20)
    calldata = _approve_calldata("0x" + "ab" * 20, _UINT256_MAX)
    assert await rule.evaluate(_pending_tx(calldata, to=None)) is None
