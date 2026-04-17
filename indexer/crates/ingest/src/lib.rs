//! Block / tx ingestion.
//!
//! Trait-first: any archive-RPC provider (Alchemy, Infura, self-hosted Erigon)
//! plugs in behind [`BlockSource`]. The reference impl [`AlchemySource`] is a
//! stub — fill it in when we start real ingestion.

use aegis_types::BlockNumber;
use alloy_primitives::B256;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawBlock {
    pub number: BlockNumber,
    pub hash: B256,
    pub timestamp: u64,
    pub txs: Vec<RawTx>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawTx {
    pub hash: B256,
    pub input: Vec<u8>,
    pub receipt: RawReceipt,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawReceipt {
    pub status: bool,
    pub gas_used: u64,
    pub logs: Vec<RawLog>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawLog {
    pub address: alloy_primitives::Address,
    pub topics: Vec<B256>,
    pub data: Vec<u8>,
}

#[async_trait]
pub trait BlockSource: Send + Sync {
    async fn latest_block(&self) -> Result<BlockNumber, IngestError>;
    async fn get_block(&self, number: BlockNumber) -> Result<RawBlock, IngestError>;
}

#[derive(Debug, thiserror::Error)]
pub enum IngestError {
    #[error("rpc error: {0}")]
    Rpc(String),
    #[error("decode error: {0}")]
    Decode(String),
}

/// Alchemy-backed block source. Stub until we wire alloy RPC.
pub struct AlchemySource {
    _rpc_url: String,
}

impl AlchemySource {
    pub fn new(rpc_url: impl Into<String>) -> Self {
        Self {
            _rpc_url: rpc_url.into(),
        }
    }
}

#[async_trait]
impl BlockSource for AlchemySource {
    async fn latest_block(&self) -> Result<BlockNumber, IngestError> {
        Err(IngestError::Rpc("AlchemySource not implemented yet".into()))
    }

    async fn get_block(&self, _number: BlockNumber) -> Result<RawBlock, IngestError> {
        Err(IngestError::Rpc("AlchemySource not implemented yet".into()))
    }
}
