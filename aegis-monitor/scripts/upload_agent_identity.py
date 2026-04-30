"""Anchor the agent's signer pubkey on Arweave (one-shot, install-time).

Why anchor on Arweave: the signer address is published at
`/agent-identity`, but if it lives only on an Aegis-operated server a
malicious operator could swap it post-hoc to validate a forged signature.
Anchoring the address on Arweave at install time closes that gap — a
verifier can cross-check `/agent-identity` against an immutable record.

Spec: `docs/specs/arweave-flag-storage.md` §"Agent-identity anchoring".

Usage:

```
# Dry-run (default — no Arweave wallet required, prints what would be uploaded):
python -m scripts.upload_agent_identity \\
    --signing-key 0x... --agent-id aegis-monitor-prod

# Real upload (once Irys integration is wired):
python -m scripts.upload_agent_identity \\
    --signing-key 0x... --agent-id aegis-monitor-prod --uploader irys

# Rotation (publish a new identity that supersedes the previous one):
python -m scripts.upload_agent_identity \\
    --signing-key 0x... --agent-id aegis-monitor-prod \\
    --supersedes <prior_arweave_tx_id>
```

The script:

1. Builds the identity statement (agent_id, signer_address, ISO ts,
   optional `supersedes`).
2. Signs it with the same EIP-191 envelope the monitor uses for flag
   bodies — verifiers can reuse the existing verification flow.
3. Uploads via the configured `ArweaveUploader`.
4. Writes `infra/arweave-identity.json` so `/agent-identity` can serve
   the tx id without a runtime Arweave call.

The DryRun path lets operators rehearse the install on a new key
without an Irys wallet.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from eth_account import Account
from eth_account.messages import encode_defunct

from aegis_monitor.arweave.uploader import (
    ArweaveUploader,
    DryRunUploader,
    build_identity_tags,
)


def _canonical(payload: dict[str, object]) -> bytes:
    """Match the canonicalisation used by `AttestationBody.canonical_json`."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


async def _run(args: argparse.Namespace) -> int:
    raw_key = args.signing_key
    if raw_key.startswith("0x"):
        raw_key = raw_key[2:]
    if len(raw_key) != 64:
        print("error: signing-key must be 32 bytes (64 hex chars).", file=sys.stderr)
        return 2

    account = Account.from_key(bytes.fromhex(raw_key))
    signer_address = account.address

    body: dict[str, object] = {
        "agent_id": args.agent_id,
        "version": args.version,
        "signer_address": signer_address,
        "issued_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if args.supersedes:
        body["supersedes"] = args.supersedes
    body_bytes = _canonical(body)

    signed = account.sign_message(encode_defunct(body_bytes))
    sig_hex = "0x" + signed.signature.hex().lstrip("0x")
    payload_obj = {**body, "sig": sig_hex}
    payload_bytes = _canonical(payload_obj)

    uploader = _resolve_uploader(args.uploader)
    tags = build_identity_tags(agent_id=args.agent_id, signer_address=signer_address)
    tx_id = await uploader.upload(payload_bytes, tags)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_data = {
        "agent_id": args.agent_id,
        "signer_address": signer_address,
        "arweave_tx_id": tx_id,
        "issued_at": body["issued_at"],
        "uploader": args.uploader,
    }
    if args.supersedes:
        out_data["supersedes"] = args.supersedes
    out_path.write_text(json.dumps(out_data, indent=2, sort_keys=True) + "\n")

    print(
        f"agent_id        : {args.agent_id}\n"
        f"signer_address  : {signer_address}\n"
        f"arweave_tx_id   : {tx_id}\n"
        f"identity file   : {out_path}\n"
    )
    return 0


def _resolve_uploader(name: str) -> ArweaveUploader:
    if name == "dryrun":
        return DryRunUploader()
    if name == "irys":
        # Defer to keep the script importable even before the prod
        # uploader exists. The placeholder raises at construction.
        from aegis_monitor.arweave.uploader import IrysHttpUploader

        return IrysHttpUploader()
    raise ValueError(f"unknown uploader: {name!r} (expected 'dryrun' or 'irys')")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Anchor the aegis-monitor signer pubkey on Arweave."
    )
    parser.add_argument(
        "--signing-key",
        required=True,
        help="Agent EIP-191 private key (0x-prefixed 64-hex). Read from env in CI.",
    )
    parser.add_argument(
        "--agent-id",
        required=True,
        help="Stable agent identifier, e.g. 'aegis-monitor-prod'.",
    )
    parser.add_argument(
        "--version",
        default="0.1",
        help="Identity-statement version (default: 0.1).",
    )
    parser.add_argument(
        "--supersedes",
        default=None,
        help="Prior identity-statement Arweave tx id (for key rotation).",
    )
    parser.add_argument(
        "--uploader",
        choices=["dryrun", "irys"],
        default="dryrun",
        help="Arweave uploader to use. 'irys' requires the prod integration.",
    )
    parser.add_argument(
        "--out",
        default="infra/arweave-identity.json",
        help=(
            "Where to write the resulting identity manifest "
            "(default: infra/arweave-identity.json)."
        ),
    )
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
