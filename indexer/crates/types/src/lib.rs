//! Canonical types shared across the indexer.
//!
//! Layout mirrors `docs/specs/intent-mapping.md` §Schema. Serialization rules
//! (SSZ, fixed widths, no floats) live in the spec — this crate holds the
//! in-memory representation.

use alloy_primitives::{Address, B256, U256};
use serde::{Deserialize, Serialize};

pub type Wei = U256;
pub type BlockNumber = u64;
pub type Timestamp = u64;
pub type Selector = [u8; 4];
pub type BasisPoints = u16;

/// Per-tx row extracted by the indexer. Append-only.
///
/// One row per transaction. Drives incremental profile updates.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TxFeatureRow {
    pub block: BlockNumber,
    pub tx_hash: B256,
    pub from: Address,
    pub to: Option<Address>,
    pub value_wei: Wei,
    pub gas_used: u64,
    pub gas_price_wei: Wei,
    pub selector: Option<Selector>,
    pub arg_summary: String,
    pub token_transfers: Vec<TokenTransfer>,
    pub ts: Timestamp,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenTransfer {
    pub token: Address,
    pub from: Address,
    pub to: Address,
    pub amount: Wei,
}

/// Rolling behavioral profile for an externally-owned account (or any address).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddressProfile {
    pub address: Address,
    pub first_seen_ts: Timestamp,
    pub chains_active: Vec<String>,
    pub tx_freq_per_day: Percentiles<u32>,
    pub tx_value_wei: Percentiles<Wei>,
    pub active_hours_mask_utc: u32,
    pub counterparties_top_k: Vec<Address>,
    pub protocols_top_k: Vec<String>,
    pub function_sigs_top_k: Vec<Selector>,
    pub gas_price_percentile: u8,
    pub risk_flags: u32,
    pub anomaly_score_bp: BasisPoints,
    pub profile_version: u32,
    pub updated_at_block: BlockNumber,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContractProfile {
    pub contract: Address,
    pub contract_type: String,
    pub daily_active_users: Percentiles<u32>,
    pub daily_volume_usd: Percentiles<u64>,
    pub tvl_usd: Percentiles<u64>,
    pub common_function_sigs: Vec<Selector>,
    pub param_ranges_json: String,
    pub upgrade_history_count: u32,
    pub anomaly_score_bp: BasisPoints,
    pub profile_version: u32,
    pub updated_at_block: BlockNumber,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Percentiles<T> {
    pub p50: T,
    pub p95: T,
    pub p99: T,
}

/// Screening verdict for a single tx, produced by a `Screener`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Flag {
    Green,
    Yellow,
    Orange,
    Red,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Tier {
    One,
    Two,
    Three,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScreeningResult {
    pub tx_hash: B256,
    pub flag: Flag,
    pub score_bp: BasisPoints,
    pub tier: Tier,
    pub reasons: Vec<String>,
}

#[derive(Debug, thiserror::Error)]
pub enum TypesError {
    #[error("canonical-encoding error: {0}")]
    Encoding(String),
}
