# Agent Training Pipeline

**Status:** Draft (tracks [#8](https://github.com/jon-tompkins/aegis-public/issues/8))
**Phase:** 0 — design
**Related:** [`aegis-training-plan.md`](../../aegis-training-plan.md), [intent-mapping.md](./intent-mapping.md), [soul-hash.md](./soul-hash.md)

---

## Purpose

Turn raw L1/L2 history into behavioral profiles and keep them fresh post-launch. This is Sprints 1–3 of `aegis-training-plan.md`, made concrete enough for a contributor to pick up.

## Goals

- Ingest 12 months of Ethereum L1 + major L2 history for the top 1M active addresses.
- Emit profiles in the schema defined by [intent-mapping.md](./intent-mapping.md).
- Support incremental updates (per-tx streaming, no full recompute).
- Produce Tier 1 (heuristic) and Tier 2 (statistical) screening artifacts with measurable precision/recall on historical exploits.

## Non-goals

- Tier 3 LLM escalation infra beyond a thin prompt scaffold — separate issue.
- Slashing / consensus integration.

## 1. Data ingestion

**Sources**
- Archive RPC — Alchemy or Infura primary; self-hosted Erigon as cost fallback.
- Chains (v0): Ethereum L1, Arbitrum, Base, Optimism.

**Indexer language** — recommend **Rust** using `alloy` + `reth-primitives`. Go is acceptable if the contributor is stronger there.

**Targeting (v0)**
- Top 1M addresses by tx count over rolling 12 months.
- All Etherscan-verified contracts with ≥1000 interactions.
- All bridge contracts (explicit allowlist).

**Output** — rows in `tx_feature_log` ([intent-mapping.md §Schema](./intent-mapping.md#2-schema-v0)).

## 2. Feature engineering

**Per-tx** (from receipts + traces)
- `from`, `to`, `value_wei`, `gas_used`, `gas_price_wei`, `nonce`
- function selector (first 4 bytes of calldata)
- decoded arg summary, length-bounded
- token transfer events (ERC-20 / ERC-721 / ERC-1155)
- block timestamp → UTC hour, day-of-week

**Aggregated, windowed** (7d / 30d)
- rolling mean/std for value and frequency
- gas-price percentile
- counterparty set + Jaccard drift vs. prior window
- protocol interaction entropy over selectors

## 3. Model format — "BYO model" constraint

Validators may run different models. The pipeline ships:

1. **Canonical profiles** — shared, part of soul hash.
2. **Reference screening models** — Tier 1 rules + Tier 2 stat model. Validators may use or replace.
3. **Stable I/O interface** — any third-party model pluggable.

**Reference Tier 2 model (v0):** `sklearn` IsolationForest + per-address z-score on windowed features. Serialize as ONNX where possible, or versioned pickle with schema pin.

## 4. Backtesting — known exploit replay

Replay these exploits against the pipeline:

| Exploit | Expected tier |
|---|---|
| Ronin Bridge | Tier 1 (value anomaly) |
| Wormhole | Tier 2 (param anomaly) |
| Poly Network | Tier 1 (cross-chain) |
| Mango Markets | Tier 2 + 3 |
| Curve re-entrancy | Tier 1 (known pattern) |
| Harmony Bridge | Tier 1 (value + counterparty) |

**Target:** ≥90% detection, ≤1% false positive on a held-out normal-tx sample.

## 5. Real-time path

After backfill:
- Streaming consumer (Kafka or NATS) reads new blocks, updates `address_profile` / `contract_profile` incrementally.
- Nightly reconciliation job recomputes from `tx_feature_log` and diffs against the live profile — any drift logged.

## 6. Interface for third-party models

```
interface Screener {
  screen(tx: CanonicalTx, profile: AddressProfile, contract: ContractProfile | None)
    -> { flag: 🟢🟡🟠🔴, score: u16 /* bp */, tier: 1|2|3, reasons: string[] }
}
```

Language bindings: Rust trait + gRPC so non-Rust implementations are first-class.

## Acceptance criteria

- [ ] Indexer ingests ≥12 months of Ethereum L1 for the 1M-address target set into `tx_feature_log`
- [ ] Feature extraction emits canonical per-address and per-contract profiles
- [ ] Tier 1 rule engine (~50 rules seeded from known exploit patterns)
- [ ] Tier 2 reference model trained and serialized
- [ ] `screen(tx) -> {flag, score, tier}` API, <50ms p99 for Tier 1+2
- [ ] Exploit-replay backtest report with precision/recall
- [ ] Streaming consumer + reconciliation job
- [ ] Docs on plugging in a non-reference model

## Open questions

- Can we batch `eth_getLogs` + traces cheaply enough on hosted RPC, or is a self-hosted archive node required early?
- Ship Tier 3 prompt template here or in a separate issue?
- Schema versioning without invalidating historical backfills — migration policy?
