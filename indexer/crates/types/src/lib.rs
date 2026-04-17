//! Canonical types shared across the indexer.
//!
//! Layout mirrors `docs/specs/intent-mapping.md` §Schema (v0, Bob's spec).
//! Serialization rules (SSZ, fixed widths, no floats) are in the spec —
//! this crate holds the in-memory representation.
//!
//! Open reconciliation item: the spec says `UInt256` is big-endian, SSZ canon
//! is little-endian. Pin a single answer in both files before shipping test
//! vectors.

use alloy_primitives::{Address, B256, U256};
use serde::{Deserialize, Serialize};

pub type Wei = U256;
pub type BlockNumber = u64;
pub type Timestamp = u64;
pub type Epoch = u64;
pub type Selector = [u8; 4];
pub type BasisPoints = u16;

/// Classification for `ContractProfile::contract_type`.
/// Wire value is a `u8` (see intent-mapping.md §Schema).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u8)]
pub enum ContractType {
    Unknown = 0,
    Dex = 1,
    Lending = 2,
    Bridge = 3,
    Nft = 4,
    Gov = 5,
}

/// Classification for `AddressProfile::profile_type`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u8)]
pub enum ProfileType {
    Eoa = 0,
    Contract = 1,
}

/// Per-tx row extracted by the indexer. Append-only.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TxFeatureRow {
    pub tx_hash: B256,
    pub block_number: BlockNumber,
    pub block_timestamp: Timestamp,
    pub epoch: Epoch,
    pub sender: Address,
    pub receiver: Address,
    pub value: Wei,
    pub gas_used: u64,
    pub contract_called: Address,
    pub func_sig: Selector,
    pub is_new_address: bool,
    pub is_new_counterparty: bool,
    pub value_bp_vs_avg: u16,
    pub hour_bucket: u8,
}

/// Rolling behavioral profile for an externally-owned account (or any address).
/// Matches `docs/specs/intent-mapping.md` `address_profile`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddressProfile {
    pub address: Address,
    pub epoch: Epoch,
    pub updated_at: Timestamp,

    pub tx_count_30d: u64,
    pub avg_value_30d: Wei,
    pub max_value_30d: Wei,
    /// 72-bit packed bitfield (3 bytes).
    pub active_hours: [u8; 3],

    pub counterparty_count: u32,
    pub protocol_count: u16,
    /// JSON-encoded map {address => count}. Not part of soul-hash input.
    pub top_counterparties: String,

    pub value_threshold_bp: BasisPoints,
    pub frequency_threshold_bp: BasisPoints,
    pub new_counterparty_threshold_bp: BasisPoints,

    pub risk_flags: u16,
    pub anomaly_score_bp: BasisPoints,

    pub first_tx_epoch: Epoch,
    pub profile_type: ProfileType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContractProfile {
    pub contract: Address,
    pub epoch: Epoch,
    pub updated_at: Timestamp,

    pub contract_type: ContractType,

    pub dau_30d: u64,
    pub volume_30d: Wei,
    pub tvl_current: Wei,
    pub tvl_range_low: Wei,
    pub tvl_range_high: Wei,

    /// JSON array of `func_sig` bytes. Not part of soul-hash input.
    pub common_functions: String,
    /// JSON `{func_sig: {param: [min, max]}}`. Not part of soul-hash input.
    pub param_ranges: String,

    pub upgrade_count: u16,
    pub last_upgrade_epoch: Epoch,

    pub volume_threshold_bp: BasisPoints,
    pub param_threshold_bp: BasisPoints,

    pub anomaly_score_bp: BasisPoints,
}

/// Per-epoch snapshot used by the soul-hash commitment (see soul-hash.md).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfileEpoch {
    pub epoch: Epoch,
    pub created_at: Timestamp,
    pub profile_root: B256,
    pub address_count: u64,
    pub contract_count: u64,
    /// 0=computing, 1=canonical, 2=finalized
    pub status: u8,
}

/// Screening verdict for a single tx. Matches `docs/specs/byo-model.md`
/// `ScreeningOutput`, expressed as a Rust type.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u8)]
pub enum Flag {
    Clear = 0,
    Watch = 1,
    Escalate = 2,
    Pause = 3,
    Reject = 4,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScreeningOutput {
    pub flag: Flag,
    pub confidence_bp: BasisPoints,
    pub reasoning_hash: B256,
    pub reasoning_snippet: String,
}

#[derive(Debug, thiserror::Error)]
pub enum TypesError {
    #[error("canonical-encoding error: {0}")]
    Encoding(String),
}
