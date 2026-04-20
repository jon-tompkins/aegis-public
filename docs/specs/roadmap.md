# Aegis — Phased Roadmap

**Status:** First cut, 2026-04-17
**Not precious** — every phase boundary is movable. The point is to separate "we know what this is" from "we've built it" from "someone's using it."

---

## North star

Two sellable assets coming out the other side:

1. **The chain** — an L2 where exploits get rejected at block validation time. Cash-flowing like Base / Arbitrum.
2. **The screening tech stack** — indexer, rule engine, soul-hash impl, validator coordination. Sellable / licensable independent of the chain.

Exit options remain open either way: Base / OP Labs / Arbitrum acquire the chain, or a custodian / wallet-infra player licenses the tech.

---

## Phase 0 — Scoping & design ✅ *(near-complete)*

**Goal:** Every major design call has a written answer.
**Exit criterion:** Zero open *"what should this be?"* questions in the five core specs (intent-mapping, soul-hash, training-pipeline, economics, agent-comms).

### What's in

- Architecture: [`aegis-chain-design.md`](../aegis-chain-design.md)
- Training plan: [`aegis-training-plan.md`](../aegis-training-plan.md)
- Data & storage: [`intent-mapping.md`](./intent-mapping.md), [`soul-hash.md`](./soul-hash.md), [`off-chain-store.md`](./off-chain-store.md)
- Screening: [`training-pipeline.md`](./training-pipeline.md), [`byo-model.md`](./byo-model.md), [`hack-taxonomy.md`](./hack-taxonomy.md)
- Coordination: [`agent-comms.md`](./agent-comms.md), [`memory-strategy.md`](./memory-strategy.md)
- Economics: [`economics.md`](./economics.md), [`staking-systems.md`](./staking-systems.md), [`economics-model.csv`](./economics-model.csv)
- Guardian (deferred): [`guardian.md`](./guardian.md)
- Code scaffolds: [`indexer/`](../../indexer/), [`scripts/tier1_detector.py`](../../scripts/tier1_detector.py), [`scripts/exploits/exploits.json`](../../scripts/exploits/exploits.json)

### Gaps still to close (must resolve before Phase 1)

- **Endianness** — SSZ canon is little-endian, `intent-mapping.md` says `UInt256` big-endian. Pick one.
- **Epoch cadence** — 12h vs 1d (tied to soul-hash grace window + profile_epoch cost)
- **Testnet privacy posture** — Mode A (fully public) or Mode B (public-hash / private-detail). `soul-hash.md` picks B for v1; confirm consistency with intent-mapping.
- **SSZ library pin** — `ssz_rs` vs `ethereum_ssz`. Decides the shape of test vectors.
- **Hash backend pin** — `tiny-keccak` vs `alloy-primitives` keccak.

Track these as open issues on `clark`/`Bob` until decided.

---

## Phase 1 — Buildable MVP 🏗️

**Goal:** 3-validator local testbed screening Ethereum mainnet backfill data.
**Exit criterion:** Exploit-replay backtest runs against ≥50 exploits and produces a recall + FP report. One tx end-to-end: ingest → features → profile → screener → Tier 1 verdict → teacup filed.

### Work items

| Item | Status | Where |
|---|---|---|
| `cargo check` passes on `indexer/` workspace | ⏳ Pending network-capable run | `indexer/` |
| Wire `AlchemySource` to real `alloy::providers::Provider` | ⏳ Stub | `indexer/crates/ingest/src/lib.rs` |
| Implement `ClickhouseStore: ProfileStore` | ⏳ Not started | `indexer/crates/profile/` |
| Apply DDL to a real ClickHouse | ⏳ Script only | `indexer/sql/001_initial_schema.sql` |
| Stand up Postgres for off-chain memory | ⏳ DDL not committed yet (see gap below) | ref spec [`off-chain-store.md`](./off-chain-store.md) |
| Port T1 rules from Python → Rust `Tier1Rule` impls | ⏳ Python ref exists | `scripts/tier1_detector.py` → `indexer/crates/screener/` |
| Tier 2 reference model (IsolationForest) trained + serialized | ⏳ Not started | new: `indexer/crates/tier2/` |
| Feature decoding (ERC-20/721/1155 logs, signed-tx → from/to/value) | ⏳ TODO-marked | `indexer/crates/features/src/lib.rs` |
| 3-validator local testbed via Manifold | ⏳ Bob's track — needs live Manifold hub | ref spec [`agent-comms.md`](./agent-comms.md) |
| Signed-message schema for Aegis validator traffic | ⏳ Schema sketch in spec, no impl | ref spec [`agent-comms.md`](./agent-comms.md) |
| Grow exploit DB from 10 → 50+ entries | ⏳ Contributor bounty territory | `scripts/exploits/exploits.json` |
| Backtest runner (`scripts/backtest.py`) | ⏳ Outlined in README, not impl | `scripts/exploits/README.md` |

### Missing specs / outlines to add

- **`docs/specs/local-dev-setup.md`** — how a contributor brings up the full stack: ClickHouse + Postgres + Manifold + indexer + 3 validators + test RPC. Outline:
  ```
  ## prerequisites
  ## bring-up order
  ## env vars / config
  ## smoke test: screen one tx end-to-end
  ## tear-down
  ```
- **`docs/specs/op-stack-fork-plan.md`** — which OP Stack version we fork (Bedrock vs Holocene vs whichever is current), patch strategy for `aegis_ext` header, upstream-tracking commitment. Outline:
  ```
  ## version pin + justification
  ## patches needed
  ## upstream sync cadence
  ## "paved road" components (we don't touch) vs "fork" components (we own)
  ```
- **`indexer/sql/002_offchain_memory.sql`** — Postgres DDL from `off-chain-store.md`.
- **`indexer/sql/003_migrations_README.md`** — how migrations are numbered + applied across both ClickHouse and Postgres.

---

## Phase 2 — Devnet / public testnet 🧪

**Goal:** A public testnet with real Ethereum bridge-in, 5–10 validators (team-operated OK), and the wallet SDK path lit up. Blog-post-able results from replaying historical exploits against the live chain.
**Exit criterion:** First external dev successfully bridges test-ETH in, submits a tx that Aegis catches as suspicious, and the block commits the flag.

### Work items

| Item | Where |
|---|---|
| Mainnet-Ethereum → Aegis-testnet bridge | new — likely based on OP Stack canonical bridge |
| Faucet | new |
| Block explorer (off-the-shelf, e.g. Blockscout) | infra |
| Metrics + dashboards (Prometheus + Grafana) | new |
| Validator operator guide | new spec |
| Incentivized exploit-replay announcement | comms |
| Wallet SDK skeleton (Guardian-style pre-submission signer, off-chain advisory mode) | new code: `sdk/wallet-guard/` |
| Council bootstrapping (5-of-7 multisig, placeholder members) | new |

### Missing specs

- **`docs/specs/testnet-launch-plan.md`** — timeline, validator committee, faucet, bridge spec, success metrics. Outline:
  ```
  ## validator committee v0 (team-operated or pre-invited partners)
  ## bridge architecture
  ## faucet + test-ETH policy
  ## metrics + what we publish
  ## incident response during testnet
  ```
- **`docs/specs/validator-operator-guide.md`** — how to spin up, register, monitor, upgrade a validator. Outline:
  ```
  ## hardware / cloud requirements
  ## install + register (Manifold cap announce + on-chain registration)
  ## model-hash commitment
  ## monitoring a validator is doing its job
  ## upgrade + rollback
  ```
- **`docs/specs/observability.md`** — metrics schema, alert thresholds, public dashboards. Outline:
  ```
  ## per-validator metrics (latency, flag distribution, compliance-test pass rate)
  ## chain-level metrics (blocks, profile_root churn, epoch transitions)
  ## what's public vs ops-only
  ## alerts that page a human
  ```
- **`sdk/wallet-guard/README.md`** — wallet SDK surface. Outline:
  ```
  ## install
  ## screen(tx) -> {safe, flagged, block, reasons[]}
  ## transport: HTTPS for advisory mode, EIP-4337 module for hard-enforce
  ## auth / rate-limit model
  ```

---

## Phase 3 — Mainnet + real TVL 🚀

**Goal:** Mainnet chain with its own AEGIS token (stake + governance only, **not** gas), native DeFi primitives, real users, real slashing events, a council that's actually voted in.
**Exit criterion:** ≥$10M TVL sustained 90 days, ≥1 caught exploit attempt on mainnet publicly documented, ≥10 validators with ≥3 operated by non-team entities.

### Work items

- Mainnet genesis (validator set, genesis distribution, token launch)
- Native DeFi primitives live: AMM (Solidly-style), pool lending (Aave-style), native bridging
- AEGIS token launch — allocation + vesting schedule
- Slashing live on mainnet (starts with low thresholds, tightens over time)
- UMA-style council constituted per `economics.md`
- Insurance-tier pricing for high-TVL protocols
- Incident response playbook exercised in a tabletop drill pre-launch
- Formal audit of: OP Stack fork, soul-hash commitment, screening contract path, bridge

### Missing specs

- **`docs/specs/mainnet-launch-plan.md`** — genesis, token launch, bridge, validator onboarding at scale. Outline similar to testnet-launch but with production hardening.
- **`docs/specs/incident-response.md`** — when an exploit is caught, what happens (public post-mortem cadence, bounty payment to flagger, slashing enforcement, comms).
- **`docs/specs/governance.md`** — council composition, term limits, voting mechanics, what's on-chain vs off-chain governance. **Explicit exclusions** for Aegis Labs IP (see Phase 5).
- **`docs/specs/aegis-token.md`** — allocation (validators, community, treasury, team), vesting, emission schedule, bounded-inflation cap.
- **`docs/specs/audit-plan.md`** — scope, auditor shortlist, what counts as a blocker.

---

## Phase 4 — Ecosystem + proof 📈

**Goal:** The model's exploit-prevention rate is measurable, public, and defensible. Wallets and protocols *choose* Aegis rather than needing persuasion.
**Exit criterion:** ≥$100M TVL, ≥2 major wallets shipping the wallet SDK, ≥1 top-100-TVL protocol opting into Aegis attestation as a hard-block on high-value ops (bridge withdrawal, governance execution).

### Work items

- Third-party validators running non-reference models
- Wallet SDK deployed by Rabby / Rainbow / MetaMask-SnapKit / similar — at least one
- Protocol integrations: bridge or lending market requiring Aegis attestation for a specific operation
- Exploit DB → 200+ entries with ongoing community contributions
- Quarterly exploit-prevention report published
- Conference talks / research papers
- Bounty program for new T1 rules + exploit DB entries

### Missing specs

- **`docs/specs/ecosystem-partnerships.md`** — target wallet + protocol list, integration paths, incentives. Outline:
  ```
  ## target wallets (rationale per candidate)
  ## target protocols (bridges first, then lending, then DEX)
  ## integration modes (advisory, co-signer, on-chain attestation)
  ## what we offer (free tier, paid tier, revenue share)
  ```
- **`docs/specs/public-metrics.md`** — what we publish + how, so the number is defensible. Outline:
  ```
  ## exploits-prevented count methodology
  ## false-positive rate methodology
  ## reporting cadence + format (quarterly blog post)
  ## diligence data room structure (for acquirers)
  ```
- **`docs/specs/contributor-program.md`** — bounty structure, CLA vs DCO, IP split between bounty work and core. Outline as Phase 4 starts.

---

## Phase 5 — Labs entity + exit-readiness 🏛️

**Goal:** Aegis Labs stands up as the corporate vehicle. License split formalized. Company is cleanly acquirable, the chain keeps running regardless.
**Exit criterion:** Labs has equity cap table, IP assignment agreements with contributors, a clean data room, and a license split that a real acquirer can buy without needing to negotiate with token holders.

### Work items

- **Labs entity formed** (Delaware C-corp or equivalent) — employs core team, owns proprietary IP, takes equity investment
- **License split enforced:**
  - MIT / Apache: chain code, screener reference impl, indexer, SDK, all specs
  - Labs-proprietary: model weights, Tier 2/3 trained artifacts, operational know-how, the fully-curated exploit DB beyond seed entries, customer relationships
- **Token governance scoped narrowly** — only chain-native params (slashing thresholds, epoch cadence, council seats). Never over screening logic or Labs IP.
- Data room ready: backtest reports, exploit-prevention metrics, validator registry, financials
- Optional **Phase 5.5** — productize the screening stack as a standalone AVS subscription product, sold independent of the chain

### Missing specs

- **`docs/specs/labs-charter.md`** — entity structure, IP ownership, employee + contributor agreements. Outline:
  ```
  ## entity form (Delaware C-corp)
  ## relationship to chain (Labs contributes to chain, chain pays fees to validators not to Labs)
  ## what Labs owns (proprietary repo, brand, customer contracts)
  ## what Labs doesn't own (chain code, token, protocol governance)
  ## investor story (Labs is the vehicle for equity; chain runs regardless)
  ```
- **`docs/specs/governance-scope.md`** — formal list of what the token decides, what the council decides, what's automatic, what's Labs-only.
- **`docs/specs/acquisition-readiness.md`** — internal checklist for being diligence-ready. Outline:
  ```
  ## financial readiness (revenue, cost, cap table)
  ## IP readiness (license clarity, CLAs, contributor assignments)
  ## metrics readiness (exploit prevention rate, validator compliance)
  ## org readiness (team + contractors + advisors documented)
  ```

---

## How we track

- Issues with `tenet/backlog` or `tenet/in-progress` are in-flight.
- Labels `clark` / `Bob` identify whose turn it is.
- `tenet/done` means the acceptance criteria for an issue are met.
- Phase transitions happen when that phase's exit criterion is met — not when every work item ticks. It's OK to ship to the next phase with some items deferred.

## What's deliberately not in the roadmap

- **Multi-chain screening AVS** — parked. Good v2 bet if the L2 proves the model; not a distraction now.
- **EIP-4337 Guardian as a required component** — optional add-on. Wallet SDK gives most of the value without forcing AA.
- **Shared memory via Tenet on the screening hot path** — excluded. Breaks soul-hash determinism per `memory-strategy.md`.
