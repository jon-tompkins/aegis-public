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

### Byte-level example — a minimal `AddressProfile`

This is the canonical SSZ encoding of a tiny profile so future contributors have ground truth to test against.

**Inputs**

```
address                = 0x000000000000000000000000000000000000dEaD
first_seen_ts          = 1_700_000_000   (Tue Nov 14 22:13:20 UTC 2023)
chains_active          = ["ethereum"]
tx_freq_per_day_p50    = 12
tx_freq_per_day_p95    = 47
tx_value_wei_p50       = 0x0de0b6b3a7640000     (1 ETH = 1e18 wei)
tx_value_wei_p95       = 0x1bc16d674ec80000     (2 ETH)
tx_value_wei_p99       = 0x4563918244f40000     (5 ETH)
active_hours_mask_utc  = 0x0000_f000            (hours 12..15 UTC)
counterparties_top_k   = []                     (none yet)
protocols_top_k        = []
function_sigs_top_k    = [0xa9059cbb]           (ERC-20 transfer)
gas_price_percentile   = 45
risk_flags             = 0
anomaly_score_bp       = 250                    (2.5%)
profile_version        = 1
updated_at_block       = 21_000_000
```

**Layout rules** (applied in field order):
1. Fixed-size scalars written little-endian at declared width (`UInt8/16/32/64/256`).
2. `Address` = `Bytes20`, written raw.
3. Variable-size fields (`Vec<T>`, `String`) are SSZ-variable — the fixed part holds a `u32` offset (pointing past the end of the fixed region); the variable part is appended in declaration order.
4. `LowCardinality(String)` → UTF-8 bytes preceded by a 4-byte length.
5. `FixedString(4)` selector → raw 4 bytes. Fixed-length `Vec<FixedString(4)>` of top-k is a variable-size field with a 4-byte length prefix inside the variable region.

**Encoded bytes** (hex, whitespace for the reader only — ignored in `keccak256`):

```
# --- fixed region ---
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00   # address[0..16]
00 00 00 00 00 00 de ad                           # address[16..20]
00 bb 72 65 00 00 00 00                           # first_seen_ts u64 LE (0x656572bb00)
30 01 00 00                                       # offset → chains_active (48 = 0x30)
0c 00 00 00                                       # tx_freq_per_day_p50
2f 00 00 00                                       # tx_freq_per_day_p95
# 32-byte little-endian U256 each for the three value percentiles:
00 00 64 a7 b3 b6 e0 0d 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00   # p50 = 1e18
00 00 c8 4e 67 6d c1 1b 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00   # p95 = 2e18
00 00 f4 44 82 91 63 45 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00   # p99 = 5e18
00 f0 00 00                                       # active_hours_mask_utc
40 01 00 00                                       # offset → counterparties_top_k
44 01 00 00                                       # offset → protocols_top_k
48 01 00 00                                       # offset → function_sigs_top_k
2d                                                # gas_price_percentile u8
00 00 00 00                                       # risk_flags u32
fa 00                                             # anomaly_score_bp u16 (250)
01 00 00 00                                       # profile_version u32
40 6b 40 01 00 00 00 00                           # updated_at_block u64 (21_000_000)

# --- variable region ---
# chains_active: list of LowCardinality(String) "ethereum"
01 00 00 00                                       # list length = 1
08 00 00 00                                       # string length = 8
65 74 68 65 72 65 75 6d                           # "ethereum"

# counterparties_top_k: empty list
00 00 00 00

# protocols_top_k: empty list
00 00 00 00

# function_sigs_top_k: [0xa9059cbb]
01 00 00 00                                       # list length = 1
a9 05 9c bb                                       # selector
```

**Resulting `profile_leaf`** (SSZ bytes above, keccak'd):

```
keccak256(canonical_bytes) = 0xBF75…LEAF   (compute at implementation time, commit in test vectors)
```

Test vectors belong in `indexer/crates/types/tests/ssz_vectors.rs` (to be added once a concrete SSZ library is pinned — see open question below).

### Open question — SSZ library pin

Rust SSZ ecosystem options:
- `ssz_rs` — clean API, active, no consensus-client-specific baggage
- `ethereum_ssz` (Lighthouse) — battle-tested, larger surface
- `milagro-bls`-adjacent bespoke encoder — only if we need custom types

Decision lands with #10 (soul hash) since the same library produces `profile_root`.

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
