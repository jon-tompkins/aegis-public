"""EIP-191 signing for attestations.

The agent holds a single secp256k1 private key. For every rule hit we:

1. Build an `AttestationBody` from the tx + hit + agent context
2. Serialise it canonically (`body.canonical_json()` — sorted keys, no
   whitespace, UTF-8)
3. Wrap the bytes in the EIP-191 personal-sign envelope
   (`\x19Ethereum Signed Message:\n<len>` prefix)
4. Sign with the agent key, emitting r||s||v (65 bytes) as 0x-prefixed hex

Verifiers reverse the process: recompute `body.canonical_json()` on the
received fields and call `eth_account.Account.recover_message(...)` with
the sig — the recovered address must equal the agent's published public
key. If `canonical_json()` ever changes, every prior signature breaks;
see the schema docstring — treat it as a wire-format contract.

`AttestationSigner.build_and_sign()` is the hot-path entrypoint the
consumer uses: takes a `PendingTx`, the monitored address, and a
`RuleHit`, stamps `ts_ms`, and returns a fully-formed `Attestation`.
"""

from __future__ import annotations

import time

from eth_account import Account
from eth_account.messages import encode_defunct

from ..schemas import Attestation, AttestationBody, PendingTx, RuleHit


class AttestationSigner:
    def __init__(self, signing_key_hex: str, agent_id: str) -> None:
        if signing_key_hex.startswith("0x"):
            signing_key_hex = signing_key_hex[2:]
        if len(signing_key_hex) != 64:
            raise ValueError(
                "signing key must be 32 bytes (64 hex chars), with or without 0x prefix"
            )
        self._account = Account.from_key(bytes.fromhex(signing_key_hex))
        self._agent_id = agent_id

    @property
    def address(self) -> str:
        """Checksummed Ethereum address of the signing key — publish this for verifiers."""
        return self._account.address

    def sign(self, body: AttestationBody) -> Attestation:
        """Sign a pre-built body. Useful when the consumer has already chosen `ts_ms`."""
        message = encode_defunct(body.canonical_json())
        signed = self._account.sign_message(message)
        sig_hex = _to_0x_hex(signed.signature)
        return Attestation(**body.model_dump(), sig=sig_hex)

    def build_and_sign(
        self,
        *,
        tx: PendingTx,
        monitored_address: str,
        hit: RuleHit,
        ts_ms: int | None = None,
    ) -> Attestation:
        """Construct + sign in one step. Stamps `ts_ms` from wall-clock if omitted."""
        body = AttestationBody(
            tx_hash=tx.tx_hash,
            monitored_address=monitored_address,
            rule_id=hit.rule_id,
            rule_version=hit.rule_version,
            severity=hit.severity,
            reason_human=hit.reason_human,
            reason_structured=hit.reason_structured,
            agent_id=self._agent_id,
            ts_ms=ts_ms if ts_ms is not None else int(time.time() * 1000),
        )
        return self.sign(body)


def _to_0x_hex(value: object) -> str:
    """Coerce bytes-like or hex-string signatures into a 0x-prefixed lower-case hex string.

    `eth_account`'s signed-message object returns a `HexBytes` whose `.hex()`
    has varied between versions (sometimes includes the `0x` prefix, sometimes
    not). Normalising here protects the Attestation's strict 132-char sig
    validator.
    """
    if hasattr(value, "to_0x_hex"):
        try:
            return str(value.to_0x_hex()).lower()
        except Exception:
            pass  # fall through
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    s = str(value)
    return s.lower() if s.startswith("0x") else "0x" + s.lower()
