//! Per-tx feature extraction.
//!
//! Input: [`RawBlock`] from `aegis-ingest`.
//! Output: [`TxFeatureRow`] — one per tx — matching the
//! `tx_feature_log` schema in `docs/specs/intent-mapping.md`.

use aegis_ingest::RawBlock;
use aegis_types::{Selector, TokenTransfer, TxFeatureRow};

pub fn extract_block(block: &RawBlock) -> Vec<TxFeatureRow> {
    block
        .txs
        .iter()
        .map(|tx| TxFeatureRow {
            block: block.number,
            tx_hash: tx.hash,
            from: alloy_primitives::Address::ZERO, // TODO: decode from signed tx
            to: None,                              // TODO
            value_wei: aegis_types::Wei::ZERO,     // TODO
            gas_used: tx.receipt.gas_used,
            gas_price_wei: aegis_types::Wei::ZERO, // TODO
            selector: decode_selector(&tx.input),
            arg_summary: String::new(), // TODO: bounded canonical JSON
            token_transfers: decode_token_transfers(&tx.receipt.logs),
            ts: block.timestamp,
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

fn decode_token_transfers(_logs: &[aegis_ingest::RawLog]) -> Vec<TokenTransfer> {
    // TODO: decode ERC-20 Transfer(address,address,uint256),
    // ERC-721 Transfer(address,address,uint256), ERC-1155 TransferSingle/Batch.
    Vec::new()
}
