-- ClickHouse DDL for the aegis profile store.
--
-- Matches docs/specs/intent-mapping.md §Schema (v0).
-- Apply with:  clickhouse-client --multiquery < sql/001_initial_schema.sql

CREATE DATABASE IF NOT EXISTS aegis;

-- ---------------------------------------------------------------------------
-- tx_feature_log: append-only per-tx rows emitted by the indexer.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aegis.tx_feature_log
(
    block            UInt64,
    tx_hash          FixedString(32),
    from             FixedString(20),
    to               FixedString(20),        -- zero-bytes for contract creation
    value_wei        UInt256,
    gas_used         UInt64,
    gas_price_wei    UInt256,
    selector         FixedString(4),         -- zero-bytes when input < 4 bytes
    arg_summary      String,                 -- bounded canonical JSON
    token_transfers  String,                 -- JSON array, decoded elsewhere
    ts               DateTime
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (block, tx_hash);

-- ---------------------------------------------------------------------------
-- address_profile: one row per address, overwritten on each update.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aegis.address_profile
(
    address                FixedString(20),
    first_seen_ts          DateTime,
    chains_active          Array(LowCardinality(String)),
    tx_freq_per_day_p50    UInt32,
    tx_freq_per_day_p95    UInt32,
    tx_value_wei_p50       UInt256,
    tx_value_wei_p95       UInt256,
    tx_value_wei_p99       UInt256,
    active_hours_mask_utc  UInt32,
    counterparties_top_k   Array(FixedString(20)),
    protocols_top_k        Array(LowCardinality(String)),
    function_sigs_top_k    Array(FixedString(4)),
    gas_price_percentile   UInt8,
    risk_flags             UInt32,
    anomaly_score_bp       UInt16,
    profile_version        UInt32,
    updated_at_block       UInt64
)
ENGINE = ReplacingMergeTree(updated_at_block)
ORDER BY address;

-- ---------------------------------------------------------------------------
-- contract_profile
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aegis.contract_profile
(
    contract               FixedString(20),
    type                   LowCardinality(String),
    daily_active_users_p50 UInt32,
    daily_active_users_p95 UInt32,
    daily_volume_usd_p50   UInt64,
    daily_volume_usd_p95   UInt64,
    tvl_usd_p50            UInt64,
    tvl_usd_p95            UInt64,
    common_function_sigs   Array(FixedString(4)),
    param_ranges_json      String,
    upgrade_history_count  UInt32,
    anomaly_score_bp       UInt16,
    profile_version        UInt32,
    updated_at_block       UInt64
)
ENGINE = ReplacingMergeTree(updated_at_block)
ORDER BY contract;

-- ---------------------------------------------------------------------------
-- profile_epoch: snapshot feeding the soul hash (see docs/specs/soul-hash.md)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aegis.profile_epoch
(
    epoch            UInt64,
    address_root     FixedString(32),
    contract_root    FixedString(32),
    meta_hash        FixedString(32),
    profile_root     FixedString(32),
    schema_version   UInt32,
    created_at_block UInt64
)
ENGINE = MergeTree
ORDER BY epoch;
