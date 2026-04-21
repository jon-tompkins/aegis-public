"""Cache policy tests for `BytecodeChecker`.

HTTP is mocked out via monkeypatch on `_fetch_has_code`. We're testing
the cache + eviction + TTL logic, not the HTTP round-trip (that happens
against real Alchemy in integration).
"""

from __future__ import annotations

import time

import pytest

from aegis_monitor.screening.bytecode import BytecodeChecker


@pytest.fixture
def fake_checker(monkeypatch: pytest.MonkeyPatch) -> tuple[BytecodeChecker, list[str]]:
    checker = BytecodeChecker(rpc_url="https://unused", negative_ttl_s=0.05)
    calls: list[str] = []

    async def fake_fetch(address: str) -> bool:
        calls.append(address)
        # Addresses ending in even parity are "contracts", odd are "EOAs".
        # This lets tests encode intent in the address itself.
        return int(address[-1], 16) % 2 == 0

    monkeypatch.setattr(checker, "_fetch_has_code", fake_fetch)
    return checker, calls


@pytest.mark.asyncio
async def test_positive_cached_after_first_lookup(
    fake_checker: tuple[BytecodeChecker, list[str]],
) -> None:
    checker, calls = fake_checker
    addr = "0x" + "a" * 39 + "0"  # last hex = 0 → even → "has code"
    assert await checker.has_code(addr) is True
    assert await checker.has_code(addr) is True  # cache hit
    assert calls == [addr]  # only one RPC
    assert checker.positive_cache_size == 1


@pytest.mark.asyncio
async def test_negative_respects_ttl(
    fake_checker: tuple[BytecodeChecker, list[str]],
) -> None:
    checker, calls = fake_checker
    addr = "0x" + "b" * 39 + "1"  # last hex = 1 → odd → "no code"
    assert await checker.has_code(addr) is False
    assert await checker.has_code(addr) is False  # cached
    assert calls == [addr]
    # Wait past the 50ms TTL from the fixture
    time.sleep(0.1)
    assert await checker.has_code(addr) is False
    assert calls == [addr, addr]  # second RPC after TTL expiry


@pytest.mark.asyncio
async def test_address_case_normalised(
    fake_checker: tuple[BytecodeChecker, list[str]],
) -> None:
    checker, calls = fake_checker
    upper = "0x" + "A" * 39 + "0"
    lower = "0x" + "a" * 39 + "0"
    assert await checker.has_code(upper) is True
    assert await checker.has_code(lower) is True
    # Both cache hits reference the same (lower) key.
    assert calls == [lower]


@pytest.mark.asyncio
async def test_positive_cache_lru_eviction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checker = BytecodeChecker(rpc_url="https://unused", max_entries=3)

    async def fake_fetch(address: str) -> bool:
        return True  # all "contracts"

    monkeypatch.setattr(checker, "_fetch_has_code", fake_fetch)

    for i in range(5):
        addr = f"0x{i:040x}"
        await checker.has_code(addr)

    # Capacity 3 — only the three most-recently-inserted survive.
    assert checker.positive_cache_size == 3


@pytest.mark.asyncio
async def test_move_to_end_on_hit_keeps_hot_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checker = BytecodeChecker(rpc_url="https://unused", max_entries=3)

    async def fake_fetch(address: str) -> bool:
        return True

    monkeypatch.setattr(checker, "_fetch_has_code", fake_fetch)

    a = "0x" + "a" * 40
    b = "0x" + "b" * 40
    c = "0x" + "c" * 40
    d = "0x" + "d" * 40

    await checker.has_code(a)
    await checker.has_code(b)
    await checker.has_code(c)
    # Hit A again — it should be moved to the "recently used" end.
    await checker.has_code(a)
    # D comes in, evicting the oldest — which is B, not A.
    await checker.has_code(d)

    # A is still cached; B should be gone.
    assert await checker.has_code(a) is True  # cache hit
    assert await checker.has_code(d) is True  # cache hit
