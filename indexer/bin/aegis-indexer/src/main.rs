//! aegis-indexer — backfill + stream driver.
//!
//! Wires the four crates together. Still a skeleton: `AlchemySource` doesn't
//! hit real RPC yet, and `MemoryStore` is not the production path. Commands
//! exist so the pipeline shape is visible end-to-end.

use aegis_features::extract_block;
use aegis_ingest::{AlchemySource, BlockSource};
use aegis_profile::{MemoryStore, ProfileStore};
use aegis_screener::Tier1RuleEngine;
use aegis_types::BlockNumber;
use anyhow::Result;
use clap::{Parser, Subcommand};
use std::sync::Arc;

#[derive(Parser, Debug)]
#[command(name = "aegis-indexer", version)]
struct Cli {
    #[arg(long, env = "AEGIS_RPC_URL", default_value = "https://eth.example/rpc")]
    rpc_url: String,

    /// Epoch to tag ingested rows with. Real epoch derivation lives with the
    /// soul-hash spec (see docs/specs/soul-hash.md); for now callers pass it.
    #[arg(long, env = "AEGIS_EPOCH", default_value_t = 0)]
    epoch: u64,

    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand, Debug)]
enum Cmd {
    /// Backfill from `from` to `to` (inclusive).
    Backfill {
        #[arg(long)]
        from: BlockNumber,
        #[arg(long)]
        to: BlockNumber,
    },
    /// Follow the chain head.
    Stream,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .init();

    let cli = Cli::parse();

    let source: Arc<dyn BlockSource> = Arc::new(AlchemySource::new(cli.rpc_url.clone()));
    let store: Arc<dyn ProfileStore> = Arc::new(MemoryStore::new());
    let _screener = Tier1RuleEngine::new();

    match cli.cmd {
        Cmd::Backfill { from, to } => backfill(source, store, cli.epoch, from, to).await?,
        Cmd::Stream => stream(source, store, cli.epoch).await?,
    }
    Ok(())
}

async fn backfill(
    source: Arc<dyn BlockSource>,
    store: Arc<dyn ProfileStore>,
    epoch: u64,
    from: BlockNumber,
    to: BlockNumber,
) -> Result<()> {
    tracing::info!(epoch, from, to, "backfill starting");
    for n in from..=to {
        let block = source.get_block(n).await?;
        let rows = extract_block(&block, epoch);
        store.append_tx_features(&rows).await?;
    }
    Ok(())
}

async fn stream(
    source: Arc<dyn BlockSource>,
    store: Arc<dyn ProfileStore>,
    epoch: u64,
) -> Result<()> {
    tracing::info!(epoch, "stream starting");
    let mut next = source.latest_block().await?;
    loop {
        let head = source.latest_block().await?;
        while next <= head {
            let block = source.get_block(next).await?;
            let rows = extract_block(&block, epoch);
            store.append_tx_features(&rows).await?;
            next += 1;
        }
        tokio::time::sleep(std::time::Duration::from_secs(2)).await;
    }
}
