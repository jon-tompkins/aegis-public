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

**Data & storage**
- [`intent-mapping.md`](docs/specs/intent-mapping.md) — address/contract profile store, ClickHouse + LMDB (#7)
- [`soul-hash.md`](docs/specs/soul-hash.md) — Merkle commitment to the profile dataset, OP Stack header ext (#10)

**Pipeline & models**
- [`training-pipeline.md`](docs/specs/training-pipeline.md) — ingestion, features, Tier 1/2 reference (#8)
- [`byo-model.md`](docs/specs/byo-model.md) — screening I/O interface validators must implement
- [`hack-taxonomy.md`](docs/specs/hack-taxonomy.md) — exploit patterns driving Tier 1 rule design

**Coordination & agents**
- [`agent-comms.md`](docs/specs/agent-comms.md) — Manifold for v0, on-chain for truth (#9)
- [`memory-strategy.md`](docs/specs/memory-strategy.md) — Tenet / teacups / MRI applicability
- [`guardian.md`](docs/specs/guardian.md) — Guardian layer, deferred to v1+ (#11)

**Economics**
- [`economics.md`](docs/specs/economics.md) — token, revenue mix, slashing (#12)
- [`economics-model.csv`](docs/specs/economics-model.csv) — per-validator P&L numeric model
- [`staking-systems.md`](docs/specs/staking-systems.md) — EigenLayer / UMA / chain-native DeFi analysis

**Pre-merge drafts (Clark's v0, kept for diff):** `*.v0.md` files next to their current counterparts.

## Code
- [`indexer/`](indexer/) — Rust workspace (types, ingest, features, profile, screener, CLI) + ClickHouse DDL (#8). Skeleton; RPC and ClickHouse impls are stubs.
- [`scripts/tier1_detector.py`](scripts/tier1_detector.py) — first Tier 1 rule-engine prototype (#14)

## GitHub workflows
- [`.github/workflows/setup-labels.yml`](.github/workflows/setup-labels.yml) — one-shot label creator (`clark` / `Bob`)
- [`.github/workflows/clark-monitor.yml`](.github/workflows/clark-monitor.yml) — surfaces the `clark` queue; coordination-only, no LLM

## Key Decisions Made
- OP Stack fork (MIT, modular, designed to be extended)
- 3-tier screening: heuristics → statistical → LLM escalation
- Single-agent screening for speed, multi-agent vote on escalation
- L1/L2 history ingestion for cold start
- Bring-your-own model for validators
- Canonical behavioral profiles hashed on-chain ("soul hash")
- Slashing for clear negligence, not judgment calls
- Gas token = ETH or stable, not AEGIS (see `gas-token-decision` commit on main)
- Manifold for agent coordination in v0; Tenet deferred (breaks soul-hash determinism)

## Open Threads
- Validator integrity: profile privacy vs verifiability, slashing thresholds, "CAPTCHA tests" for validators
- Token/economics: how validators get paid for inference
- Profile attestation without giving attackers a map of blind spots
- Cross-chain monitoring scope

## Next
- Tailscale as coordination layer for building (context switch in progress)
