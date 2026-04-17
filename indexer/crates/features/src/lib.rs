//! Per-tx feature extraction.
//!
//! Input: [`RawBlock`] from `aegis-ingest`.
//! Output: [`TxFeatureRow`] — one per tx — matching the `tx_feature_log`
//! schema in `docs/specs/intent-mapping.md`.

use aegis_ingest::RawBlock;
use aegis_types::{Selector, TxFeatureRow};

pub fn extract_block(block: &RawBlock, epoch: u64) -> Vec<TxFeatureRow> {
    block
        .txs
        .iter()
        .map(|tx| TxFeatureRow {
            tx_hash: tx.hash,
            block_number: block.number,
            block_timestamp: block.timestamp,
            epoch,
            sender: alloy_primitives::Address::ZERO, // TODO: decode from signed tx
            receiver: alloy_primitives::Address::ZERO, // TODO
            value: aegis_types::Wei::ZERO,           // TODO
            gas_used: tx.receipt.gas_used,
            contract_called: alloy_primitives::Address::ZERO, // TODO
            func_sig: decode_selector(&tx.input).unwrap_or([0u8; 4]),
            is_new_address: false,      // TODO: needs profile lookup
            is_new_counterparty: false, // TODO: needs profile lookup
            value_bp_vs_avg: 0,         // TODO: needs profile lookup
            hour_bucket: hour_bucket_from_ts(block.timestamp),
        })
        .collect()
}

fn decode_selector(input: &[u8]) -> Option<Selector> {
    if input.len() < 4 {
        return None;
    }
    let mut sel = [0u8; 4];
    sel.copy_from_slice(&input[..4]);
    Some(sel)
}

fn hour_bucket_from_ts(ts: u64) -> u8 {
    ((ts / 3600) % 24) as u8
}
