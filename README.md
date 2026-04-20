# Aegis Chain — Project Tracker

**Status:** Phase 0 → Phase 1 transition
**Started:** 2026-04-15
**Roadmap:** [`docs/specs/roadmap.md`](docs/specs/roadmap.md)

## What
Ethereum L2 with AI agent validators that screen every tx for anomalous behavior and can pause/reject exploits at the chain level.

## Roadmap at a glance

See [`docs/specs/roadmap.md`](docs/specs/roadmap.md) for the full version. Short form:

- **Phase 0 — Scoping & design** *(near-complete)* — specs, architecture decisions, code scaffolds
- **Phase 1 — Buildable MVP** *(next)* — 3-validator local testbed, exploit-replay backtest, real RPC ingest
- **Phase 2 — Devnet / public testnet** — public testnet, team-operated validators, wallet SDK skeleton
- **Phase 3 — Mainnet + real TVL** — token launch, native DeFi primitives, slashing live, council constituted
- **Phase 4 — Ecosystem + proof** — wallet SDK shipped by ≥2 major wallets, ≥1 protocol-level integration, public exploit-prevention metrics
- **Phase 5 — Labs + exit-readiness** — Aegis Labs entity, license split, acquisition-ready

## Artifacts by phase

### Phase 0 — Scoping & design

**Top-level design**
- [`aegis-chain-design.md`](aegis-chain-design.md) — architecture, tx flow, intervention, governance, validator integrity
- [`aegis-training-plan.md`](aegis-training-plan.md) — behavioral modeling, data sources, 3-tier screening, 16-week plan

**Specs — data & storage**
- [`docs/specs/intent-mapping.md`](docs/specs/intent-mapping.md) — address/contract profile store (#7)
- [`docs/specs/soul-hash.md`](docs/specs/soul-hash.md) — Merkle commitment, OP Stack header extension (#10)
- [`docs/specs/off-chain-store.md`](docs/specs/off-chain-store.md) — Postgres for teacups / trust-ledger / MRI (#13)

**Specs — pipeline & models**
- [`docs/specs/training-pipeline.md`](docs/specs/training-pipeline.md) — ingestion, features, Tier 1/2 reference (#8)
- [`docs/specs/byo-model.md`](docs/specs/byo-model.md) — screening I/O interface for validators
- [`docs/specs/hack-taxonomy.md`](docs/specs/hack-taxonomy.md) — exploit patterns driving Tier 1 rules

**Specs — coordination & agents**
- [`docs/specs/agent-comms.md`](docs/specs/agent-comms.md) — Manifold for v0, on-chain for truth (#9)
- [`docs/specs/memory-strategy.md`](docs/specs/memory-strategy.md) — Tenet / teacups / MRI applicability
- [`docs/specs/guardian.md`](docs/specs/guardian.md) — Guardian layer, deferred to v1+ (#11)

**Specs — economics**
- [`docs/specs/economics.md`](docs/specs/economics.md) — token, revenue mix, slashing (#12)
- [`docs/specs/economics-model.csv`](docs/specs/economics-model.csv) — per-validator P&L numeric model
- [`docs/specs/staking-systems.md`](docs/specs/staking-systems.md) — EigenLayer / UMA / DeFi-in-a-Box analysis

**Code scaffolds** *(wired enough to iterate on, not enough to run end-to-end yet)*
- [`indexer/`](indexer/) — Rust workspace (types / ingest / features / profile / screener / CLI) + ClickHouse DDL (#7, #8)
- [`scripts/tier1_detector.py`](scripts/tier1_detector.py) — Tier 1 rule engine, T1-001..T1-010 (#14)
- [`scripts/exploits/exploits.json`](scripts/exploits/exploits.json) — 10 seed exploits for backtest (#14)

**Coordination infra**
- [`.github/workflows/setup-labels.yml`](.github/workflows/setup-labels.yml) — one-shot label creator (`clark` / `Bob`)
- [`.github/workflows/clark-monitor.yml`](.github/workflows/clark-monitor.yml) — surfaces the `clark` queue; coordination-only, no LLM
- [`.claude/commands/clark-loop.md`](.claude/commands/clark-loop.md) — slash command for local `/loop` agent ticks
- [`.claude/HANDOFF.md`](.claude/HANDOFF.md) — session handoff doc for fresh local Claude sessions

**Pre-merge drafts (Clark's v0, kept for diff):** `docs/specs/*.v0.md` files alongside their current counterparts.

### Phase 1 — Buildable MVP *(in flight)*

Work items, what-needs-doing, and missing spec outlines live in [`docs/specs/roadmap.md`](docs/specs/roadmap.md#phase-1--buildable-mvp-️). Highlights:

- Port Tier 1 rules Python → Rust
- Wire real RPC + ClickHouse + Postgres
- 3-validator local testbed on Manifold
- Backtest runner against ≥50 exploits
- **Missing specs to write:** `local-dev-setup.md`, `op-stack-fork-plan.md`, `indexer/sql/002_offchain_memory.sql`

### Phase 2 — Devnet / public testnet *(not started)*

- Public testnet + Ethereum bridge + faucet
- Validator operator guide
- Wallet SDK skeleton (off-chain advisory + EIP-4337 co-signer modes)
- **Missing specs to write:** `testnet-launch-plan.md`, `validator-operator-guide.md`, `observability.md`, `sdk/wallet-guard/README.md`

### Phase 3 — Mainnet + real TVL *(not started)*

- AEGIS token launch (stake + governance only — gas stays ETH/stable)
- Native DeFi primitives (AMM, lending, bridging)
- Slashing live, council constituted
- Formal audits
- **Missing specs to write:** `mainnet-launch-plan.md`, `incident-response.md`, `governance.md`, `aegis-token.md`, `audit-plan.md`

### Phase 4 — Ecosystem + proof *(not started)*

- Wallet SDK shipped by major wallets (Rabby / Rainbow / Metamask-Snap)
- Protocol-level integrations (Aegis attestation required for specific ops)
- Public exploit-prevention metrics + quarterly reports
- **Missing specs to write:** `ecosystem-partnerships.md`, `public-metrics.md`, `contributor-program.md`

### Phase 5 — Labs + exit-readiness *(not started)*

- Aegis Labs entity (Delaware C-corp) employing the core team
- License split: MIT chain code + screener reference; proprietary model weights + curated exploit DB
- Token governance scoped narrowly (chain params only, never screening IP)
- **Missing specs to write:** `labs-charter.md`, `governance-scope.md`, `acquisition-readiness.md`

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
