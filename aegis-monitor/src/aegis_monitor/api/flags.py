"""Historical flag query endpoint.

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
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, ValidationError
from sqlalchemy import select

from ..db.models import Flag
from ..db.session import session_scope
from ..schemas import Attestation, FlagResponse, MonitorRequest

router = APIRouter()

_DEFAULT_LIMIT = 100
_MAX_LIMIT = 500


class FlagsPage(BaseModel):
    flags: list[FlagResponse]
    next_before_id: int | None


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
) -> FlagsPage:
    # Normalise address through the MonitorRequest validator so case + format
    # rules stay in one place.
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
    stmt = stmt.order_by(Flag.id.desc()).limit(limit)

    async with session_scope() as session:
        result = await session.execute(stmt)
        rows = list(result.scalars().all())

    responses = [_to_flag_response(r) for r in rows]
    next_cursor = rows[-1].id if len(rows) == limit else None
    return FlagsPage(flags=responses, next_before_id=next_cursor)


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
    )
    return FlagResponse(id=row.id, attestation=att, created_at=row.created_at)
