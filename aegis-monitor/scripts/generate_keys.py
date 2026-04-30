"""Generate the Phase 1a signing keypair for `aegis-monitor`.

Why a script: the monitor signs attestations under EIP-191. The
private key has to be generated *somewhere* before it can land in AWS
Secrets Manager. Generating on a laptop, writing to stdout, and copying
into Secrets Manager once is cleaner than letting Terraform create
random keys (Terraform state files end up holding the private key —
something we want to avoid).

Usage:

```
python -m scripts.generate_keys              # prints to stdout
python -m scripts.generate_keys --json       # JSON payload, easy to pipe into AWS
python -m scripts.generate_keys --quiet      # private key only, for automation
```

Operator runbook reference: `docs/specs/arweave-flag-storage.md`
§"Operator checklist".

Security:

- The private key is printed to stdout. Run on a trusted machine and
  pipe directly into Secrets Manager (`aws secretsmanager put-secret-
  value`) — don't commit it, don't paste it into chat, don't leave it
  in shell history (`HISTCONTROL=ignorespace` + a leading space).
- The public address is safe to publish — it's what verifiers use to
  authenticate every attestation we sign.
- We deliberately don't write to disk. If you need a file, redirect
  stdout yourself and own the lifecycle.
"""

from __future__ import annotations

import argparse
import json
import sys

from eth_account import Account


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a fresh secp256k1 keypair for aegis-monitor's EIP-191 signer. "
            "Prints the private key + public address to stdout. Pipe into Secrets Manager."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a single JSON object instead of human-readable lines.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the 0x-prefixed private key (for automation).",
    )
    args = parser.parse_args()

    # eth_account uses os.urandom under the hood — that's the right entropy
    # source. We don't need to plug in our own RNG.
    account = Account.create()
    private_hex = "0x" + account.key.hex()
    address = account.address  # already EIP-55 checksummed

    if args.quiet:
        print(private_hex)
        return 0

    if args.json:
        print(json.dumps({"private_key": private_hex, "address": address}))
        return 0

    sys.stdout.write(
        "Aegis monitor signing keypair\n"
        "=============================\n"
        f"address     : {address}\n"
        f"private_key : {private_hex}\n"
        "\n"
        "Next steps:\n"
        "  1. Store the private key in AWS Secrets Manager as AGENT_SIGNING_KEY.\n"
        "     aws secretsmanager put-secret-value \\\n"
        "       --secret-id aegis-monitor/agent-signing-key \\\n"
        "       --secret-string '<private_key>'\n"
        "  2. Run scripts.upload_agent_identity to anchor the public address\n"
        "     on Arweave. Commit the returned tx id to infra/arweave-identity.json.\n"
        "  3. The address above is the value verifiers will recover from each\n"
        "     attestation signature. Publishing it is intentional.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
