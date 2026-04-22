"""T1.5 — fresh approval followed by a first-touch on a new contract.

Drainer escalation pattern: the victim signs an approval (T1.1 may also
fire if the spender is an EOA, but it doesn't have to — sophisticated
drainers route through innocuous-looking contracts). Shortly after, the
same address calls a contract it has never interacted with before. The
correlation of those two events inside a short window is the signal.

Spec says "within N blocks". Pending txs aren't in a block yet, so we
approximate with a wallclock window. Default 120 s ≈ 10 mainnet blocks
at 12 s slot time. Override via `T1_5_FRESH_APPROVAL_WINDOW_SECONDS`.

State lives in `InteractionState` (process-local for v1; persistence is
a follow-up). The rule mutates state during `evaluate` — this is allowed
by the engine contract — to record:

- approvals → updates `last_approval_ms`
- every tx with a `to_address` → adds the destination to the seen set

Order matters: we *check* "is this destination new?" *before* recording
it as seen. Otherwise the first-ever-touch would always look already-seen.
"""

from __future__ import annotations

import logging
import os
import time

from ...schemas import PendingTx, RuleHit
from ..interaction_state import InteractionState

log = logging.getLogger(__name__)


# Reuse the approval selectors from T1.1 / T1.4.
_APPROVE = "0x095ea7b3"
_INCREASE_ALLOWANCE = "0x39509351"
_SET_APPROVAL_FOR_ALL = "0xa22cb465"
_PERMIT = "0xd505accf"

_APPROVAL_SELECTORS = frozenset(
    {_APPROVE, _INCREASE_ALLOWANCE, _SET_APPROVAL_FOR_ALL, _PERMIT}
)


def _default_window_seconds() -> float:
    """Resolve the window from env, falling back to 120 s ≈ 10 ETH blocks."""
    raw = os.environ.get("T1_5_FRESH_APPROVAL_WINDOW_SECONDS")
    if raw is None:
        return 120.0
    try:
        value = float(raw)
    except ValueError:
        log.warning(
            "T1_5_FRESH_APPROVAL_WINDOW_SECONDS=%s is not a float; using default",
            raw,
        )
        return 120.0
    return max(value, 0.0)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _is_approval(input_data: str) -> bool:
    if len(input_data) < 10:
        return False
    return input_data[:10].lower() in _APPROVAL_SELECTORS


class FreshApprovalNewContractRule:
    """Flag a first-touch on a new contract within `window_s` of an approval."""

    rule_id = "t1.fresh_approval_new_contract"
    rule_version = "t1-v0.1"
    severity = "high"

    def __init__(
        self,
        state: InteractionState,
        *,
        window_seconds: float | None = None,
    ) -> None:
        self._state = state
        self._window_ms = int(
            (window_seconds if window_seconds is not None else _default_window_seconds())
            * 1000
        )

    async def evaluate(self, tx: PendingTx) -> RuleHit | None:
        # Contract creations skip — no destination to learn from.
        if tx.to_address is None:
            return None

        monitored = tx.from_address
        destination = tx.to_address
        now_ms = _now_ms()

        # Approval bookkeeping: an approval just primes the timer; it
        # doesn't itself produce a hit. T1.1 / T1.4 cover the approval
        # itself.
        if _is_approval(tx.input_data):
            self._state.record_approval(monitored, now_ms)
            self._state.record_destination(monitored, destination)
            return None

        # Non-approval, has a destination. Decide before mutating state.
        is_new_destination = not self._state.has_seen_destination(
            monitored, destination
        )
        last_approval_ms = self._state.last_approval_ms(monitored)

        try:
            if not is_new_destination:
                return None
            if last_approval_ms is None:
                return None
            elapsed_ms = now_ms - last_approval_ms
            if elapsed_ms < 0 or elapsed_ms > self._window_ms:
                return None
            return RuleHit(
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                severity=self.severity,
                reason_human=(
                    "First interaction with a new contract within "
                    f"{self._window_ms // 1000}s of a fresh approval "
                    "— possible drainer follow-through"
                ),
                reason_structured={
                    "destination_contract": destination,
                    "elapsed_ms_since_approval": elapsed_ms,
                    "window_ms": self._window_ms,
                },
            )
        finally:
            # Always learn from the tx, even when we fired — so a repeat
            # call to the same contract doesn't fire again.
            self._state.record_destination(monitored, destination)
