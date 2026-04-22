"""Erc20Reader — ABI-encoded eth_call wrappers."""

from __future__ import annotations

import pytest

from aegis_monitor.screening.erc20 import (
    Erc20Reader,
    _decode_bool,
    _decode_uint256,
    _encode_address,
)

# -----------------------------------------------------------------------------
# Encoding / decoding primitives
# -----------------------------------------------------------------------------


def test_encode_address_pads_to_32_bytes() -> None:
    addr = "0x" + "ab" * 20
    encoded = _encode_address(addr)
    assert len(encoded) == 64
    assert encoded == "0" * 24 + "ab" * 20


def test_decode_uint256_normal() -> None:
    assert _decode_uint256("0x" + "0" * 62 + "2a") == 42


def test_decode_uint256_max() -> None:
    assert _decode_uint256("0x" + "f" * 64) == (1 << 256) - 1


def test_decode_uint256_empty_returns_none() -> None:
    assert _decode_uint256("0x") is None


def test_decode_uint256_no_prefix_returns_none() -> None:
    assert _decode_uint256("ff") is None


def test_decode_bool_true() -> None:
    assert _decode_bool("0x" + "0" * 63 + "1") is True


def test_decode_bool_false() -> None:
    assert _decode_bool("0x" + "0" * 64) is False


def test_decode_bool_empty_returns_none() -> None:
    assert _decode_bool("0x") is None


# -----------------------------------------------------------------------------
# Reader — verify request shape via FakeEthCall
# -----------------------------------------------------------------------------


class FakeEthCall:
    def __init__(self, response: str | None = None) -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    async def call(self, to: str, data: str) -> str | None:
        self.calls.append((to, data))
        return self.response


@pytest.mark.asyncio
async def test_allowance_builds_correct_calldata() -> None:
    fake = FakeEthCall(response="0x" + "0" * 62 + "ff")  # 255
    reader = Erc20Reader(fake)
    token = "0x" + "11" * 20
    owner = "0x" + "aa" * 20
    spender = "0x" + "bb" * 20
    result = await reader.allowance(token, owner, spender)
    assert result == 255
    assert len(fake.calls) == 1
    to, data = fake.calls[0]
    assert to == token
    # selector + 2 padded address slots
    assert data.startswith("0xdd62ed3e")
    assert len(data) == 10 + 64 + 64
    assert data[10:74] == _encode_address(owner)
    assert data[74:138] == _encode_address(spender)


@pytest.mark.asyncio
async def test_balance_of_builds_correct_calldata() -> None:
    fake = FakeEthCall(response="0x" + "0" * 60 + "1234")
    reader = Erc20Reader(fake)
    token = "0x" + "11" * 20
    owner = "0x" + "aa" * 20
    result = await reader.balance_of(token, owner)
    assert result == 0x1234
    to, data = fake.calls[0]
    assert to == token
    assert data.startswith("0x70a08231")
    assert data[10:] == _encode_address(owner)


@pytest.mark.asyncio
async def test_is_approved_for_all_returns_bool() -> None:
    fake = FakeEthCall(response="0x" + "0" * 63 + "1")
    reader = Erc20Reader(fake)
    result = await reader.is_approved_for_all(
        "0x" + "11" * 20, "0x" + "aa" * 20, "0x" + "bb" * 20
    )
    assert result is True


@pytest.mark.asyncio
async def test_call_failure_returns_none() -> None:
    fake = FakeEthCall(response=None)
    reader = Erc20Reader(fake)
    assert await reader.allowance("0x" + "11" * 20, "0x" + "aa" * 20, "0x" + "bb" * 20) is None
    assert await reader.balance_of("0x" + "11" * 20, "0x" + "aa" * 20) is None
    assert await reader.is_approved_for_all(
        "0x" + "11" * 20, "0x" + "aa" * 20, "0x" + "bb" * 20
    ) is None
