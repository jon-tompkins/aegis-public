"""T1.5 — fresh approval followed by first-touch on a new contract."""

from __future__ import annotations

from typing import Iterator
from unittest.mock import patch

import pytest

from aegis_monitor.schemas import PendingTx
from aegis_monitor.screening.interaction_state import InteractionState
from aegis_monitor.screening.rules.fresh_approval_new_contract import (
    FreshApprovalNewContractRule,
)


_MONITORED = "0x" + "33" * 20
_TOKEN = "0x" + "11" * 20
_OTHER_CONTRACT = "0x" + "44" * 20


def _encode_address_arg(addr: str) -> str:
    return addr[2:].lower().rjust(64, "0")


def _approve_calldata(spender: str = "0x" + "ab" * 20, amount: int = 1) -> str:
    return "0x095ea7b3" + _encode_address_arg(spender) + f"{amount:064x}"


def _generic_call_calldata() -> str:
    # Some random non-approval selector with no args.
    return "0xdeadbeef"


def _pending_tx(
    input_data: str,
    *,
    to: str | None = _TOKEN,
    from_address: str = _MONITORED,
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


@pytest.fixture
def fixed_clock() -> Iterator[list[int]]:
    """Patch _now_ms with a controllable counter shared across calls."""
    current = [1_000_000]

    def _now() -> int:
        return current[0]

    with patch(
        "aegis_monitor.screening.rules.fresh_approval_new_contract._now_ms",
        side_effect=_now,
    ):
        yield current


# -----------------------------------------------------------------------------
# Approval observation (no hit on the approval itself)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approval_alone_does_not_fire_but_records_state(fixed_clock: list[int]) -> None:
    state = InteractionState()
    rule = FreshApprovalNewContractRule(state, window_seconds=120)
    assert await rule.evaluate(_pending_tx(_approve_calldata())) is None
    assert state.last_approval_ms(_MONITORED) == 1_000_000
    # Approval target is recorded as seen so a follow-up call to the same
    # address doesn't get flagged as "new contract".
    assert state.has_seen_destination(_MONITORED, _TOKEN)


# -----------------------------------------------------------------------------
# Fires
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fires_on_new_contract_within_window(fixed_clock: list[int]) -> None:
    state = InteractionState()
    rule = FreshApprovalNewContractRule(state, window_seconds=120)

    # Approve a token at t=0.
    await rule.evaluate(_pending_tx(_approve_calldata(), to=_TOKEN))

    # 30s later, monitored calls a brand-new contract.
    fixed_clock[0] += 30_000
    hit = await rule.evaluate(
        _pending_tx(_generic_call_calldata(), to=_OTHER_CONTRACT)
    )
    assert hit is not None
    assert hit.rule_id == "t1.fresh_approval_new_contract"
    assert hit.reason_structured["destination_contract"] == _OTHER_CONTRACT
    assert hit.reason_structured["elapsed_ms_since_approval"] == 30_000


@pytest.mark.asyncio
async def test_does_not_fire_on_repeat_call_after_first_touch(
    fixed_clock: list[int],
) -> None:
    state = InteractionState()
    rule = FreshApprovalNewContractRule(state, window_seconds=120)

    await rule.evaluate(_pending_tx(_approve_calldata(), to=_TOKEN))
    fixed_clock[0] += 30_000
    first = await rule.evaluate(
        _pending_tx(_generic_call_calldata(), to=_OTHER_CONTRACT)
    )
    assert first is not None

    # Second call to the same contract — no longer "new".
    fixed_clock[0] += 1000
    second = await rule.evaluate(
        _pending_tx(_generic_call_calldata(), to=_OTHER_CONTRACT)
    )
    assert second is None


# -----------------------------------------------------------------------------
# Negative cases
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_does_not_fire_outside_window(fixed_clock: list[int]) -> None:
    state = InteractionState()
    rule = FreshApprovalNewContractRule(state, window_seconds=120)

    await rule.evaluate(_pending_tx(_approve_calldata(), to=_TOKEN))
    # Jump past the window.
    fixed_clock[0] += 200_000
    assert await rule.evaluate(
        _pending_tx(_generic_call_calldata(), to=_OTHER_CONTRACT)
    ) is None


@pytest.mark.asyncio
async def test_does_not_fire_without_prior_approval(fixed_clock: list[int]) -> None:
    state = InteractionState()
    rule = FreshApprovalNewContractRule(state, window_seconds=120)
    # No prior approval, just a fresh call.
    assert await rule.evaluate(
        _pending_tx(_generic_call_calldata(), to=_OTHER_CONTRACT)
    ) is None


@pytest.mark.asyncio
async def test_ignores_contract_creation(fixed_clock: list[int]) -> None:
    state = InteractionState()
    rule = FreshApprovalNewContractRule(state, window_seconds=120)
    await rule.evaluate(_pending_tx(_approve_calldata(), to=_TOKEN))
    fixed_clock[0] += 1000
    assert await rule.evaluate(
        _pending_tx(_generic_call_calldata(), to=None)
    ) is None
