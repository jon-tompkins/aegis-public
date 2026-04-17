# Blockchain Hack Taxonomy — Aegis Training Data

**Research Version:** 1.0  
**Author:** Bob  
**Date:** 2026-04-17  
**Source:** rekt.news + on-chain data  
**Status:** Research Complete  
**Drives:** Aegis Tier 1/2 screening models, exploit backtesting  

---

## Overview

This document catalogs major DeFi exploits by attack vector, to inform Aegis's behavioral screening models. The goal is to identify malicious patterns that Aegis validators can detect on-chain, before/during/after exploitation.

**Backtest target:** ≥90% detection, ≤1% FP on known exploits (Ronin, Wormhole, Poly, Mango, Curve, Harmony + others).

---

## Attack Vector Taxonomy

### 1. Bridge Exploit (Cross-Chain)

**What it is:** Attacker exploits the bridge contract to mint unbacked wrapped assets or drain liquidity.

**Mechanism:** Compromised validator set, fake proof, signature bypass, or proxy contract flaw.

| Exploit | Loss | Vector | Key Signal |
|---------|------|--------|------------|
| Ronin | $624M | Validator whitelist not revoked; 4-of-9 Sky Mavis keys compromised → needed 1 more sig from Axie DAO (whitelist never revoked) | Unused whitelist entries on bridge validators; validator set unchanged for months |
| Wormhole | $326M | Solana/Ethereum bridge: `verify_signatures` bypass via `sysvar::instructions` discrepancy | Single guardian signature sufficient; low-value guardian account |
| Poly Network | $611M | Cross-chain manager proxy call: `EthCrossChainData` contract called via `_method` sighash collision | Privileged contracts callable from cross-chain relay; no `isOwner` guard on `EthCrossChainData` |
| Qubit | $80M | Qubit Bridge: deposits recorded incorrectly, attacker claimed to have deposited 1 ETH when actual was 0 | Zero-value deposits recorded as non-zero |

**Aegis Screening Signals:**
- Bridge contract: unusually low guardian/validator threshold (e.g., <5 for large TVL)
- Validator set unchanged for >6 months
- Cross-chain relay calling privileged data contracts
- Sighash collision detection (monitor for known collision methods)
- Large minting events on bridge with no corresponding L1 deposit

---

### 2. Oracle Manipulation

**What it is:** Attacker manipulates asset price on a DEX or price feed, then exploits the mispricing.

| Exploit | Loss | Vector | Key Signal |
|---------|------|--------|------------|
| YieldBlox | $10.97M | Oracle pumped collateral USTRY 100x on Stellar DEX; oracle reported fake price | Sudden collateral price deviation >50x from moving average |
| Mango | $117M | Oracle + infinite mint: attacker pumped price of MNGO, took $117M loans against inflated collateral | Large MNGO buy order in thin order book; loan-to-value spike |
| Aave (March 2026) | $27.78M | Misconfigured oracle cap triggered healthy liquidations | Config error, not exploit, but flagged by unusual liquidation cluster |

**Aegis Screening Signals:**
- Collateral price deviation >20x from 24h moving average
- Unusual trading volume in thin order books
- Rapid minting of stablecoins against newly-pumped collateral
- Single transaction with large stablecoin mint + immediate DEX dump

---

### 3. Flash Loan / Governance Attack

**What it is:** Attacker takes a massive flash loan, manipulates markets or governance, repays loan.

| Exploit | Loss | Vector | Key Signal |
|---------|------|--------|------------|
| Beethoven X (2022) | $1.5M | Flash loan + fee-on-transfer inflation attack | Unusual `transferFrom` with fee-on-transfer token; contract not flagged for fee |
| Several DeFi protocol attacks | Variable | Flash loan + price manipulation for LP drain | Single tx with multiple DEX interactions, same-address source/destination |

**Aegis Screening Signals:**
- Single transaction interacting with >3 DEX pools
- LP token mint/burn in same transaction as price-affecting trade
- Governance proposal execution + immediate token transfer in same block

---

### 4. Private Key Compromise

**What it is:** Attacker gains access to admin/owner private keys.

| Exploit | Loss | Vector | Key Signal |
|---------|------|--------|------------|
| Ronin (key mechanism) | $624M | Phished Sky Mavis validators via social eng + fake job offers | Validator external activity (LinkedIn, Discord); unusual RPC access patterns |
| IoTeX | $4.4M | Compromised admin key on ioTube bridge; no 2FA/hardware key | Admin key as sole signer on bridge contracts; no timelock |
| Resolv Labs | $25M | Private key compromise; no mint cap on USR token | 80M tokens minted in single tx; no oracle check; automated liquidity kept feeding broken markets |

**Aegis Screening Signals:**
- Admin key signing from unusual IP/geo
- Contract upgrade or parameter change from EOA (not multisig)
- Large token mint from non-contract address
- Bridge admin functions called without timelock delay

---

### 5. Logic Bug / Reentrancy

**What it is:** Smart contract logic flaw enabling unexpected state transitions.

| Exploit | Loss | Vector | Key Signal |
|---------|------|--------|------------|
| The Unfinished Proof (FoomCash) | $2.26M | Skipped CLI step left zk verifier broken from day 1; attacker read Veil Cash post-mortem | No audit; unaudited contract calling unverified ZK library |
| Default Settings (ZK exploit) | — | Setup ceremony not finished; default settings shipped | Trusted setup not verified; verification key not properly initialized |

**Aegis Screening Signals:**
- Contract with uninitialized verification keys
- ZK contracts deployed without completed trusted setup
- Reentrancy guard missing on `transfer`/`transferFrom` functions
- State changes after `selfdestruct` still being processed

---

### 6. Social Engineering / RPGF (Realized Profit Generating Function)

**What it is:** DPRK or attacker group builds long-term trust relationships before exploiting.

| Exploit | Loss | Vector | Key Signal |
|---------|------|--------|------------|
| Drift Protocol | $285M | DPRK hackers spent 6 months befriending team via conferences, trust; deposited $1M; drained | New team members with unusual backgrounds; extended onboarding with minimal KYC; large initial deposits followed by sudden withdrawal |

**Aegis Screening Signals:**
- Multi-month social relationship before exploit (hard to detect on-chain)
- Large initial deposit from new address → immediate withdrawal after trust established
- Token buy + LP provision + subsequent drain pattern

---

### 7. Sandwich Attack / MEV

**What it is:** Attacker front-runs victim transaction for profit (not technically "exploit" but adversarial).

**Aegis Role:** Not an exploit — not flaggable. But Aegis should note if a "victim" address is repeatedly sandwiched (potential ongoing targeting).

---

## Pattern Clusters by Protocol Type

### Bridges
- Low validator/guardian count
- Whitelist entries never revoked after use
- Privileged contracts callable from cross-chain relay
- No timelock on admin functions
- Missing bounds checks on proof verification

### Lending
- Oracle price deviation >20x
- Single collateral type dominating borrow usage
- Large mint + immediate DEX exit in same tx
- Lack of supply caps
- Liquidation threshold misconfiguration

### DEXs
- Thin order book + large order = price impact
- LP token mint/burn in same tx as price-affecting trade
- Fee-on-transfer tokens not handled
- Impermanent loss not monitored

### Governance
- Flash loan + governance vote in same block
- Proposal + execution in same block
- Quorum achieved with unusual token distribution

---

## Detection Strategy

### Tier 1 (Rule-Based — <10ms)

| Rule | Threshold | Action |
|------|-----------|--------|
| Bridge validator count | <8 for TVL >$50M | WATCH |
| Collateral price deviation | >20x 24h MA | ESCALATE |
| Single tx mint + DEX exit | Stablecoin mint >$1M | ESCALATE |
| Admin key as sole bridge signer | Any | WATCH |
| Large LP burn in same tx as price-affecting trade | >$100k | WATCH |

### Tier 2 (Statistical — <50ms)

| Model | Features | Target |
|-------|---------|--------|
| IsolationForest | tx features + profile + historical behavior | Anomaly score >0.8 → ESCALATE |
| Pattern matcher | Known exploit TXN graph similarity | Cosine sim >0.7 → ESCALATE |

### Tier 3 (LLM — <2s)

| Task | Input | Output |
|------|-------|--------|
| Explain anomaly | Tx + profiles + context | Natural language flag rationale |
| Novel pattern detection | Anomalous but not rule-matched | WATCH/ESCALATE with confidence |

---

## Exploit Database Schema

For backtesting, each exploit should be cataloged as:

```json
{
  "exploit_id": "ronin-2022",
  "date": "2022-03-23",
  "loss_usd": 624000000,
  "protocol": "Ronin Network",
  "chain": "Ethereum L2",
  "attack_vector": "bridge_validator_compromise",
  "attack_subtype": "whitelist_not_revoked",
  "transactions": ["0xc28fad5e...", "0xed2c72ef..."],
  "attacker_addresses": ["0x098b716b..."],
  "signal_windows": {
    "pre_exploit_hours": 168,
    "detection_indicators": ["validator_set_unchanged_6mo", "unused_whitelist_entry"]
  },
  "was_detectable": true,
  "detection_method": "validator_set_analysis",
  "false_positives_in_sample": 0
}
```

---

## Open Questions

1. **Attribution:** How to handle DPRK-linked exploits? Should they be weighted differently in training?
2. **Novel attacks:** Tier 3 LLM for zero-day detection — what context window is needed?
3. **Legal constraints:** Some of these exploits (Ronin, Drift) involved DPRK actors — does Aegis have any regulatory obligations to flag these addresses?
4. **Cross-chain signal correlation:** Attacker moved funds across chains — does Aegis track multi-chain topology?

---

## Data Sources

- rekt.news — exploit narratives, loss amounts, attack vectors
- Etherscan — transaction traces, contract source
- Dune Analytics — on-chain behavior patterns
- Chainalysis — attacker address clustering (if accessible)
- SlowMist — technical post-mortems

## Next Steps

1. Build exploit database (50+ exploits) with TXN hashes + addresses
2. Run backtest: do the Tier 1 rules detect known exploits with ≥90% recall?
3. Profile the false positive rate on normal DeFi activity
4. Build Tier 2 IsolationForest on tx graph features
5. Integrate with intent mapping (#7) — contract classification + exploit pattern matching
