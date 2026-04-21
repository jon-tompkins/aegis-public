"""T1.1 + T1.2 — approval / setApprovalForAll to an EOA.

The wallet-drainer pattern: victim signs an `approve`, `increaseAllowance`,
`setApprovalForAll`, or `permit` to an address that is not a contract.
Legitimate approvals go to DEX routers, NFT marketplaces, etc. — all
contracts. Approvals to EOAs are almost always drainer payloads.

Method coverage:

| Selector      | Method              | Spender arg position |
|---------------|---------------------|----------------------|
| `0x095ea7b3`  | approve             | arg0                 |
| `0x39509351`  | increaseAllowance   | arg0                 |
| `0xa22cb465`  | setApprovalForAll   | arg0 (operator)      |
| `0xd505accf`  | permit (EIP-2612)   | arg1 (after owner)   |

All return addresses decoded from the standard ABI encoding (address
right-aligned in a 32-byte word — we read the last 40 hex chars).
"""

from __future__ import annotations

import logging

from ...schemas import PendingTx, RuleHit
from ..bytecode import BytecodeChecker

log = logging.getLogger(__name__)


_APPROVE = "0x095ea7b3"
_INCREASE_ALLOWANCE = "0x39509351"
_SET_APPROVAL_FOR_ALL = "0xa22cb465"
_PERMIT = "0xd505accf"

_METHODS: dict[str, str] = {
    _APPROVE: "approve",
    _INCREASE_ALLOWANCE: "increaseAllowance",
    _SET_APPROVAL_FOR_ALL: "setApprovalForAll",
    _PERMIT: "permit",
}

# Methods where the spender/operator sits in arg0 (first 32-byte slot after
# the 4-byte selector). `permit` is the exception — owner in arg0, spender
# in arg1.
_SPENDER_IN_ARG0 = {_APPROVE, _INCREASE_ALLOWANCE, _SET_APPROVAL_FOR_ALL}


def _decode_spender(input_data: str, selector: str) -> str | None:
    """Pull the spender/operator address from ABI-encoded calldata.

    Returns a lower-case 0x-prefixed address or None if the calldata is
    shorter than expected.
    """
    # Strip "0x" + 4-byte selector (8 hex chars) = 10 chars.
    calldata = input_data[10:]
    if selector in _SPENDER_IN_ARG0:
        if len(calldata) < 64:
            return None
        arg_slot = calldata[:64]
    elif selector == _PERMIT:
        if len(calldata) < 128:
            return None
        arg_slot = calldata[64:128]
    else:
        return None
    # Address is the last 20 bytes (40 hex) of the 32-byte slot.
    return "0x" + arg_slot[-40:].lower()


class ApproveToEoaRule:
    """Flag ERC-20 / ERC-721 approvals whose spender has no contract bytecode."""

    rule_id = "t1.approve_to_eoa"
    rule_version = "t1-v0.1"
    severity = "high"

    def __init__(self, bytecode: BytecodeChecker) -> None:
        self._bytecode = bytecode

    async def evaluate(self, tx: PendingTx) -> RuleHit | None:
        if tx.to_address is None:
            return None  # contract creation, not an approval

        if len(tx.input_data) < 10:
            return None
        selector = tx.input_data[:10].lower()
        method = _METHODS.get(selector)
        if method is None:
            return None

        spender = _decode_spender(tx.input_data, selector)
        if spender is None:
            return None

        if await self._bytecode.has_code(spender):
            return None  # approval is to a contract; fine

        return RuleHit(
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            severity=self.severity,
            reason_human=(
                f"{method} granted to an address with no contract code "
                "(likely wallet-drainer pattern)"
            ),
            reason_structured={
                "method": method,
                "selector": selector,
                "token_contract": tx.to_address,
                "spender": spender,
            },
        )
