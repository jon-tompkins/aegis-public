"""`GET /agent-identity` — public agent metadata for verifiers.

Returns:

```
{
  "agent_id": "aegis-monitor-prod",
  "signer_address": "0x...",
  "arweave_identity_tx_id": "<arweave tx id>" | null
}
```

Why this exists: a verifier holding a signed flag needs to know which
public key to recover against. The `signer_address` value is the canonical
answer for the *current* signer. The `arweave_identity_tx_id` lets the
same verifier cross-reference the signer-address claim against the
identity statement we anchored on Arweave at install — closing the loop
on "what if the operator swapped the published pubkey post-hoc?". See
`docs/specs/arweave-flag-storage.md` §"Agent-identity anchoring".

Source of truth for the Arweave tx id: a JSON file committed to the
repo at `infra/arweave-identity.json`. The path is overridable via
`AEGIS_ARWEAVE_IDENTITY_FILE` for ops who want to keep it elsewhere.
The file is read once at boot; if absent or malformed, the endpoint
returns `null` and the deploy is still functional (Phase 1a doesn't
gate on Arweave anchoring being complete — that's an operator step).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..attestation.signer import AttestationSigner

router = APIRouter()
log = logging.getLogger(__name__)

_DEFAULT_IDENTITY_FILE = "infra/arweave-identity.json"


class AgentIdentity(BaseModel):
    agent_id: str
    signer_address: str
    arweave_identity_tx_id: str | None = None


def load_identity_tx_id(path: str | None = None) -> str | None:
    """Read the anchored Arweave tx id from disk, returning None on miss.

    Tolerant by design: a fresh deploy may not have run the
    `upload-agent-identity` script yet. We log once at boot and serve
    `null` rather than failing the endpoint.
    """
    p = Path(path or os.environ.get("AEGIS_ARWEAVE_IDENTITY_FILE", _DEFAULT_IDENTITY_FILE))
    if not p.is_file():
        log.info("arweave identity file not present at %s — serving null", p)
        return None
    try:
        data: dict[str, Any] = json.loads(p.read_text())
    except (OSError, ValueError):
        log.warning("arweave identity file at %s is unreadable — serving null", p)
        return None
    tx_id = data.get("arweave_tx_id")
    if not isinstance(tx_id, str) or not tx_id:
        log.warning("arweave identity file at %s missing arweave_tx_id — serving null", p)
        return None
    return tx_id


@router.get("/agent-identity", response_model=AgentIdentity)
async def agent_identity(request: Request) -> AgentIdentity:
    signer: AttestationSigner | None = getattr(request.app.state, "signer", None)
    if signer is None:
        raise RuntimeError("signer not initialised on app.state")
    tx_id: str | None = getattr(request.app.state, "arweave_identity_tx_id", None)
    return AgentIdentity(
        agent_id=signer.agent_id,
        signer_address=signer.address,
        arweave_identity_tx_id=tx_id,
    )
