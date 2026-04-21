"""Rule registry behavior — ordering, exception isolation, hit collection."""

from __future__ import annotations

import pytest

from aegis_monitor.schemas import PendingTx, RuleHit
from aegis_monitor.screening.engine import Rule, RuleRegistry


def _make_tx() -> PendingTx:
    return PendingTx(
        tx_hash="0x" + "11" * 32,
        from_address="0x" + "22" * 20,
        to_address="0x" + "33" * 20,
        value_wei=0,
        input_data="0x",
        gas=21000,
        gas_price=0,
        nonce=0,
    )


class _FakeMatchRule:
    rule_id = "fake.match"
    rule_version = "v0.1"
    severity = "high"

    async def evaluate(self, tx: PendingTx) -> RuleHit | None:
        return RuleHit(
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            severity=self.severity,
            reason_human="matched",
            reason_structured={"tx": tx.tx_hash},
        )


class _FakeSilentRule:
    rule_id = "fake.silent"
    rule_version = "v0.1"
    severity = "low"

    async def evaluate(self, tx: PendingTx) -> RuleHit | None:
        return None


class _FakeCrashRule:
    rule_id = "fake.crash"
    rule_version = "v0.1"
    severity = "medium"

    async def evaluate(self, tx: PendingTx) -> RuleHit | None:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_registry_collects_only_hits() -> None:
    reg = RuleRegistry([_FakeMatchRule(), _FakeSilentRule()])
    hits = await reg.run_all(_make_tx())
    assert len(hits) == 1
    assert hits[0].rule_id == "fake.match"


@pytest.mark.asyncio
async def test_crashing_rule_does_not_stop_others() -> None:
    reg = RuleRegistry([_FakeCrashRule(), _FakeMatchRule()])
    hits = await reg.run_all(_make_tx())
    # The crash is logged but swallowed; fake.match still fires.
    assert [h.rule_id for h in hits] == ["fake.match"]


@pytest.mark.asyncio
async def test_empty_registry_returns_empty() -> None:
    reg = RuleRegistry([])
    hits = await reg.run_all(_make_tx())
    assert hits == []


def test_registry_ids_preserves_order() -> None:
    reg = RuleRegistry([_FakeMatchRule(), _FakeSilentRule(), _FakeCrashRule()])
    assert reg.ids() == ["fake.match", "fake.silent", "fake.crash"]
    assert len(reg) == 3


def test_rule_protocol_matches_fakes() -> None:
    # The runtime_checkable Protocol should accept our fakes — guards against
    # accidental signature drift.
    assert isinstance(_FakeMatchRule(), Rule)
    assert isinstance(_FakeSilentRule(), Rule)
