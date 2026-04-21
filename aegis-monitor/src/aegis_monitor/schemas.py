"""Pydantic models shared across the agent.

Three groups:

1. **Inbound** — `MonitorRequest`, `PendingTx`. What we accept from clients
   (HTTP) and the mempool feed (Alchemy WS).
2. **Internal** — `RuleHit`. What a rule emits when it fires.
3. **Outbound** — `AttestationBody`, `Attestation`, `FlagResponse`. The
   canonical signed flag and its API envelope.

EIP-191 signing contract: `AttestationBody.canonical_json()` is the exact
byte sequence passed to the signer. Any change to that method is a
breaking protocol change — bump a version string, don't silently alter.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# -----------------------------------------------------------------------------
# Primitive types
# -----------------------------------------------------------------------------

Severity = Literal["low", "medium", "high", "critical"]

_HEX_ADDRESS_LEN = 42  # "0x" + 40 hex
_TX_HASH_LEN = 66  # "0x" + 64 hex


def _is_hex_address(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _HEX_ADDRESS_LEN
        and value.startswith("0x")
        and all(c in "0123456789abcdefABCDEF" for c in value[2:])
    )


def _is_tx_hash(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _TX_HASH_LEN
        and value.startswith("0x")
        and all(c in "0123456789abcdefABCDEF" for c in value[2:])
    )


# -----------------------------------------------------------------------------
# Inbound
# -----------------------------------------------------------------------------


class MonitorRequest(BaseModel):
    """Body for `POST /monitor` — add an address to the watch set."""

    address: str = Field(description="EIP-55 or lower-case hex address, 0x-prefixed")

    @field_validator("address")
    @classmethod
    def _validate_address(cls, v: str) -> str:
        if not _is_hex_address(v):
            raise ValueError("address must be a 0x-prefixed 40-hex-char string")
        return v.lower()


class PendingTx(BaseModel):
    """Decoded pending transaction from the Alchemy WS feed.

    We keep the raw payload alongside the parsed fields so rule debugging
    can always reach for the source-of-truth structure without a round trip.
    """

    model_config = ConfigDict(frozen=True)

    tx_hash: str
    from_address: str
    to_address: str | None = Field(default=None, description="None on contract creation")
    value_wei: int = Field(ge=0)
    input_data: str = Field(description="0x-prefixed hex calldata")
    gas: int = Field(ge=0)
    gas_price: int = Field(ge=0)
    nonce: int = Field(ge=0)
    chain_id: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict, description="Original WS payload")

    @field_validator("tx_hash")
    @classmethod
    def _validate_tx_hash(cls, v: str) -> str:
        if not _is_tx_hash(v):
            raise ValueError("tx_hash must be a 0x-prefixed 64-hex-char string")
        return v.lower()

    @field_validator("from_address")
    @classmethod
    def _validate_from(cls, v: str) -> str:
        if not _is_hex_address(v):
            raise ValueError("from_address must be a 0x-prefixed 40-hex-char string")
        return v.lower()

    @field_validator("to_address")
    @classmethod
    def _validate_to(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not _is_hex_address(v):
            raise ValueError("to_address must be a 0x-prefixed 40-hex-char string or None")
        return v.lower()

    @field_validator("input_data")
    @classmethod
    def _validate_input(cls, v: str) -> str:
        if not (isinstance(v, str) and v.startswith("0x") and all(
            c in "0123456789abcdefABCDEF" for c in v[2:]
        )):
            raise ValueError("input_data must be a 0x-prefixed hex string")
        return v.lower()


# -----------------------------------------------------------------------------
# Internal: rule output
# -----------------------------------------------------------------------------


class RuleHit(BaseModel):
    """A single rule deciding that a tx matches its pattern.

    `reason_structured` is intentionally free-form JSON — rules decide what
    machine-readable context is useful (spender, token, amount hex, etc.).
    `reason_human` is a single short sentence suitable for UI display.
    """

    rule_id: str = Field(description="Stable id, e.g. 't1.approve_to_eoa'")
    rule_version: str = Field(description="Version tag for the rule logic, e.g. 't1-v0.1'")
    severity: Severity
    reason_human: str = Field(min_length=1, max_length=280)
    reason_structured: dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# Outbound: attestations
# -----------------------------------------------------------------------------


class AttestationBody(BaseModel):
    """Canonical signed body of a flag attestation.

    `canonical_json()` produces the exact bytes signed by the agent key under
    EIP-191. Verifiers recompute the same canonical form and recover the
    signer from `sig` — if the recovered address matches the agent's
    published public key, the attestation is authentic.

    Stability matters: any change to the canonical serialisation (field
    order, whitespace, key names) breaks every prior signature. Treat this
    class as a wire-format contract.
    """

    model_config = ConfigDict(frozen=True)

    tx_hash: str
    monitored_address: str
    rule_id: str
    rule_version: str
    severity: Severity
    reason_human: str
    reason_structured: dict[str, Any] = Field(default_factory=dict)
    agent_id: str
    ts_ms: int = Field(ge=0, description="Unix epoch milliseconds")

    @field_validator("tx_hash")
    @classmethod
    def _validate_tx_hash(cls, v: str) -> str:
        if not _is_tx_hash(v):
            raise ValueError("tx_hash must be a 0x-prefixed 64-hex-char string")
        return v.lower()

    @field_validator("monitored_address")
    @classmethod
    def _validate_address(cls, v: str) -> str:
        if not _is_hex_address(v):
            raise ValueError("monitored_address must be a 0x-prefixed 40-hex-char string")
        return v.lower()

    def canonical_json(self) -> bytes:
        """Deterministic JSON encoding: sorted keys, no whitespace, UTF-8.

        This is the exact byte sequence the EIP-191 signer ingests. Do not
        pretty-print. Do not reorder fields. If the protocol wants a change,
        bump `rule_version` or add a versioned wrapper — never mutate this
        function quietly.
        """
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")


class Attestation(AttestationBody):
    """Body + signature. What we persist and what the API returns."""

    sig: str = Field(description="0x-prefixed EIP-191 signature (65 bytes, r||s||v)")

    @field_validator("sig")
    @classmethod
    def _validate_sig(cls, v: str) -> str:
        # 0x + 65 bytes hex = 2 + 130 chars
        if not (isinstance(v, str) and v.startswith("0x") and len(v) == 132 and all(
            c in "0123456789abcdefABCDEF" for c in v[2:]
        )):
            raise ValueError("sig must be a 0x-prefixed 130-hex-char EIP-191 signature")
        return v.lower()


# -----------------------------------------------------------------------------
# Outbound: API envelopes
# -----------------------------------------------------------------------------


class FlagResponse(BaseModel):
    """One row from `GET /flags` — persistence id + full attestation."""

    id: int
    attestation: Attestation
    created_at: datetime
