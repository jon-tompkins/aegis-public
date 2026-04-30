"""Historical flag query + correction endpoints.

`GET /flags` supports optional filtering by address and time window, plus
cursor pagination via `before_id`. Cursor pagination (rather than
offset) plays well with a high-write append-only table — pages stay
consistent even as new rows arrive.

Response shape:

```
{
  "flags": [FlagResponse, ...],
  "next_before_id": int | null
}
```

`next_before_id` is non-null when the result is exactly `limit` rows —
the client uses it as the `before_id` of the next request.

Append-only correction model:

- `POST /flags/{id}/correct` emits a fresh signed flag whose
  `supersedes` field points back at the row being corrected. The prior
  row is never edited or deleted — both records survive on Arweave and
  the chain of corrections is the audit trail.
- `GET /flags` hides any row that has been superseded by a newer one,
  unless `?include_superseded=true` is passed.

`GET /flags/{id}/proof` returns the pointers a third-party verifier
needs to recompute the canonical body and recover the signer — no Aegis
server in the trust path.
"""

from __future__ import annotations

import base64
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select

from ..attestation import insert_attestation
from ..attestation.signer import AttestationSigner
from ..db.models import Flag
from ..db.session import session_scope
from ..schemas import (
    Attestation,
    AttestationBody,
    FlagProof,
    FlagResponse,
    MonitorRequest,
    Severity,
)

router = APIRouter()

_DEFAULT_LIMIT = 100
_MAX_LIMIT = 500


class FlagsPage(BaseModel):
    flags: list[FlagResponse]
    next_before_id: int | None


class CorrectionRequest(BaseModel):
    """Operator-issued correction. The new flag inherits `tx_hash` and
    `monitored_address` from the original; everything else is fresh.
    `reason_structured` should explain why the correction is being
    issued — that text is itself part of the signed audit trail.
    """

    rule_id: str = Field(min_length=1, max_length=64)
    rule_version: str = Field(min_length=1, max_length=32)
    severity: Severity
    reason_human: str = Field(min_length=1, max_length=280)
    reason_structured: dict[str, Any] = Field(default_factory=dict)

    @field_validator("rule_id")
    @classmethod
    def _rule_id_correction_namespace(cls, v: str) -> str:
        # Operators must namespace corrections so they're distinguishable
        # from rule-engine output in audit views. Rule-engine ids look
        # like `t1.approve_to_eoa`; corrections must start with `corr.`.
        if not v.startswith("corr."):
            raise ValueError("correction rule_id must start with 'corr.'")
        return v


@router.get("/flags", response_model=FlagsPage)
async def list_flags(
    request: Request,
    address: str | None = Query(
        default=None,
        description="Filter to flags for this monitored address. 0x-prefixed hex.",
    ),
    since_ms: int | None = Query(
        default=None,
        ge=0,
        description="Filter ts_ms >= since_ms (Unix epoch milliseconds).",
    ),
    before_id: int | None = Query(
        default=None,
        ge=1,
        description="Cursor: return flags with id < before_id.",
    ),
    limit: int = Query(
        default=_DEFAULT_LIMIT,
        ge=1,
        le=_MAX_LIMIT,
        description=f"Max rows. Default {_DEFAULT_LIMIT}, max {_MAX_LIMIT}.",
    ),
    include_superseded: bool = Query(
        default=False,
        description=(
            "Include flags that have been superseded by a later correction. "
            "Default False — the UI shows only the latest non-superseded "
            "record per attestation, with full history available on demand."
        ),
    ),
) -> FlagsPage:
    normalised_addr: str | None = None
    if address is not None:
        try:
            normalised_addr = MonitorRequest(address=address).address
        except ValidationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="address must be a 0x-prefixed 40-hex-char string",
            ) from None

    stmt = select(Flag)
    if normalised_addr is not None:
        stmt = stmt.where(Flag.monitored_address == normalised_addr)
    if since_ms is not None:
        stmt = stmt.where(Flag.ts_ms >= since_ms)
    if before_id is not None:
        stmt = stmt.where(Flag.id < before_id)
    if not include_superseded:
        # Anti-join: drop any row whose id is referenced by some other row's
        # `supersedes`. Cheap because `ix_flags_supersedes` covers the inner
        # set; expected cardinality is tiny — corrections are rare.
        superseded_ids = select(Flag.supersedes).where(Flag.supersedes.is_not(None))
        stmt = stmt.where(Flag.id.not_in(superseded_ids))
    stmt = stmt.order_by(Flag.id.desc()).limit(limit)

    async with session_scope() as session:
        result = await session.execute(stmt)
        rows = list(result.scalars().all())

    responses = [_to_flag_response(r) for r in rows]
    next_cursor = rows[-1].id if len(rows) == limit else None
    return FlagsPage(flags=responses, next_before_id=next_cursor)


@router.get("/flags/{flag_id}/proof", response_model=FlagProof)
async def flag_proof(flag_id: int, request: Request) -> FlagProof:
    """Pointers + canonical body bytes for third-party signature verification.

    The verifier doesn't need to trust this server: they fetch the same
    bytes from Arweave (when `arweave_tx_id` is populated) and compare.
    """
    signer = _signer(request)

    async with session_scope() as session:
        row = await session.get(Flag, flag_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="flag not found")

    body = AttestationBody(
        tx_hash=row.tx_hash,
        monitored_address=row.monitored_address,
        rule_id=row.rule_id,
        rule_version=row.rule_version,
        severity=row.severity,  # type: ignore[arg-type]
        reason_human=row.reason_human,
        reason_structured=row.reason_structured,
        agent_id=row.agent_id,
        ts_ms=row.ts_ms,
        supersedes=row.supersedes,
    )
    canonical = body.canonical_json()
    gateway = (
        f"https://arweave.net/{row.arweave_tx_id}" if row.arweave_tx_id else None
    )
    return FlagProof(
        flag_id=row.id,
        arweave_tx_id=row.arweave_tx_id,
        gateway_url=gateway,
        canonical_body_bytes_b64=base64.b64encode(canonical).decode("ascii"),
        sig=row.sig,
        signer_address=signer.address,
    )


@router.post(
    "/flags/{flag_id}/correct",
    response_model=FlagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def correct_flag(
    flag_id: int, body: CorrectionRequest, request: Request
) -> FlagResponse:
    """Issue an append-only correction.

    The new attestation:
    - Inherits `tx_hash` + `monitored_address` from the original.
    - Carries `supersedes = <original.id>`.
    - Is signed fresh under the agent key — verifiers can independently
      authenticate the correction without trusting this endpoint.

    The prior row stays in the database and on Arweave; `?include_superseded=
    true` exposes the pre-correction record for audit.
    """
    signer = _signer(request)
    broadcaster = _broadcaster(request)

    async with session_scope() as session:
        original = await session.get(Flag, flag_id)
        if original is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="flag not found"
            )
        # We allow correcting a correction (chains are explicit), but not
        # double-superseding — fail loudly so the operator can fetch the
        # current head and correct that instead.
        head_check = await session.execute(
            select(Flag.id).where(Flag.supersedes == original.id).limit(1)
        )
        if head_check.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="flag has already been superseded by a later correction",
            )

        attestation_body = AttestationBody(
            tx_hash=original.tx_hash,
            monitored_address=original.monitored_address,
            rule_id=body.rule_id,
            rule_version=body.rule_version,
            severity=body.severity,
            reason_human=body.reason_human,
            reason_structured=body.reason_structured,
            agent_id=signer.agent_id,
            ts_ms=_now_ms(),
            supersedes=original.id,
        )
        attestation = signer.sign(attestation_body)
        new_id = await insert_attestation(session, attestation)

    # Reuse the live broadcast path so subscribers see the correction in
    # real time — UIs can swap the row in place.
    await broadcaster.broadcast(new_id, attestation)

    return FlagResponse(
        id=new_id,
        attestation=attestation,
        created_at=_now_dt(),
        arweave_tx_id=None,
        arweave_confirmed_at=None,
    )


def _to_flag_response(row: Flag) -> FlagResponse:
    att = Attestation(
        tx_hash=row.tx_hash,
        monitored_address=row.monitored_address,
        rule_id=row.rule_id,
        rule_version=row.rule_version,
        severity=row.severity,  # type: ignore[arg-type]
        reason_human=row.reason_human,
        reason_structured=row.reason_structured,
        agent_id=row.agent_id,
        ts_ms=row.ts_ms,
        sig=row.sig,
        supersedes=row.supersedes,
    )
    return FlagResponse(
        id=row.id,
        attestation=att,
        created_at=row.created_at,
        arweave_tx_id=row.arweave_tx_id,
        arweave_confirmed_at=row.arweave_confirmed_at,
    )


def _signer(request: Request) -> AttestationSigner:
    signer = getattr(request.app.state, "signer", None)
    if signer is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="signer not initialised",
        )
    return signer


def _broadcaster(request: Request) -> Any:
    broadcaster = getattr(request.app.state, "broadcaster", None)
    if broadcaster is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="broadcaster not initialised",
        )
    return broadcaster


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


def _now_dt() -> Any:
    from datetime import UTC, datetime

    return datetime.now(UTC)
