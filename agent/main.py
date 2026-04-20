"""Aegis monitor agent — FastAPI entrypoint.

Scaffold only. Real implementation tracked in
https://github.com/jon-tompkins/aegis-public/issues/21
"""

from fastapi import FastAPI

app = FastAPI(title="Aegis Monitor Agent", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "agent_id": "aegis-monitor-01"}
