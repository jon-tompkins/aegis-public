# Aegis Monitor Agent

Python service that subscribes to Ethereum mainnet pending-tx streams, runs Tier 1 screening rules against txs from watched addresses, and emits signed attestations when a rule fires.

**Status:** Phase 1a scaffold. See [#20](https://github.com/jon-tompkins/aegis-public/issues/20) and [#21](https://github.com/jon-tompkins/aegis-public/issues/21).

## Layout (planned)

```
agent/
├── main.py              # FastAPI entrypoint
├── mempool/             # Alchemy WS subscription
├── rules/               # Tier 1 detectors
├── attest/              # EIP-191 signing + persistence
├── db/                  # Postgres schema + asyncpg helpers
└── tests/               # unit + integration
```

## Quickstart (to be filled in during #21)

```sh
cd agent
uv sync                   # or: pip install -e .
cp .env.example .env
uv run uvicorn main:app --reload
```

Required env:
- `ALCHEMY_WS_URL`
- `AGENT_SIGNING_KEY`    (hex, no 0x)
- `DATABASE_URL`
- `AGENT_ID`             (e.g. `aegis-monitor-01`)

## Rules

See [`docs/specs/hack-taxonomy.md`](../docs/specs/hack-taxonomy.md) for the pattern catalogue. v1 rule set is defined in [#21](https://github.com/jon-tompkins/aegis-public/issues/21).

## Attestations

Every flag produces a JSON object signed EIP-191 with the agent key. Schema is in [#21](https://github.com/jon-tompkins/aegis-public/issues/21). Signatures verify against the agent's published public key.

## Out of scope for Phase 1a

Blocking txs (mainnet observation only), slashing, soul-hash commitment, Tier 2 / Tier 3 models, multi-agent consensus. See [#20](https://github.com/jon-tompkins/aegis-public/issues/20) for the full not-doing-list.
