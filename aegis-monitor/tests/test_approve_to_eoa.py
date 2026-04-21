"""T1.1 / T1.2 rule behavior + ABI decoder tests."""

from __future__ import annotations

import pytest

from aegis_monitor.schemas import PendingTx
from aegis_monitor.screening.rules.approve_to_eoa import (
    ApproveToEoaRule,
    _decode_spender,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


class FakeBytecode:
    """Stand-in for BytecodeChecker that returns a pre-set answer."""

    def __init__(self, has_code_return: bool) -> None:
        self._has_code = has_code_return
        self.calls: list[str] = []

    async def has_code(self, address: str) -> bool:
        self.calls.append(address)
        return self._has_code


def _pending_tx(input_data: str, to: str | None = "0x" + "11" * 20) -> PendingTx:
    return PendingTx(
        tx_hash="0x" + "de" * 32,
        from_address="0x" + "22" * 20,
        to_address=to,
        value_wei=0,
        input_data=input_data,
        gas=100_000,
        gas_price=0,
        nonce=0,
    )


def _encode_address_arg(addr: str) -> str:
    """Right-pad a 20-byte address into a 32-byte ABI slot, hex only."""
    stripped = addr[2:].lower()  # drop 0x
    return stripped.rjust(64, "0")


def _approve_calldata(spender: str) -> str:
    amount = "ff" * 32  # unlimited
    return "0x095ea7b3" + _encode_address_arg(spender) + amount


def _set_approval_for_all_calldata(operator: str, approved: bool = True) -> str:
    flag = "0" * 63 + ("1" if approved else "0")
    return "0xa22cb465" + _encode_address_arg(operator) + flag


def _permit_calldata(owner: str, spender: str) -> str:
    # owner, spender, value, deadline, v, r, s (with v + r + s each 32 bytes)
    value = "0" * 64
    deadline = "0" * 64
    v = "0" * 64
    r = "0" * 64
    s = "0" * 64
    return (
        "0xd505accf"
        + _encode_address_arg(owner)
        + _encode_address_arg(spender)
        + value
        + deadline
        + v
        + r
        + s
    )


# -----------------------------------------------------------------------------
# Decoder
# -----------------------------------------------------------------------------


def test_decode_spender_approve() -> None:
    spender = "0x" + "cd" * 20
    assert _decode_spender(_approve_calldata(spender), "0x095ea7b3") == spender.lower()


def test_decode_spender_set_approval_for_all() -> None:
    operator = "0x" + "ef" * 20
    calldata = _set_approval_for_all_calldata(operator)
    assert _decode_spender(calldata, "0xa22cb465") == operator.lower()


def test_decode_spender_permit_uses_arg1() -> None:
    owner = "0x" + "aa" * 20
    spender = "0x" + "bb" * 20
    calldata = _permit_calldata(owner, spender)
    assert _decode_spender(calldata, "0xd505accf") == spender.lower()


def test_decode_spender_short_calldata_returns_none() -> None:
    assert _decode_spender("0x095ea7b3", "0x095ea7b3") is None


def test_decode_spender_unknown_selector_returns_none() -> None:
    assert _decode_spender("0xdeadbeef" + "0" * 64, "0xdeadbeef") is None


# -----------------------------------------------------------------------------
# Rule
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fires_when_spender_has_no_code() -> None:
    rule = ApproveToEoaRule(FakeBytecode(has_code_return=False))
    spender = "0x" + "cd" * 20
    hit = await rule.evaluate(_pending_tx(_approve_calldata(spender)))
    assert hit is not None
    assert hit.rule_id == "t1.approve_to_eoa"
    assert hit.severity == "high"
    assert hit.reason_structured["method"] == "approve"
    assert hit.reason_structured["spender"] == spender.lower()


@pytest.mark.asyncio
async def test_does_not_fire_when_spender_is_contract() -> None:
    rule = ApproveToEoaRule(FakeBytecode(has_code_return=True))
    hit = await rule.evaluate(_pending_tx(_approve_calldata("0x" + "cd" * 20)))
    assert hit is None


@pytest.mark.asyncio
async def test_ignores_non_approval_selectors() -> None:
    # transfer(address,uint256) — 0xa9059cbb. Not an approval; skip without
    # even calling the bytecode checker.
    bytecode = FakeBytecode(has_code_return=False)
    rule = ApproveToEoaRule(bytecode)
    calldata = "0xa9059cbb" + _encode_address_arg("0x" + "cd" * 20) + "00" * 32
    assert await rule.evaluate(_pending_tx(calldata)) is None
    assert bytecode.calls == []


@pytest.mark.asyncio
async def test_ignores_contract_creation() -> None:
    bytecode = FakeBytecode(has_code_return=False)
    rule = ApproveToEoaRule(bytecode)
    assert await rule.evaluate(_pending_tx(_approve_calldata("0x" + "cd" * 20), to=None)) is None
    assert bytecode.calls == []


@pytest.mark.asyncio
async def test_fires_for_set_approval_for_all_to_eoa() -> None:
    rule = ApproveToEoaRule(FakeBytecode(has_code_return=False))
    operator = "0x" + "ef" * 20
    calldata = _set_approval_for_all_calldata(operator)
    hit = await rule.evaluate(_pending_tx(calldata))
    assert hit is not None
    assert hit.reason_structured["method"] == "setApprovalForAll"
    assert hit.reason_structured["spender"] == operator.lower()


@pytest.mark.asyncio
async def test_fires_for_permit_to_eoa() -> None:
    rule = ApproveToEoaRule(FakeBytecode(has_code_return=False))
    owner = "0x" + "aa" * 20
    spender = "0x" + "bb" * 20
    hit = await rule.evaluate(_pending_tx(_permit_calldata(owner, spender)))
    assert hit is not None
    assert hit.reason_structured["method"] == "permit"
    assert hit.reason_structured["spender"] == spender.lower()
