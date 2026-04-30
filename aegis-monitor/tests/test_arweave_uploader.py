"""Tests for the Arweave uploader abstraction.

The DryRunUploader is the only concrete implementation that ships with
Phase 1a — it has to be deterministic so tests and dev environments can
assert against expected output. Tag construction is part of the public
contract too; if these helpers drift, third-party indexers stop seeing
our flags under their existing GraphQL queries.
"""

from __future__ import annotations

import asyncio

import pytest

from aegis_monitor.arweave.uploader import (
    DryRunUploader,
    Tag,
    build_flag_tags,
    build_identity_tags,
)


def _payload() -> bytes:
    return b'{"agent_id":"aegis-monitor-01","ts_ms":1}'


def _tags() -> list[Tag]:
    return [
        Tag("App-Name", "aegis-monitor"),
        Tag("Aegis-Agent-Id", "aegis-monitor-01"),
    ]


def test_tag_rejects_empty_fields() -> None:
    with pytest.raises(ValueError):
        Tag("", "x")
    with pytest.raises(ValueError):
        Tag("x", "")


def test_dry_run_upload_is_deterministic() -> None:
    u = DryRunUploader()
    a = asyncio.run(u.upload(_payload(), _tags()))
    b = asyncio.run(u.upload(_payload(), _tags()))
    assert a == b
    assert a.startswith("dryrun-")
    # Suffix is base64url of a 32-byte hash → ~43 chars (with no padding).
    assert 40 <= len(a) - len("dryrun-") <= 44


def test_dry_run_upload_changes_with_payload() -> None:
    u = DryRunUploader()
    a = asyncio.run(u.upload(_payload(), _tags()))
    b = asyncio.run(u.upload(_payload() + b"x", _tags()))
    assert a != b


def test_dry_run_upload_changes_with_tags() -> None:
    u = DryRunUploader()
    a = asyncio.run(u.upload(_payload(), _tags()))
    b = asyncio.run(
        u.upload(
            _payload(),
            [Tag("App-Name", "aegis-monitor"), Tag("Aegis-Agent-Id", "different")],
        )
    )
    assert a != b


def test_build_flag_tags_includes_required_keys() -> None:
    tags = build_flag_tags(
        agent_id="aegis-monitor-01",
        tx_hash="0x" + "ab" * 32,
        monitored_address="0x" + "cd" * 20,
        rule_id="t1.approve_to_eoa",
        rule_version="t1-v0.1",
        severity="high",
        ts_ms=1_700_000_000_000,
    )
    names = {t.name for t in tags}
    # These are the names that public GraphQL queries will key off — if
    # any of them rename, third-party indexers silently lose visibility.
    assert {
        "App-Name",
        "App-Version",
        "Content-Type",
        "Aegis-Agent-Id",
        "Aegis-Tx-Hash",
        "Aegis-Monitored-Addr",
        "Aegis-Rule-Id",
        "Aegis-Rule-Version",
        "Aegis-Severity",
        "Aegis-Ts-Ms",
    }.issubset(names)


def test_build_identity_tags_marks_app_type() -> None:
    tags = build_identity_tags(
        agent_id="aegis-monitor-01",
        signer_address="0xabc",
    )
    pairs = {t.name: t.value for t in tags}
    # `App-Type=identity` is what lets a verifier discriminate between
    # flag attestations and identity statements at query time.
    assert pairs["App-Type"] == "identity"
    assert pairs["Aegis-Agent-Id"] == "aegis-monitor-01"
    assert pairs["Aegis-Signer-Address"] == "0xabc"
