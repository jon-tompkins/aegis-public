# Aegis Monitor Agent

Python service that subscribes to Ethereum mainnet pending-tx streams, runs Tier 1 screening rules against txs from watched addresses, and emits signed attestations when a rule fires.

**Status:** Phase 1a scaffold. See [#21](https://github.com/jon-tompkins/aegis-public/issues/21) and [`docs/specs/phase-1a-tasks.md`](../docs/specs/phase-1a-tasks.md).

## Layout

```
aegis-monitor/
├── Dockerfile
├── pyproject.toml
├── src/
│   └── aegis_monitor/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app
│       ├── api/                    # HTTP + WS routes
│       ├── screening/              # Rule engine + Tier 1 detectors
│       ├── attestation/            # EIP-191 signing + canonical serialization
│       └── db/                     # Postgres schema + async DB helpers
└── tests/
```

## Quickstart

```sh
cd aegis-monitor
uv sync                   # or: pip install -e '.[dev]'
cp .env.example .env
uv run uvicorn aegis_monitor.main:app --reload
```

Required env:

- `ALCHEMY_WS_URL`
- `AGENT_SIGNING_KEY`    (hex, no `0x`)
- `DATABASE_URL`         (Postgres, async driver: `postgresql+asyncpg://…`)
- `AGENT_ID`             (e.g. `aegis-monitor-01`)

## Docker

```sh
docker build -t aegis-monitor .
docker run --rm -p 8000:8000 --env-file .env aegis-monitor
```

## Rules

See [`docs/specs/hack-taxonomy.md`](../docs/specs/hack-taxonomy.md) for the attack pattern catalogue and [`docs/specs/screening-rules.md`](../docs/specs/screening-rules.md) for canonical AEG-xxx rule entries. v1 Tier 1 set is defined in [#21](https://github.com/jon-tompkins/aegis-public/issues/21).

## Attestations

Every flag produces a JSON object signed EIP-191 with the agent key. Schema lives in [#21](https://github.com/jon-tompkins/aegis-public/issues/21). Signatures verify against the agent's published public key.

## Out of scope for Phase 1a

Blocking txs (mainnet observation only), slashing, soul-hash commitment, Tier 2 / Tier 3 models, multi-agent consensus. See [#20](https://github.com/jon-tompkins/aegis-public/issues/20) for the full not-doing list.
