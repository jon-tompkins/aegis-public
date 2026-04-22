"""T1.4 — unlimited or outsized token approval.

Two tiers, both target the same wallet-drainer concern from a different
angle than T1.1 (which focuses on the *spender* being an EOA).

| Pattern                              | Severity | Reason                       |
|--------------------------------------|----------|------------------------------|
| `amount == uint256.max`              | high     | Effectively unlimited mint   |
| `amount > 10 × balanceOf(owner)`     | medium   | Outsized vs current holdings |

A signature change to use historical max-ever balance instead of current
balance is a follow-up — `balance_of` is a single RPC and good enough as
a v1 baseline. The 10× multiplier and the unlimited threshold are the
two bound knobs and live in `_OUTSIZED_MULTIPLIER` / `_UINT256_MAX`.

Selectors covered: `approve`, `increaseAllowance`, `permit`. We
deliberately skip `setApprovalForAll` — it's a boolean toggle, not an
amount, and is already covered by T1.1 when the operator is an EOA.

Fires independently of T1.1, so a single tx can produce two attestations
(approve-to-EOA + outsized-approve). The engine deduplicates nothing; we
want both signals on the wire.
"""

from __future__ import annotations

import logging

from ...schemas import PendingTx, RuleHit
from ..erc20 import Erc20Reader

log = logging.getLogger(__name__)


_APPROVE = "0x095ea7b3"
_INCREASE_ALLOWANCE = "0x39509351"
_PERMIT = "0xd505accf"

_UINT256_MAX = (1 << 256) - 1
_OUTSIZED_MULTIPLIER = 10


def _decode_approve_amount(input_data: str) -> tuple[str, int] | None:
    """`approve` / `increaseAllowance`: arg0=spender, arg1=amount.

    Returns `(owner, amount)` where owner is `tx.from_address` semantically;
    we let the caller wire that up rather than passing it in here.
    """
    calldata = input_data[10:]
    if len(calldata) < 128:
        return None
    spender = "0x" + calldata[24:64].lower()
    try:
        amount = int(calldata[64:128], 16)
    except ValueError:
        return None
    return spender, amount


def _decode_permit(input_data: str) -> tuple[str, str, int] | None:
    """`permit(owner, spender, value, deadline, v, r, s)`.

    Returns `(owner, spender, value)`. Owner is the on-chain signer of the
    permit, not the relaying tx sender — relayers are common.
    """
    calldata = input_data[10:]
    if len(calldata) < 128:
        return None
    owner = "0x" + calldata[24:64].lower()
    spender = "0x" + calldata[88:128].lower()
    if len(calldata) < 192:
        return None
    try:
        value = int(calldata[128:192], 16)
    except ValueError:
        return None
    return owner, spender, value


class UnlimitedApprovalRule:
    """Flag approvals whose amount is unlimited or outsized vs. balance."""

    rule_id = "t1.unlimited_approval"
    rule_version = "t1-v0.1"
    # Default severity — overridden per hit (high for unlimited, medium otherwise).
    severity = "medium"

    def __init__(self, erc20: Erc20Reader) -> None:
        self._erc20 = erc20

    async def evaluate(self, tx: PendingTx) -> RuleHit | None:
        if tx.to_address is None:
            return None
        if len(tx.input_data) < 10:
            return None
        selector = tx.input_data[:10].lower()

        if selector in (_APPROVE, _INCREASE_ALLOWANCE):
            decoded = _decode_approve_amount(tx.input_data)
            if decoded is None:
                return None
            spender, amount = decoded
            owner = tx.from_address
            method = "approve" if selector == _APPROVE else "increaseAllowance"
        elif selector == _PERMIT:
            decoded_p = _decode_permit(tx.input_data)
            if decoded_p is None:
                return None
            owner, spender, amount = decoded_p
            method = "permit"
        else:
            return None

        token = tx.to_address

        if amount == _UINT256_MAX:
            return RuleHit(
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                severity="high",
                reason_human=(
                    f"{method} grants unlimited (uint256.max) allowance"
                ),
                reason_structured={
                    "method": method,
                    "selector": selector,
                    "token_contract": token,
                    "owner": owner,
                    "spender": spender,
                    "amount": str(amount),
                    "trigger": "uint256_max",
                },
            )

        # Outsized vs current balance. RPC failure → skip (don't flag on
        # missing data).
        balance = await self._erc20.balance_of(token, owner)
        if balance is None:
            return None
        # A zero balance with any non-zero approval looks suspicious but
        # we don't fire on that alone — could be a legitimate pre-funding
        # workflow. Require an actual balance for the multiplier to mean
        # something.
        if balance == 0:
            return None
        if amount > _OUTSIZED_MULTIPLIER * balance:
            return RuleHit(
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                severity="medium",
                reason_human=(
                    f"{method} amount is {amount // balance}× the owner's "
                    f"current balance — outsized vs holdings"
                ),
                reason_structured={
                    "method": method,
                    "selector": selector,
                    "token_contract": token,
                    "owner": owner,
                    "spender": spender,
                    "amount": str(amount),
                    "owner_balance": str(balance),
                    "multiplier_threshold": _OUTSIZED_MULTIPLIER,
                    "trigger": "outsized_vs_balance",
                },
            )

        return None
