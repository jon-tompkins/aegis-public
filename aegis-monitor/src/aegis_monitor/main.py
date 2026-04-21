"""Aegis monitor agent — FastAPI entrypoint.

Wires together the Alchemy mempool listener, rule engine, and attestation
layer. Scaffold only for now — real handlers land as tasks from
docs/specs/phase-1a-tasks.md complete.
"""

from fastapi import FastAPI

app = FastAPI(title="Aegis Monitor Agent", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — returns OK if the process is up.

    The `/ready` probe (pending) will additionally check Alchemy WS and
    Postgres connectivity.
    """
    return {"status": "ok", "agent_id": "aegis-monitor-01"}
