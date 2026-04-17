-- ClickHouse DDL for the aegis profile store (v0).
--
-- Canonical source: docs/specs/intent-mapping.md §Schema (Bob's spec).
-- Apply with:  clickhouse-client --multiquery < indexer/sql/001_initial_schema.sql
--
-- Open reconciliation item: Bob's intent-mapping.md §Encoding Rules says
-- UInt256 is big-endian. SSZ canon is little-endian. Before real test
-- vectors ship, pick one and pin it in both intent-mapping.md and
-- indexer/crates/types/src/lib.rs.

CREATE DATABASE IF NOT EXISTS aegis;

-- ---------------------------------------------------------------------------
-- address_profile: current behavioral profile for each address.
-- ReplacingMergeTree on (address, epoch) — latest epoch wins.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aegis.address_profile
(
    address                         FixedString(20) NOT NULL,
    epoch                           UInt64 NOT NULL,
    updated_at                      DateTime NOT NULL,

    -- Core behavioral features
    tx_count_30d                    UInt64 DEFAULT 0,
    avg_value_30d                   UInt256 DEFAULT 0,
    max_value_30d                   UInt256 DEFAULT 0,
    active_hours                    FixedString(3) DEFAULT unhex('000000'),

    -- Graph features
    counterparty_count              UInt32 DEFAULT 0,
    protocol_count                  UInt16 DEFAULT 0,
    top_counterparties              String DEFAULT '{}',

    -- Thresholds (basis points)
    value_threshold_bp              UInt16 DEFAULT 500,
    frequency_threshold_bp          UInt16 DEFAULT 300,
    new_counterparty_threshold_bp   UInt16 DEFAULT 200,

    -- Risk signals
    risk_flags                      UInt16 DEFAULT 0,
    anomaly_score_bp                UInt16 DEFAULT 0,

    -- Metadata
    first_tx_epoch                  UInt64 DEFAULT 0,
    profile_type                    UInt8 DEFAULT 0
)
ENGINE = ReplacingMergeTree(epoch)
ORDER BY (address, epoch);

-- ---------------------------------------------------------------------------
-- contract_profile
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aegis.contract_profile
(
    contract                FixedString(20) NOT NULL,
    epoch                   UInt64 NOT NULL,
    updated_at              DateTime NOT NULL,

    -- Classification: 0=unknown, 1=DEX, 2=lending, 3=bridge, 4=NFT, 5=gov
    contract_type           UInt8 DEFAULT 0,

    -- Volume features
    dau_30d                 UInt64 DEFAULT 0,
    volume_30d              UInt256 DEFAULT 0,
    tvl_current             UInt256 DEFAULT 0,
    tvl_range_low           UInt256 DEFAULT 0,
    tvl_range_high          UInt256 DEFAULT 0,

    -- Behavioral (JSON; not part of soul-hash input)
    common_functions        String DEFAULT '[]',
    param_ranges            String DEFAULT '{}',

    upgrade_count           UInt16 DEFAULT 0,
    last_upgrade_epoch      UInt64 DEFAULT 0,

    -- Thresholds
    volume_threshold_bp     UInt16 DEFAULT 500,
    param_threshold_bp      UInt16 DEFAULT 300,

    anomaly_score_bp        UInt16 DEFAULT 0
)
ENGINE = ReplacingMergeTree(epoch)
ORDER BY (contract, epoch);

-- ---------------------------------------------------------------------------
-- tx_feature_log: append-only per-tx feature rows. Drives profile recomputes.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aegis.tx_feature_log
(
    tx_hash                 FixedString(32) NOT NULL,
    block_number            UInt64 NOT NULL,
    block_timestamp         DateTime NOT NULL,
    epoch                   UInt64 NOT NULL,

    sender                  FixedString(20) NOT NULL,
    receiver                FixedString(20) DEFAULT unhex('0000000000000000000000000000000000000000'),
    value                   UInt256 DEFAULT 0,
    gas_used                UInt64 DEFAULT 0,

    -- Decoded
    contract_called         FixedString(20) DEFAULT unhex('0000000000000000000000000000000000000000'),
    func_sig                FixedString(4)  DEFAULT unhex('00000000'),

    -- Features
    is_new_address          UInt8 DEFAULT 0,
    is_new_counterparty     UInt8 DEFAULT 0,
    value_bp_vs_avg         UInt16 DEFAULT 0,
    hour_bucket             UInt8 DEFAULT 0
)
ENGINE = MergeTree
ORDER BY (block_number, tx_hash);

-- ---------------------------------------------------------------------------
-- profile_epoch: per-epoch snapshot feeding soul hash (see docs/specs/soul-hash.md)
-- Status: 0=computing, 1=canonical, 2=finalized
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aegis.profile_epoch
(
    epoch           UInt64 NOT NULL,
    created_at      DateTime NOT NULL,

    profile_root    FixedString(32) NOT NULL,

    address_count   UInt64 DEFAULT 0,
    contract_count  UInt64 DEFAULT 0,

    status          UInt8 DEFAULT 0
)
ENGINE = ReplacingMergeTree(epoch)
ORDER BY epoch;
