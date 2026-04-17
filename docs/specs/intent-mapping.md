# Intent Mapping — Address/Contract Behavioral Profile Storage

**Spec Version:** 1.0  
**Author:** Bob  
**Date:** 2026-04-17  
**Status:** Draft  
**Depends on:** None (prerequisite for #8, #10)  
**Drives:** Soul hash (#10), Training pipeline (#8)

---

## Overview

The intent map is the data store holding per-address and per-contract behavioral profiles. Validators read it during Tier 1/2 screening to answer: *"is this transaction normal for this address?"*. The `profile_root` in each block commits to the canonical dataset — so this store's content must be deterministic and reproducible.

### Data Flow

```
On-chain events (L1/L2)
    │
    ▼
┌─────────────────────────────────┐
│  Indexer (Envio or custom)       │
│  Extracts per-tx features         │
│  Writes to: tx_feature_log        │
└───────────────┬─────────────────┘
                │ batch / stream
                ▼
┌─────────────────────────────────┐
│  Feature Aggregator              │
│  Updates rolling windows          │
│  Writes to: address_profile       │
│             contract_profile      │
└───────────────┬─────────────────┘
                │ periodic (per epoch)
                ▼
┌─────────────────────────────────┐
│  Profile Hasher (#10)            │
│  Computes canonical root          │
│  Writes to: profile_epoch         │
└─────────────────────────────────┘
                │
                ▼ (read path)
┌─────────────────────────────────┐
│  Screening API                   │
│  Point lookup: is this normal?   │
│  Latency target: <10ms P99       │
└─────────────────────────────────┘
```

---

## Datastore Architecture

### ClickHouse (Primary Analytical Store)

ClickHouse for:
- Massive scan performance on aggregations
- Native time-series support (MATERIALIZED VIEWs)
- Compression for storage efficiency
- SQL interface for tooling

**Why not Postgres/TimescaleDB:**  
TimescaleDB is fine for <10M rows. At 100M+ rows and high write throughput, ClickHouse handles it without tuning. We're designing for L2 scale from day one.

### Hot Cache (LMDB or RocksDB)

For the <10ms P99 point lookup path:
- Validators need single-address lookups in microseconds
- ClickHouse is too slow for real-time screening reads
- Cache the current epoch's active profiles in an embedded KV store
- **LMDB** chosen: simpler, no compaction pauses, proven in Bitcoin Core

```
Lookup path:
1. Check LMDB cache for address
2. If miss → query ClickHouse → populate cache
3. Return ProfileEntry
```

Cache invalidation: on new `profile_epoch`, swap to new LMDB snapshot (atomic swap, no partial reads).

---

## Schema

### Table 1: `address_profile`

Current behavioral profile for each address.

```sql
CREATE TABLE address_profile (
    address          FixedString(20)  NOT NULL,
    epoch            UInt64          NOT NULL,
    updated_at       DateTime        NOT NULL,
    
    -- Core features
    tx_count_30d    UInt64          DEFAULT 0,
    avg_value_30d   UInt256         DEFAULT 0,  -- wei, as string
    max_value_30d   UInt256         DEFAULT 0,
    active_hours    FixedString(3)  DEFAULT '\\x000000',  -- 72-bit bitfield
    
    -- Graph features
    counterparty_count UInt32        DEFAULT 0,
    protocol_count    UInt16        DEFAULT 0,
    top_counterparties JSON          DEFAULT '{}',  -- address → count
    
    -- Thresholds (basis points)
    value_threshold_bp      UInt16 DEFAULT 500,
    frequency_threshold_bp  UInt16 DEFAULT 300,
    new_counterparty_threshold_bp UInt16 DEFAULT 200,
    
    -- Risk signals
    risk_flags       UInt16        DEFAULT 0,  -- bitfield
    anomaly_score_bp UInt16        DEFAULT 0,  -- 0-10000 bp
    
    -- Metadata
    first_tx_epoch   UInt64        DEFAULT 0,
    profile_type     UInt8         DEFAULT 0,  -- 0=EOA, 1=contract
    
    PRIMARY KEY (address, epoch)
) ENGINE = ReplacingMergeTree(epoch)
ORDER BY (address, epoch);
```

### Table 2: `contract_profile`

```sql
CREATE TABLE contract_profile (
    contract         FixedString(20) NOT NULL,
    epoch            UInt64          NOT NULL,
    updated_at       DateTime        NOT NULL,
    
    -- Classification
    contract_type    UInt8          DEFAULT 0,  -- 0=unknown, 1=DEX, 2=lending, 3=bridge, 4=NFT, 5=gov
    
    -- Volume features
    dau_30d         UInt64          DEFAULT 0,
    volume_30d      UInt256         DEFAULT 0,  -- USD (stored as wei-equivalent)
    tvl_current     UInt256         DEFAULT 0,
    tvl_range_low   UInt256         DEFAULT 0,
    tvl_range_high  UInt256         DEFAULT 0,
    
    -- Behavioral
    common_functions JSON            DEFAULT '[]',  -- [func_sig, ...]
    param_ranges    JSON            DEFAULT '{}',  -- {func_sig: {param: [min, max]}}
    upgrade_count   UInt16          DEFAULT 0,
    last_upgrade_epoch UInt64       DEFAULT 0,
    
    -- Thresholds
    volume_threshold_bp UInt16      DEFAULT 500,
    param_threshold_bp  UInt16      DEFAULT 300,
    
    anomaly_score_bp UInt16         DEFAULT 0,
    
    PRIMARY KEY (contract, epoch)
) ENGINE = ReplacingMergeTree(epoch)
ORDER BY (contract, epoch);
```

### Table 3: `tx_feature_log`

Immutable log of per-transaction features, used to recompute profiles.

```sql
CREATE TABLE tx_feature_log (
    tx_hash         FixedString(32) NOT NULL,
    block_number    UInt64          NOT NULL,
    block_timestamp DateTime        NOT NULL,
    epoch           UInt64          NOT NULL,
    
    sender          FixedString(20) NOT NULL,
    receiver        FixedString(20) DEFAULT '\\x00000000000000000000',
    value           UInt256         DEFAULT 0,
    gas_used         UInt64         DEFAULT 0,
    
    -- Decoded
    contract_called FixedString(20) DEFAULT '\\x00000000000000000000',
    func_sig       FixedString(4)  DEFAULT '\\x00000000',
    
    -- Features
    is_new_address  UInt8           DEFAULT 0,
    is_new_counterparty UInt8        DEFAULT 0,
    value_bp_vs_avg UInt16          DEFAULT 0,  -- basis points vs 30d avg
    hour_bucket     UInt8           DEFAULT 0,  -- 0-23 UTC
    
    PRIMARY KEY (tx_hash)
) ENGINE = MergeTree()
ORDER BY (block_number, tx_hash);
```

### Table 4: `profile_epoch`

Canonical snapshots of the profile dataset at each epoch boundary.

```sql
CREATE TABLE profile_epoch (
    epoch           UInt64          NOT NULL,
    created_at      DateTime        NOT NULL,
    
    -- Merkle tree root (from #10)
    profile_root    FixedString(32) NOT NULL,
    
    -- Stats
    address_count   UInt64          DEFAULT 0,
    contract_count  UInt64          DEFAULT 0,
    
    -- Status
    status          UInt8           DEFAULT 0,  -- 0=computing, 1=canonical, 2=finalized
    
    PRIMARY KEY (epoch)
) ENGINE = ReplacingMergeTree(epoch)
ORDER BY epoch;
```

---

## SSZ Encoding (for Soul Hash Input)

All profile data is SSZ-encoded for the Merkle tree hashing (#10).

### AddressProfileWrapper

```go
type AddressProfileWrapper struct {
    Address           [20]byte
    Entry             ProfileEntry  // Same ProfileEntry as in soul-hash.md
}

func (a *AddressProfileWrapper) Hash() [32]byte {
    return keccak256(encodeSSZ(a))
}
```

### Encoding Rules

- `UInt256` (value): big-endian 32-byte uint
- `JSON` fields: NOT SSZ-encoded; these are derived/debug fields, not committed
- `active_hours`: 3 bytes, packed bitfield (72 bits for 72 8-hour windows)
- `risk_flags`: 2 bytes, bitfield

---

## Cold Start Policy

When an address has no history (new or bridging in):

### Default Strict Profile

```
new_address_profile = ProfileEntry {
    value_threshold_bp:      200,  // 2% deviation → flag
    frequency_threshold_bp:  100,  // 1% deviation → flag
    new_counterparty_threshold_bp: 100,
    anomaly_score: 0,
    risk_flags: NEW_ADDRESS,
    profile_type: UNKNOWN,
}
```

### Bridge Inheritance

When address bridges from L1:
1. Query L1 history via archive RPC (Infura/Alchemy)
2. Pre-populate `address_profile` with L1 behavioral data
3. Inherit `profile_type`, `tx_count_30d`, `avg_value_30d`
4. Set `risk_flags |= L1_HISTORY_PRESENT`

### Gradual Unstrictening

After N normal transactions on Aegis, thresholds relax:

| Consecutive normal txs | Value threshold BP | Frequency threshold BP |
|------------------------|-------------------|----------------------|
| 0 (new)               | 200               | 100                  |
| 10                    | 300               | 200                  |
| 50                    | 500               | 400                  |
| 200                   | 800               | 600                  |

Thresholds reset to strict on any flagged transaction.

---

## Screening API

### GetAddressProfile

```go
func (s *Store) GetAddressProfile(ctx context.Context, address [20]byte, epoch uint64) (*ProfileEntry, error) {
    // 1. Try LMDB cache
    key := append(address[:], epochVarint()...)
    if entry, ok := s.lmdb.Get(key); ok {
        return deserializeProfile(entry), nil
    }
    
    // 2. ClickHouse fallback
    var entry ProfileEntry
    err := s.ch.QueryRow(
        "SELECT * FROM address_profile WHERE address = ? AND epoch = ?",
        address, epoch,
    ).Scan(&entry)
    if err != nil {
        return nil, err
    }
    
    // 3. Populate cache
    s.lmdb.Put(key, serializeProfile(entry))
    
    return &entry, nil
}
```

**Latency target:** <10ms P99 for cached lookups.

### UpdateProfile (batch)

```go
func (s *Store) BatchUpdateProfiles(entries []ProfileEntry) error {
    // Write to ClickHouse in batches of 1000
    for _, batch := range chunk(entries, 1000) {
        s.ch.Insert("address_profile", batch)
    }
    return nil
}
```

---

## Privacy Modes

### Testnet: Fully Public

All profiles publicly readable. Full transparency for debugging. No encryption.

### Mainnet: Public Hash / Private Detail

- Profile entries encrypted with a per-epoch symmetric key
- Root commits to encrypted values
- Validators prove (via ZK) that their local profile matches the root without revealing it
- **v1:** Use this mode

### v2: Fully Private

- Profiles never exposed
- Validators use TEE (e.g., AWS Nitro) to attest to profile contents
- Zero-knowledge proof of correct screening

---

## Open Questions for Jonto

1. **Latency target for screening reads:** Is <10ms P99 the right number? Or do we need <1ms?
2. **Data pipeline:** Build custom indexer (Rust/Go) or use Envio/GoldSky? Custom = more control, Envio = faster to ship.
3. **Privacy:** Is public profile data acceptable for v1? Or do you want encrypted-from-day-one?
4. **New contract detection:** Who classifies contract type — automated or manual?
5. **Profile staleness:** Max acceptable age of profile data before screening should flag it?

---

## Acceptance Criteria

- [x] ADR: datastore choice + privacy posture (this doc)
- [ ] DDL for all four tables (ClickHouse)
- [ ] SSZ encoding spec for ProfileEntry (see soul-hash.md)
- [ ] Point-lookup benchmark harness + results
- [ ] Cold-start policy implemented
- [ ] Screening API interface defined
- [ ] Interface with #8 (writer) and #10 (hasher) specified
