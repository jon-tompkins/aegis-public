"""End-to-end pipeline test: payload → parse → rule → sign → verify.

Walks realistic Alchemy subscription payloads through the full screening
path, stubs the bytecode checker from per-scenario lookup data, asserts
that each scenario ends in the expected outcome (flag fires or not), and
for flag-firing scenarios verifies the attestation signature recovers to
the signer's published address.

DB insertion and WS broadcast are covered separately — this test
focuses on the in-memory pipeline so it can run without infrastructure.
"""

from __future__ import annotations

from typing import Any

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct

from aegis_monitor.attestation.signer import AttestationSigner
from aegis_monitor.mempool.parser import parse_pending_tx
from aegis_monitor.screening.engine import RuleRegistry
from aegis_monitor.screening.rules.approve_to_eoa import ApproveToEoaRule

from .fixtures.alchemy_payloads import ALL_SCENARIOS


_TEST_KEY = "0x" + "22" * 32


class _StubBytecode:
    """Stand-in for BytecodeChecker using a static lookup table."""

    def __init__(self, lookup: dict[str, bool]) -> None:
        # Default missing entries to "no code" so scenarios that skip the
        # bytecode check (non-approval selectors) don't need to populate it.
        self._lookup = {k.lower(): v for k, v in lookup.items()}

    async def has_code(self, address: str) -> bool:
        return self._lookup.get(address.lower(), False)


@pytest.mark.parametrize(
    "name, factory",
    ALL_SCENARIOS,
    ids=[s[0] for s in ALL_SCENARIOS],
)
@pytest.mark.asyncio
async def test_pipeline_scenario(name: str, factory: Any) -> None:
    payload, bytecode_lookup, should_fire = factory()

    tx = parse_pending_tx(payload)
    registry = RuleRegistry([ApproveToEoaRule(_StubBytecode(bytecode_lookup))])
    hits = await registry.run_all(tx)

    if not should_fire:
        assert hits == [], f"scenario {name} fired unexpectedly: {hits}"
        return

    assert len(hits) == 1, f"scenario {name} expected 1 hit, got {len(hits)}"
    hit = hits[0]

    # Sign the hit and verify the signature recovers to the signer.
    signer = AttestationSigner(_TEST_KEY, agent_id="integration-test")
    attestation = signer.build_and_sign(tx=tx, monitored_address=tx.from_address, hit=hit)

    # Independent verification — mirrors what a third party would do.
    canonical = attestation.model_copy(update={}).model_dump(mode="json")
    # Exclude sig from recovery input — verifiers recompute body bytes.
    body_only = {k: v for k, v in canonical.items() if k != "sig"}
    from aegis_monitor.schemas import AttestationBody

    body = AttestationBody(**body_only)
    message = encode_defunct(body.canonical_json())
    recovered = Account.recover_message(message, signature=attestation.sig)
    assert recovered.lower() == signer.address.lower()

    # Sanity: attestation carries the rule identity.
    assert attestation.rule_id == "t1.approve_to_eoa"
    assert attestation.severity == "high"
    assert attestation.monitored_address == tx.from_address.lower()


@pytest.mark.asyncio
async def test_pipeline_multi_tx_distinct_signatures() -> None:
    """Every flag produces a distinct, individually-verifiable signature."""
    drainer_factory = [
        f for name, f in ALL_SCENARIOS if "eoa" in name and f()[2]
    ]
    assert len(drainer_factory) >= 2

    signer = AttestationSigner(_TEST_KEY, agent_id="integration-test")
    sigs: set[str] = set()

    for factory in drainer_factory:
        payload, lookup, _ = factory()
        tx = parse_pending_tx(payload)
        registry = RuleRegistry([ApproveToEoaRule(_StubBytecode(lookup))])
        hits = await registry.run_all(tx)
        assert hits
        att = signer.build_and_sign(tx=tx, monitored_address=tx.from_address, hit=hits[0])
        sigs.add(att.sig)

    # Different tx_hashes + timestamps = different sigs.
    assert len(sigs) == len(drainer_factory)
