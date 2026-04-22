"""T1.3 — transferFrom invoked by an unauthorized caller.

Drainer pattern: attacker has somehow obtained a valid signature or stolen
key path, then calls `transferFrom(victim, attackerEOA, …)` with their own
address as `msg.sender`. If the attacker has neither been granted an
allowance nor been set as approval-for-all, the call will revert on-chain
— but a *pending* tx can still be flagged so the victim is warned before
inclusion (e.g. front-runnable cancel via higher-gas replacement).

Decision logic for a pending `transferFrom(owner, recipient, amount)`:

| Condition                                     | Outcome |
|----------------------------------------------|---------|
| `tx.from_address == owner`                   | OK — owner moving own tokens |
| `allowance(token, owner, msg.sender) >= amount` | OK — properly approved (ERC-20) |
| `isApprovedForAll(token, owner, msg.sender) == true` | OK — properly approved (ERC-721) |
| anything else                                | FLAG    |

Both `eth_call`s can return `None` (RPC failure / non-conforming contract).
On `None` we treat the lookup as inconclusive and skip the rule rather
than firing on guesswork.
"""

from __future__ import annotations

import logging

from ...schemas import PendingTx, RuleHit
from ..erc20 import Erc20Reader

log = logging.getLogger(__name__)


_TRANSFER_FROM = "0x23b872dd"  # transferFrom(address,address,uint256)


def _decode_transfer_from(input_data: str) -> tuple[str, str, int] | None:
    """Decode `(owner, recipient, amount_or_tokenId)` from calldata.

    Returns None if the calldata is shorter than the three required slots.
    """
    calldata = input_data[10:]  # strip "0x" + selector
    if len(calldata) < 192:  # 3 × 64
        return None
    owner = "0x" + calldata[24:64].lower()
    recipient = "0x" + calldata[88:128].lower()
    try:
        amount = int(calldata[128:192], 16)
    except ValueError:
        return None
    return owner, recipient, amount


class TransferFromUnauthorizedRule:
    """Flag `transferFrom` whose `msg.sender` lacks an allowance from `owner`."""

    rule_id = "t1.transfer_from_unauthorized"
    rule_version = "t1-v0.1"
    severity = "critical"

    def __init__(self, erc20: Erc20Reader) -> None:
        self._erc20 = erc20

    async def evaluate(self, tx: PendingTx) -> RuleHit | None:
        if tx.to_address is None:
            return None  # contract creation
        if len(tx.input_data) < 10:
            return None
        if tx.input_data[:10].lower() != _TRANSFER_FROM:
            return None

        decoded = _decode_transfer_from(tx.input_data)
        if decoded is None:
            return None
        owner, recipient, amount_or_token_id = decoded

        # Owner moving their own tokens — always allowed.
        if owner.lower() == tx.from_address.lower():
            return None

        token = tx.to_address
        spender = tx.from_address

        allowance = await self._erc20.allowance(token, owner, spender)
        if allowance is not None and allowance >= amount_or_token_id:
            return None

        # ERC-721 fallback: if allowance is missing/insufficient, check
        # `isApprovedForAll`. Covers the NFT case where transferFrom
        # carries a tokenId rather than an amount.
        approved_for_all = await self._erc20.is_approved_for_all(
            token, owner, spender
        )
        if approved_for_all is True:
            return None

        # Both lookups returned None → can't determine; skip rather than
        # flag a tx we don't understand.
        if allowance is None and approved_for_all is None:
            log.debug(
                "transferFrom skipped — both allowance + isApprovedForAll "
                "returned None for token=%s owner=%s spender=%s",
                token, owner, spender,
            )
            return None

        return RuleHit(
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            severity=self.severity,
            reason_human=(
                "transferFrom called by an address with no allowance "
                "from the owner — possible stolen-key drainer pattern"
            ),
            reason_structured={
                "method": "transferFrom",
                "selector": _TRANSFER_FROM,
                "token_contract": token,
                "owner": owner,
                "recipient": recipient,
                "spender": spender,
                "amount_or_token_id": str(amount_or_token_id),
                "allowance": None if allowance is None else str(allowance),
            },
        )
