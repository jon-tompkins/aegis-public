"""Process-wide settings, loaded from environment.

Lazily validated — `Settings.from_env()` is called once at app startup in
the FastAPI lifespan context. Missing required vars raise
`RuntimeError` before the app binds to a port so supervisors see a fast
fail, not a partially-running service.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    alchemy_ws_url: str
    agent_signing_key: str
    database_url: str
    agent_id: str

    @classmethod
    def from_env(cls) -> Settings:
        def req(key: str) -> str:
            value = os.environ.get(key)
            if not value:
                raise RuntimeError(f"required env var {key} is not set")
            return value

        return cls(
            alchemy_ws_url=req("ALCHEMY_WS_URL"),
            agent_signing_key=req("AGENT_SIGNING_KEY"),
            database_url=req("DATABASE_URL"),
            agent_id=os.environ.get("AGENT_ID", "aegis-monitor-01"),
        )
