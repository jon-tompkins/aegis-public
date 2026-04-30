"""Arweave uploader abstraction.

The rest of the system depends only on the `ArweaveUploader` protocol:
"give me bytes + tags, get back an Arweave tx id". Every concrete
implementation must satisfy that contract — the writer task and the
identity-anchoring script are uploader-agnostic.

Two implementations live here:

- **`DryRunUploader`** — deterministic, offline. Returns a fake tx id
  derived from a SHA-256 of the payload + tags. Used in tests and as
  the default for local dev where no Irys wallet exists. Logs every
  upload at INFO so an operator can sanity-check what would have been
  published.

- **`IrysHttpUploader`** — placeholder for the production path. The
  real Irys (Bundlr) data-item format requires either signing
  data-items in Python (currently no first-class library — would mean
  porting a chunk of `@dha-team/arbundles`) or running a small Node.js
  sidecar that exposes the JS SDK over HTTP. Both paths are realistic;
  picking one is an operator decision that needs Jonto's input + an
  Irys-funded wallet before it's worth implementing. Until then this
  class raises on instantiation so we can't accidentally ship a no-op
  uploader to prod.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Tag:
    """One Arweave transaction tag. Both name and value are user-facing
    metadata indexed by gateways' GraphQL endpoints. We keep them ASCII —
    not a protocol requirement, but it sidesteps gateway quirks."""

    name: str
    value: str

    def __post_init__(self) -> None:
        if not self.name or not self.value:
            raise ValueError("tag name and value must be non-empty")


class ArweaveUploader(Protocol):
    """Minimal contract for publishing a canonical flag body."""

    async def upload(self, payload: bytes, tags: list[Tag]) -> str:
        """Publish `payload` to Arweave with `tags`. Return the tx id.

        Implementations MUST raise on failure rather than swallowing —
        the writer task's retry loop is the only place that decides
        what to do with transient errors.
        """


log = logging.getLogger(__name__)


class DryRunUploader:
    """Offline uploader. Returns a deterministic fake tx id; logs the
    intended upload at INFO so it's visible in dev/CI output.

    Determinism matters: the same payload always hashes to the same
    "tx id" so tests and devs can assert against expected values.
    """

    def __init__(self, prefix: str = "dryrun-") -> None:
        self._prefix = prefix

    async def upload(self, payload: bytes, tags: list[Tag]) -> str:
        tag_repr = ",".join(f"{t.name}={t.value}" for t in tags)
        log.info(
            "DRY-RUN arweave upload: bytes=%d tags=[%s]",
            len(payload),
            tag_repr,
        )
        h = hashlib.sha256()
        h.update(payload)
        for t in tags:
            h.update(t.name.encode("utf-8"))
            h.update(b"=")
            h.update(t.value.encode("utf-8"))
            h.update(b";")
        # Arweave tx ids are ~43 chars (base64url of 32 bytes). Match the
        # shape so downstream consumers (gateway URLs, tests) treat the
        # output as plausible.
        import base64

        suffix = base64.urlsafe_b64encode(h.digest()).rstrip(b"=").decode("ascii")
        return f"{self._prefix}{suffix}"


class IrysHttpUploader:
    """Real Irys / Bundlr integration — not yet wired.

    Implementing this means either (a) porting Bundlr data-item signing
    to Python, or (b) running a Node.js sidecar that exposes the Irys
    SDK over an internal HTTP endpoint. Both paths need an Irys-funded
    wallet (USDC top-up) and an operator decision before the work is
    worth doing. Until then, instantiation fails fast so we don't ship
    a silently-broken uploader.
    """

    def __init__(self) -> None:  # pragma: no cover — guard rail
        raise NotImplementedError(
            "Irys uploader not implemented. See docs/specs/arweave-flag-storage.md "
            "§'Bundler choice' for the two integration paths and required operator inputs."
        )

    async def upload(self, payload: bytes, tags: list[Tag]) -> str:  # pragma: no cover
        raise NotImplementedError


# -----------------------------------------------------------------------------
# Tag helpers
# -----------------------------------------------------------------------------


_APP_NAME = "aegis-monitor"
_APP_VERSION = "0.1"
_CONTENT_TYPE = "application/json"


def build_flag_tags(
    *,
    agent_id: str,
    tx_hash: str,
    monitored_address: str,
    rule_id: str,
    rule_version: str,
    severity: str,
    ts_ms: int,
) -> list[Tag]:
    """Tags attached to a flag-attestation Arweave tx.

    Tags are a discoverability index, not a trust surface — the canonical
    body is authoritative. Anyone running a GraphQL query against an
    Arweave gateway can use these to reconstruct full flag history without
    our help (`App-Name = aegis-monitor`).
    """
    return [
        Tag("App-Name", _APP_NAME),
        Tag("App-Version", _APP_VERSION),
        Tag("Content-Type", _CONTENT_TYPE),
        Tag("Aegis-Agent-Id", agent_id),
        Tag("Aegis-Tx-Hash", tx_hash),
        Tag("Aegis-Monitored-Addr", monitored_address),
        Tag("Aegis-Rule-Id", rule_id),
        Tag("Aegis-Rule-Version", rule_version),
        Tag("Aegis-Severity", severity),
        Tag("Aegis-Ts-Ms", str(ts_ms)),
    ]


def build_identity_tags(*, agent_id: str, signer_address: str) -> list[Tag]:
    """Tags attached to the one-shot agent-identity statement on Arweave."""
    return [
        Tag("App-Name", _APP_NAME),
        Tag("App-Version", _APP_VERSION),
        Tag("App-Type", "identity"),
        Tag("Content-Type", _CONTENT_TYPE),
        Tag("Aegis-Agent-Id", agent_id),
        Tag("Aegis-Signer-Address", signer_address),
    ]
