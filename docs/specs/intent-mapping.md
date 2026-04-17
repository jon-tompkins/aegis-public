# Address / Contract Intent Mapping

**Status:** Draft (tracks [#7](https://github.com/jon-tompkins/aegis-public/issues/7))
**Phase:** 0 — design
**Related:** [`aegis-training-plan.md`](../../aegis-training-plan.md), [`aegis-chain-design.md`](../../aegis-chain-design.md), [soul-hash.md](./soul-hash.md)

---

## Purpose

Design the store that holds per-address and per-contract behavioral profiles — the "intent map". This is the data substrate validators read during Tier 1/2 screening, and the dataset that `profile_root` (soul hash) commits over.

Decisions here constrain screening latency, per-tx cost, what's public vs. private, and how profiles drift.

## Goals

- Sub-50ms point lookup by address or contract during tx screening.
- Incremental updates per tx without full recompute.
- Canonical serialization so all validators produce the same Merkle root.
- Clear answer for what's public vs. private.

## Non-goals

- Training the models themselves (see [training-pipeline.md](./training-pipeline.md)).
- Hashing / attestation mechanics (see [soul-hash.md](./soul-hash.md)).
- Long-term decentralized storage / IPFS replication — deferred.

## 1. Datastore selection

Benchmark against a realistic workload (1M addresses, ~100 tx/s ingest, 1k lookups/s):

| Option | Pros | Cons | Notes |
|---|---|---|---|
| **ClickHouse** | Columnar, fast aggregations, cheap storage, great for backfills | Not ideal for single-row point lookups, eventual consistency | Primary candidate |
| TimescaleDB | Postgres semantics, good hypertables, transactional | Heavier writes at scale, less columnar benefit | Good if SQL-native preferred |
| Postgres + `pg_partman` + JSONB | Operational simplicity, single DB | Worst at scale, JSONB bloats | Fallback only |

**Likely split:** ClickHouse for feature store and aggregations, plus an in-process LMDB/RocksDB cache for hot profile lookups during screening.

## 2. Schema (v0)

Starts from the profile shapes in `aegis-training-plan.md`.

### `address_profile`

| Column | Type | Notes |
|---|---|---|
| `address` | `FixedString(20)` (pkey) | raw 20-byte address |
| `first_seen_ts` | `DateTime` | first tx observed |
| `chains_active` | `Array(LowCardinality(String))` | `ethereum`, `base`, … |
| `tx_freq_per_day_p50/p95` | `UInt32` | rolling 30d |
| `tx_value_wei_p50/p95/p99` | `UInt256` | rolling 30d |
| `active_hours_mask_utc` | `UInt32` (bitmask 0..23) | |
| `counterparties_top_k` | `Array(FixedString(20))` | k=16 |
| `protocols_top_k` | `Array(LowCardinality(String))` | labels |
| `function_sigs_top_k` | `Array(FixedString(4))` | 4-byte selectors |
| `gas_price_percentile` | `UInt8` | 0..100 |
| `risk_flags` | `UInt32` bitmask | mixer, new, proxy_creator, … |
| `anomaly_score_bp` | `UInt16` | 0..10000 basis points |
| `profile_version` | `UInt32` | schema version |
| `updated_at_block` | `UInt64` | |

### `contract_profile`

| Column | Type | Notes |
|---|---|---|
| `contract` | `FixedString(20)` (pkey) | |
| `type` | `LowCardinality(String)` | `dex`, `lending`, `bridge`, `nft`, `other` |
| `daily_active_users_p50/p95` | `UInt32` | |
| `daily_volume_usd_p50/p95` | `UInt64` | |
| `tvl_usd_p50/p95` | `UInt64` | |
| `common_function_sigs` | `Array(FixedString(4))` | |
| `param_ranges_json` | `String` | canonical-JSON, per-selector ranges |
| `upgrade_history_count` | `UInt32` | |
| `anomaly_score_bp` | `UInt16` | |
| `profile_version` | `UInt32` | |
| `updated_at_block` | `UInt64` | |

### `tx_feature_log` (append-only)

Per-tx features extracted by the indexer. Drives incremental updates.

| Column | Type |
|---|---|
| `block` | `UInt64` |
| `tx_hash` | `FixedString(32)` |
| `from`, `to` | `FixedString(20)` |
| `value_wei` | `UInt256` |
| `gas_used`, `gas_price_wei` | `UInt64`, `UInt256` |
| `selector` | `FixedString(4)` |
| `arg_summary` | `String` (length-bounded canonical JSON) |
| `token_transfers` | `Array(Tuple(token FixedString(20), from FixedString(20), to FixedString(20), amount UInt256))` |
| `ts` | `DateTime` |

### `profile_epoch`

Snapshot per epoch, feeds the soul hash.

| Column | Type |
|---|---|
| `epoch` | `UInt64` (pkey) |
| `address_root` | `FixedString(32)` |
| `contract_root` | `FixedString(32)` |
| `meta_hash` | `FixedString(32)` |
| `profile_root` | `FixedString(32)` |
| `schema_version` | `UInt32` |
| `created_at_block` | `UInt64` |

## 3. Privacy model — v1 recommendation

| Option | Visibility | Attacker advantage | Verifiability |
|---|---|---|---|
| **Fully public** | Anyone queries | Can map blind spots | Trivial — everyone hashes the same data |
| **Validator-private** | Validators only | Hidden from attackers | Requires ZK or TEE attestation |
| **Public-hash, private-detail** | Public Merkle root, detail held by validators; subset revealed on dispute | Structural leak but thresholds stay hidden | Commit-reveal |

**Recommendation:** **fully public for testnet** (simple, debuggable), migrate to **public-hash / private-detail** before mainnet.

## 4. Canonical serialization

Profile records must serialize byte-identically across validators so `profile_root` is reproducible.

Rules:
- SSZ (simple serialize) — fixed layout, auditable, already Ethereum-consensus-grade.
- All numeric fields fixed-width (`UInt8/16/32/64/256`).
- Arrays length-prefixed; top-k arrays sorted by a canonical key (e.g. descending count, ties broken by address lexicographic).
- Strings ASCII / UTF-8 with length prefix; `LowCardinality` expands to its string form at serialization time.
- No floating point anywhere — scores in basis points (`UInt16`).

Version field mandatory; any schema change bumps `profile_version` and triggers a re-snapshot at the next epoch boundary.

## 5. Default profile for new / cold addresses

Strict mode until proven normal:

- Unseen address with no bridge history: `anomaly_score_bp = 5000` (50%) default; all Tier 1 rules run with tight thresholds.
- Unseen address with bridge-in from L1: pull L1 profile (if indexed) and mark with `profile_version ≥ 1_bridged`.
- Graduation: after N=30 benign txs with no Tier 2 hits, relax to standard thresholds.

## 6. Hot cache

In-process LMDB or RocksDB keyed on `address` / `contract`. Holds the most recently accessed ~100k profiles plus all currently escalated. Eviction LRU. Consistent with ClickHouse via append-only log tail.

## Acceptance criteria

- [ ] ADR merged covering datastore choice and testnet privacy posture
- [ ] ClickHouse DDL for the four tables above
- [ ] SSZ / canonical encoding spec with byte-level examples
- [ ] Benchmark harness + results for point lookup under target load
- [ ] Cold-start policy implemented and documented
- [ ] Integration points with training pipeline (writer) and soul hash (root producer) documented

## Open questions

- Are profiles ever mutable in place, or append-only with epoch snapshots? (Epoch snapshots are likely required for soul-hash stability.)
- Hot cache — inside the validator process, or a sidecar over Unix socket?
- Under private-detail, what's the exact dispute-reveal protocol?
