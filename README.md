# Aegis Chain — Project Tracker

**Status:** Early scoping / Phase 0  
**Started:** 2026-04-15

## What
Ethereum L2 with AI agent validators that screen every tx for anomalous behavior and can pause/reject exploits at the chain level.

## Docs

### Top-level
- `aegis-chain-design.md` — Architecture, tx flow, intervention mechanism, governance, validator integrity
- `aegis-training-plan.md` — Behavioral modeling, data sources, 3-tier screening, 16-week sprint plan

### Specs (`docs/specs/`)
Contributor-ready designs, one per backlog issue:
- [`intent-mapping.md`](docs/specs/intent-mapping.md) — profile store: DB, schema, privacy ([#7](https://github.com/jon-tompkins/aegis-public/issues/7))
- [`training-pipeline.md`](docs/specs/training-pipeline.md) — ingestion, features, Tier 1/2 ([#8](https://github.com/jon-tompkins/aegis-public/issues/8))
- [`soul-hash.md`](docs/specs/soul-hash.md) — profile commitment, header extension ([#10](https://github.com/jon-tompkins/aegis-public/issues/10))
- [`economics.md`](docs/specs/economics.md) — token, slashing, incentives ([#12](https://github.com/jon-tompkins/aegis-public/issues/12))
- [`guardian.md`](docs/specs/guardian.md) — opt-in per-user screening agent ([#11](https://github.com/jon-tompkins/aegis-public/issues/11))
- [`agent-comms.md`](docs/specs/agent-comms.md) — validator communication network ([#9](https://github.com/jon-tompkins/aegis-public/issues/9))

**Build sequence (data-first):** #7 → #8 → #10 → #12. #9 is research-blocked; #11 is optional/deferred.

## Code

- [`indexer/`](indexer/) — Rust workspace: RPC ingest, feature extraction, profile store, Tier 1/2 screener, CLI. Skeleton in place; trait bodies are stubs. See [`indexer/README.md`](indexer/README.md).

## Key Decisions Made
- OP Stack fork (MIT, modular, designed to be extended)
- 3-tier screening: heuristics → statistical → LLM escalation
- Single-agent screening for speed, multi-agent vote on escalation
- L1/L2 history ingestion for cold start
- Bring-your-own model for validators
- Canonical behavioral profiles hashed on-chain ("soul hash")
- Slashing for clear negligence, not judgment calls

## Open Threads
- Validator integrity: profile privacy vs verifiability, slashing thresholds, "CAPTCHA tests" for validators
- Token/economics: how validators get paid for inference
- Profile attestation without giving attackers a map of blind spots
- Cross-chain monitoring scope

## Next
- Tailscale as coordination layer for building (context switch in progress)
