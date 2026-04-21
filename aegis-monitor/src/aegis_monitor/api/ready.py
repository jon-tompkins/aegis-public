"""Readiness probe.

`/health` answers "am I up?" — stays true on transient upstream pain so
HEALTHCHECK doesn't churn. `/ready` answers "am I useful?" — gates on
the two hard dependencies: Postgres and the Alchemy WS listener. Load
balancers should route on `/ready`; supervisors should restart on
`/health`.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ..db.session import get_engine

router = APIRouter()


async def _db_ok() -> tuple[bool, str | None]:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, None
    except Exception as e:  # pragma: no cover — env-dependent
        return False, f"db: {type(e).__name__}: {e}"


def _listener_ok(app: Any) -> tuple[bool, str | None]:
    """Shallow check: is the background listener task still running?"""
    task = getattr(app.state, "listener", None)
    if task is None:
        return False, "listener: not started"
    # `AlchemyPendingTxListener` exposes `_task`; we treat "task exists and not
    # done" as ready. Richer health metrics arrive in the observability spec.
    inner = getattr(task, "_task", None)
    if inner is None:
        return False, "listener: task not created"
    if inner.done():
        return False, "listener: task exited"
    return True, None


def _consumer_ok(app: Any) -> tuple[bool, str | None]:
    task: asyncio.Task | None = getattr(app.state, "consumer_task", None)
    if task is None:
        return False, "consumer: not started"
    if task.done():
        return False, "consumer: task exited"
    return True, None


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    checks: dict[str, dict[str, Any]] = {}

    db_ok, db_err = await _db_ok()
    checks["db"] = {"ok": db_ok, **({"error": db_err} if db_err else {})}

    lst_ok, lst_err = _listener_ok(request.app)
    checks["listener"] = {"ok": lst_ok, **({"error": lst_err} if lst_err else {})}

    csm_ok, csm_err = _consumer_ok(request.app)
    checks["consumer"] = {"ok": csm_ok, **({"error": csm_err} if csm_err else {})}

    overall = all(c["ok"] for c in checks.values())
    code = status.HTTP_200_OK if overall else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content={"ready": overall, "checks": checks})
