//! Profile read/write store.
//!
//! Trait-first so we can swap ClickHouse (primary) for LMDB (hot cache) or
//! in-memory (tests) without changing callers. See
//! `docs/specs/intent-mapping.md` §Datastore selection for the decision matrix.

use aegis_types::{AddressProfile, ContractProfile, TxFeatureRow};
use alloy_primitives::Address;
use async_trait::async_trait;

#[async_trait]
pub trait ProfileStore: Send + Sync {
    async fn append_tx_features(&self, rows: &[TxFeatureRow]) -> Result<(), ProfileError>;

    async fn get_address(&self, address: Address) -> Result<Option<AddressProfile>, ProfileError>;

    async fn put_address(&self, profile: &AddressProfile) -> Result<(), ProfileError>;

    async fn get_contract(&self, address: Address) -> Result<Option<ContractProfile>, ProfileError>;

    async fn put_contract(&self, profile: &ContractProfile) -> Result<(), ProfileError>;
}

#[derive(Debug, thiserror::Error)]
pub enum ProfileError {
    #[error("store error: {0}")]
    Store(String),
    #[error("not found")]
    NotFound,
}

/// In-memory store for tests and bring-up. Swap for ClickHouse before real use.
pub struct MemoryStore {
    inner: tokio::sync::RwLock<MemoryInner>,
}

#[derive(Default)]
struct MemoryInner {
    addresses: std::collections::HashMap<Address, AddressProfile>,
    contracts: std::collections::HashMap<Address, ContractProfile>,
    tx_log: Vec<TxFeatureRow>,
}

impl MemoryStore {
    pub fn new() -> Self {
        Self {
            inner: tokio::sync::RwLock::new(MemoryInner::default()),
        }
    }
}

impl Default for MemoryStore {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl ProfileStore for MemoryStore {
    async fn append_tx_features(&self, rows: &[TxFeatureRow]) -> Result<(), ProfileError> {
        let mut g = self.inner.write().await;
        g.tx_log.extend_from_slice(rows);
        Ok(())
    }

    async fn get_address(&self, address: Address) -> Result<Option<AddressProfile>, ProfileError> {
        Ok(self.inner.read().await.addresses.get(&address).cloned())
    }

    async fn put_address(&self, profile: &AddressProfile) -> Result<(), ProfileError> {
        self.inner
            .write()
            .await
            .addresses
            .insert(profile.address, profile.clone());
        Ok(())
    }

    async fn get_contract(&self, address: Address) -> Result<Option<ContractProfile>, ProfileError> {
        Ok(self.inner.read().await.contracts.get(&address).cloned())
    }

    async fn put_contract(&self, profile: &ContractProfile) -> Result<(), ProfileError> {
        self.inner
            .write()
            .await
            .contracts
            .insert(profile.contract, profile.clone());
        Ok(())
    }
}
