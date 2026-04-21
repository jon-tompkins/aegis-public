"""Rule engine — runs all registered rules against each pending tx.

A `Rule` is a duck-typed object with a few attributes (`rule_id`,
`rule_version`, `severity`) and an async `evaluate(tx) -> RuleHit | None`.
The `Protocol` definition below documents that contract without forcing
inheritance.

`RuleRegistry.run_all` isolates each rule: an exception in one rule
doesn't stop the others from evaluating, and errors are logged with
enough context that we can trace the tx that triggered them.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from ..schemas import PendingTx, RuleHit

log = logging.getLogger(__name__)


@runtime_checkable
class Rule(Protocol):
    """Every rule implements this surface."""

    rule_id: str
    rule_version: str
    severity: str  # Severity literal from schemas

    async def evaluate(self, tx: PendingTx) -> RuleHit | None: ...


class RuleRegistry:
    def __init__(self, rules: list[Rule]) -> None:
        self._rules = list(rules)

    def __len__(self) -> int:
        return len(self._rules)

    def ids(self) -> list[str]:
        return [r.rule_id for r in self._rules]

    async def run_all(self, tx: PendingTx) -> list[RuleHit]:
        """Run every rule in registration order, collecting all hits.

        Crashed rules log and continue. A rule that happens to be buggy on
        one payload should not silently take the whole engine down.
        """
        hits: list[RuleHit] = []
        for rule in self._rules:
            try:
                hit = await rule.evaluate(tx)
            except Exception:
                log.exception(
                    "rule %s crashed on tx %s", rule.rule_id, tx.tx_hash
                )
                continue
            if hit is not None:
                hits.append(hit)
        return hits
