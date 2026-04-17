# Aegis Chain — Behavioral Model Training Plan

## Overview

Validators need to understand "normal" for every address and contract they see. This means building behavioral profiles from on-chain data, updating them in real-time, and using them to flag anomalies at tx-screening speed.

This is the core IP of the project. Get this right and everything else follows.

---

## What We're Building

### Per-Address Behavioral Profile

```json
{
  "address": "0xabc...",
  "first_seen": "2024-01-15",
  "chains_active": ["ethereum", "arbitrum", "base"],
  "typical": {
    "tx_frequency": "2-5/day",
    "tx_value_range": [0.01, 5.0],  // ETH
    "active_hours_utc": [14, 22],   // peak activity window
    "counterparties": ["0xuniswap...", "0xaave..."],
    "protocols": ["uniswap-v3", "aave-v3", "1inch"],
    "function_signatures": ["swap()", "deposit()", "approve()"],
    "gas_price_percentile": 40
  },
  "risk_signals": {
    "new_address": false,
    "mixer_interaction": false,
    "proxy_creation": false
  },
  "anomaly_score": 0.05  // 0=normal, 1=definitely suspicious
}
```

### Per-Contract Behavioral Profile

```json
{
  "contract": "0xdef...",
  "type": "dex",  // auto-classified
  "typical": {
    "daily_active_users": [50, 200],
    "daily_volume_range": [100000, 500000],  // USD
    "tvl_range": [5000000, 8000000],
    "upgrade_frequency": "never",
    "common_functions": ["swap()", "addLiquidity()"],
    "param_ranges": {
      "swap.amountIn": [10, 100000],
      "swap.slippage": [0.001, 0.05]
    }
  },
  "anomaly_score": 0.02
}
```

---

## Data Sources

### Phase 1: Historical Ingestion (Pre-Launch)

| Source | What We Get | How |
|--------|------------|-----|
| Ethereum L1 | Full tx history, contract interactions, event logs | RPC archive node + custom indexer |
| Major L2s (Arb, Base, Optimism) | Cross-chain behavior patterns | Public RPCs + Dune/Flipside |
| Etherscan/Blockscout | Contract metadata, labels, verified source | APIs |
| DeFi Llama | TVL, protocol metadata | API |
| Chainalysis/Elliptic (optional) | Known-risk address labels | Paid (later) |

**Data volume estimate:** ~2B transactions on Ethereum L1 alone. We don't need all of them — sampling recent history (12-18 months) for active addresses is sufficient for v1.

### Phase 2: Real-Time Indexing (Post-Launch)

- Index every Aegis tx as it happens
- Subscribe to L1/L2 events for addresses that bridge in
- Update profiles incrementally (not full recompute)

---

## Training Pipeline

### Stage 1: Data Ingestion & Feature Engineering

```
Raw on-chain data
    │
    ▼
┌─────────────────────┐
│ Feature Extraction   │    Per-tx features:
│                      │    - sender, receiver, value, gas
│                      │    - contract called, function sig
│                      │    - token transfers (log parsing)
│                      │    - time-of-day, day-of-week
│                      │
│                      │    Aggregated features:
│                      │    - rolling averages, percentiles
│                      │    - counterparty frequency
│                      │    - protocol interaction diversity
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Address Clustering   │    Group similar behavioral patterns
│                      │    - EOAs vs contract wallets
│                      │    - DeFi power users vs casual
│                      │    - MEV bots vs humans
│                      │    - Known protocol patterns
└──────────┬──────────┘
           │
           ▼
    Behavioral profiles (per address, per contract)
```

### Stage 2: Anomaly Detection Models

**Tier 1 — Heuristics (fastest, cheapest, always-on)**

Rule-based checks that catch 80% of obvious anomalies:
- Tx value 10x above address's historical max
- New function call on a contract that hasn't been used in 6 months
- Interaction with a contract < 24h old
- Sudden change in counterparty graph
- Proxy upgrade + large withdrawal in same block
- Known exploit signatures (re-entrancy pattern, flash loan + price manipulation)

**Tier 2 — Statistical Models (fast, cheap, always-on)**

- Isolation forest / Z-score on behavioral features
- Rolling window anomaly detection (compare last N txs to historical baseline)
- Outlier detection on contract param ranges

**Tier 3 — LLM Judgment (slower, expensive, escalation only)**

- Full tx context + behavioral profile fed to LLM
- "Given this address's history, does this transaction make sense?"
- Chain-of-thought reasoning for auditability
- Only triggered when Tier 1 or 2 flags something

### Stage 3: Continuous Learning

```
New txs on Aegis
    │
    ├── Normal txs ──► Update behavioral profile (incremental)
    │                   Retrain statistical models periodically
    │
    └── Flagged txs ──► Human council labels (correct/incorrect)
                         └─► Feedback loop into model training
```

**Critical:** Behavioral profiles drift naturally (users change behavior). The system needs to distinguish:
- **Normal drift** — user starts using a new protocol gradually
- **Sudden shift** — account compromise or exploit

Drift rate is itself a feature.

---

## Implementation Plan

### Sprint 1: Data Foundation (Weeks 1-4)

- [ ] Set up archive RPC access (Ethereum L1 + major L2s)
- [ ] Build custom indexer for feature extraction
  - Start with Go or Rust for throughput
  - Output: feature store (ClickHouse or similar)
- [ ] Define feature schema (per-tx, per-address, per-contract)
- [ ] Ingest 12 months of L1 history for top 1M active addresses
- [ ] Basic contract classifier (DEX, lending, bridge, NFT, etc.)

**Deliverable:** Feature store with historical profiles for active addresses.

### Sprint 2: Heuristics + Stats (Weeks 5-8)

- [ ] Implement Tier 1 rule engine
  - Define initial rule set (~50 rules based on known exploit patterns)
  - Test against historical exploits (replay known hacks)
- [ ] Implement Tier 2 statistical models
  - Isolation forest per-address anomaly scoring
  - Contract param range modeling
- [ ] Build screening API (input: tx, output: flag + score)
  - Target: <50ms response time for Tier 1+2 combined
- [ ] Historical backtesting
  - Replay known exploits, measure detection rate
  - Measure false positive rate on normal txs

**Deliverable:** Working screening pipeline with measurable precision/recall.

### Sprint 3: LLM Escalation (Weeks 9-12)

- [ ] Design escalation prompt template
  - Inject behavioral profile + tx context
  - Structured output (flag confidence, reasoning, recommended action)
- [ ] Model selection for escalation
  - Test ZAI (glm-4.5-flash for cheap, glm-5.1 for heavy)
  - Test local models for validators who want self-hosted
  - Benchmark: latency, cost, accuracy
- [ ] Build escalation voting mechanism
  - Validators independently evaluate
  - Threshold consensus (e.g. >2/3 must flag to reject)
- [ ] Feedback loop infrastructure
  - Store all flags + outcomes for retraining

**Deliverable:** End-to-end screening pipeline with LLM escalation.

### Sprint 4: Testnet Integration (Weeks 13-16)

- [ ] Fork OP Stack, inject screening into tx pipeline
- [ ] Deploy testnet with agent validators
- [ ] Live testing with historical exploit replays
- [ ] Tune thresholds (false positive vs false negative tradeoff)
- [ ] Stress test: can the pipeline handle peak throughput?

**Deliverable:** Working testnet where agents screen real transactions.

---

## Validation: Known Exploit Replay

The gold standard: can we catch the exploits everyone already knows about?

| Exploit | Type | Expected Detection Tier |
|---------|------|----------------------|
| Ronin Bridge | Compromised keys, unusual withdrawal | Tier 1 (value anomaly) |
| Wormhole | Smart contract bug, unauthorized mint | Tier 2 (param anomaly) |
| Poly Network | Cross-chain msg spoofing | Tier 1 (unusual cross-chain) |
| Mango Markets | Price oracle manipulation | Tier 2 + Tier 3 (complex) |
| Curve re-entrancy | Re-entrancy + pool drain | Tier 1 (known pattern) |
| Harmony Bridge | Compromised keys | Tier 1 (value + counterparty) |

Target: **>90% detection rate on known exploits with <1% false positive rate.**

---

## Cost Estimates

### Data Ingestion

| Item | Cost |
|------|------|
| Archive RPC (Alchemy/Infura) | $200-500/mo |
| ClickHouse cluster (feature store) | $100-300/mo |
| Compute for indexing | $200-400/mo (spot instances) |

### Inference (Per-Validator, Monthly)

| Tier | Volume | Cost/tx | Monthly |
|------|--------|---------|---------|
| Tier 1 (heuristics) | ~10M txs | ~$0.00001 | ~$100 |
| Tier 2 (stats) | ~10M txs | ~$0.00005 | ~$500 |
| Tier 3 (LLM escalation) | ~10K txs (0.1%) | ~$0.01 | ~$100 |
| **Total per validator** | | | **~$700/mo** |

This is rough. Tier 1+2 could be much cheaper with local compute. Tier 3 cost depends heavily on model choice and escalation rate.

---

## Open Questions

1. **Feature store:** ClickHouse, TimescaleDB, or custom? Need to benchmark for real-time updates + fast reads during screening.
2. **Model format:** Should validators share trained models, or just share profiles and each run their own? Shared models = faster iteration but centralization pressure.
3. **Privacy of profiles:** Are behavioral profiles public (anyone can query) or validator-private? Public = more transparency. Private = harder to game.
4. **Profile staleness:** How often do profiles need refreshing? Per-tx incremental? Periodic batch? What's the memory budget per address?
5. **New address handling:** What's the default profile for an address with no L1 history? Strict mode (low tolerance) until proven normal?
