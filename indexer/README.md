# aegis-indexer

Reference indexer / feature pipeline for Aegis. Tracks [#8](https://github.com/jon-tompkins/aegis-public/issues/8).

**Status:** skeleton. The crate layout, trait boundaries, DB schema, and CLI shape are in place; the bodies of the RPC source, feature decoding, and ClickHouse store are stubs that return "not implemented yet."

See [`docs/specs/training-pipeline.md`](../docs/specs/training-pipeline.md) for the full spec and [`docs/specs/intent-mapping.md`](../docs/specs/intent-mapping.md) for the data schema.

## Layout

```
indexer/
├── Cargo.toml                 # workspace
├── crates/
│   ├── types/                 # canonical shared types
│   ├── ingest/                # BlockSource trait + AlchemySource stub
│   ├── features/              # per-tx feature extraction
│   ├── profile/               # ProfileStore trait + in-memory impl
│   └── screener/              # Screener trait + Tier 1 rule engine
├── bin/aegis-indexer/         # CLI binary (backfill | stream)
└── sql/001_initial_schema.sql # ClickHouse DDL
```

## Build

```
cd indexer
cargo build
```

## Run (once RPC + store are implemented)

```
# backfill a block range
AEGIS_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/<key> \
  cargo run --bin aegis-indexer -- backfill --from 21000000 --to 21000010

# follow the head
AEGIS_RPC_URL=... cargo run --bin aegis-indexer -- stream
```

## Next steps (checklist for #8)

- [ ] Wire `AlchemySource` to `alloy::providers::Provider` (blocks, receipts, traces)
- [ ] Decode logs in `aegis-features` (ERC-20/721/1155 `Transfer` + `TransferSingle`/`Batch`)
- [ ] Decode signed tx → `from`, `to`, `value`, `gas_price`
- [ ] Implement `ClickhouseStore: ProfileStore` on top of `clickhouse-rs`
- [ ] Port ~50 Tier 1 rules seeded from known exploit patterns
- [ ] Tier 2 reference model (IsolationForest via ONNX runtime or FFI)
- [ ] Backtest harness replaying the six exploits listed in the spec
- [ ] Reconciliation job against `tx_feature_log`
