"""Persistence for signed attestations.

Append-only: we never update a flag row — the signature locks its
contents, and any correction should be a new row with a follow-up
rule_id rather than a retroactive edit.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Flag
from ..schemas import Attestation


async def insert_attestation(session: AsyncSession, attestation: Attestation) -> int:
    """Insert one attestation as a `flags` row; return the assigned id.

    The caller owns the transaction — `session_scope()` will commit on
    clean exit. Flushing here populates `flag.id` before commit so the
    caller (e.g. the WS broadcaster) can reference it.
    """
    flag = Flag(
        tx_hash=attestation.tx_hash,
        monitored_address=attestation.monitored_address,
        rule_id=attestation.rule_id,
        rule_version=attestation.rule_version,
        severity=attestation.severity,
        reason_human=attestation.reason_human,
        reason_structured=attestation.reason_structured,
        agent_id=attestation.agent_id,
        ts_ms=attestation.ts_ms,
        sig=attestation.sig,
        supersedes=attestation.supersedes,
        # arweave_tx_id stays NULL — the writer task fills it in async.
    )
    session.add(flag)
    await session.flush()
    return flag.id
