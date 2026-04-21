# Aegis Screening Rules — Nefarious Transaction Patterns

**Living document** — agents contribute rules here  
**Version:** 0.1  
**Date:** 2026-04-21  
**Status:** Active — growing list  

---

## How to Contribute a Rule

Add a new entry in the format below. Each rule should be:
- **Specific** — enough to trigger on real transactions
- **Testable** — can be validated against historical exploit data
- **Actionable** — the guardian can do something with this

---

## Rule Format

```yaml
rule_id: AEG-XXX
title: "<short name>"
category: "<attack-category>"
severity: critical|high|medium|low
description: "<what this detects>"
detection_logic:
  - condition: "<condition>"
    field: "<tx field>"
    threshold: "<value or comparison>"
    notes: "<optional>"
signals:
  - "<signal name>": "<description>"
related_exploits:
  - "<exploit name or tx hash>"
known_false_positives:
  - "<scenario>": "<why it triggers>"
references:
  - "<link or source>"
```

---

## Rules

### AEG-001
```yaml
title: "Bridge validator threshold below minimum"
category: "bridge-exploit"
severity: critical
description: "Bridge contract has guardian/validator count below minimum threshold for TVL"
detection_logic:
  - condition: "guardian_count < 5"
    field: "bridge.validator_count"
    threshold: "5"
    notes: "For bridges with TVL > $50M"
signals:
  - "low_guardian_count": "Validator set smaller than recommended minimum"
  - "unchanged_validators_months": "Validator set unchanged for >6 months"
related_exploits:
  - "Ronin bridge exploit (2022) — $624M"
  - "Wormhole (2022) — $326M"
known_false_positives:
  - "Testnet bridges": "May legitimately have few validators"
  - "New bridges < 30 days": "May be building validator set"
references:
  - "https://rekt.news/ronin-bridge/"
```

### AEG-002
```yaml
title: "Zero-value deposit claimed as non-zero"
category: "bridge-exploit"
severity: critical
description: "User claims to have deposited ETH/ERC20 to bridge but deposit value recorded as 0"
detection_logic:
  - condition: "deposit_value == 0 AND bridge.credit_recorded > 0"
    field: "bridge.deposit_event.value"
    threshold: "0 == true AND credit_recorded > 0"
    notes: "Attacker claims deposit but actual value transferred was 0"
signals:
  - "zero_value_deposit": "Deposit event with zero value but credit issued"
  - "mismatch_deposit_credit": "Deposit amount != credited amount"
related_exploits:
  - "Qubit Bridge (2022) — $80M"
known_false_positives:
  - "Token rounding": "Very small tokens with decimals may round to 0"
references:
  - "https://rekt.news/qubit-bridge/"
```

### AEG-003
```yaml
title: "Single guardian signature sufficient for large transfer"
category: "bridge-exploit"
severity: critical
description: "Bridge allows large value transfer with only 1 signature when it should require quorum"
detection_logic:
  - condition: "signature_count == 1 AND transfer_value > threshold"
    field: "bridge.tx.signatures.length"
    threshold: "$1M USD equivalent"
    notes: "Single-sig txs should be disabled for large transfers"
signals:
  - "single_sig_large_transfer": "One signature used for large bridge transfer"
related_exploits:
  - "Wormhole (2022) — $326M — attacker forged signature"
known_false_positives:
  - "Testnet transactions": "Low value testnet txs may legitimately be 1-sig"
references:
  - "https://rekt.news/wormhole/"
```

### AEG-004
```yaml
title: "Cross-chain relay calling privileged storage"
category: "bridge-exploit"
severity: high
description: "Cross-chain manager proxy calling storage contracts directly without owner guard"
detection_logic:
  - condition: "cross_chain_manager.proxy == true AND call.to in privileged_contracts AND call.data.method not in allowed_methods"
    field: "tx.to, tx.data"
    threshold: "privileged_contracts includes EthCrossChainData"
    notes: "Poly Network exploit pattern — untrusted cross-chain relay could modify storage"
signals:
  - "proxy_call_to_storage": "Proxy contract calling storage/owner contract"
  - "unrestricted_cross_chain": "Cross-chain relay callable without governance"
related_exploits:
  - "Poly Network (2021) — $611M"
known_false_positives:
  - "Timelock transactions": "Governance-proposed changes through timelock"
references:
  - "https://rekt.news/poly-network/"
```

### AEG-005
```yaml
title: "Oracle price deviation > 50x from moving average"
category: "oracle-manipulation"
severity: high
description: "Reported asset price deviates >50x from 24hr moving average — signals manipulation"
detection_logic:
  - condition: "ABS(current_price - ma_24hr) / ma_24hr > 50"
    field: "oracle.price"
    threshold: "50x deviation"
    notes: "Sudden extreme price deviation indicates oracle manipulation"
signals:
  - "extreme_price_deviation": "Price 50x+ from normal range"
  - "volume_spike": "Trading volume spike coinciding with deviation"
related_exploits:
  - "YieldBlox — $10.97M — oracle pumped collateral 100x"
  - "Mango Markets — $117M — oracle manipulation"
known_false_positives:
  - "Flash crashes": "Legitimate rapid price drops (but usually not 50x)"
references:
  - "https://rekt.news/yieldblox/"
```

### AEG-006
```yaml
title: "Same-block mint + DEX swap"
category: "token-exploit"
severity: high
description: "Attacker mints tokens and immediately swaps on DEX before anyone can react"
detection_logic:
  - condition: "mint_event.block == dex_swap_event.block AND mint_value > threshold"
    field: "tx.block_number, mint_event.value"
    threshold: "$100k equivalent"
    notes: "Detection is same-block correlation of mint events + DEX swaps"
signals:
  - "same_block_mint_swap": "Mint and DEX swap in same block"
  - "first_swap_from_new_mint": "First-ever DEX interaction is a large swap"
related_exploits:
  - "Unknown — typical flash loan + mint pattern"
known_false_positives:
  - "Initial liquidity events": "New tokens being bootstrapped on DEX"
references:
  - "EVM event log analysis: Mint, Transfer, Approval events"
```

### AEG-007
```yaml
title: "Function signature collision — dangerous method called"
category: "access-control"
severity: critical
description: "Contract called with method selector matching dangerous operation but with unexpected params"
detection_logic:
  - condition: "method_selector in dangerous_selectors AND params_unexpected"
    field: "tx.data[:4] (selector), tx.data[4:]"
    threshold: "selector matches: 0x<dangerous>"
    notes: "Monitors for calls to dangerous functions that should be guarded"
signals:
  - "dangerous_selector_call": "Call to dangerous/privileged function selector"
  - "parameter_mismatch": "Parameters don't match expected format for function"
related_exploits:
  - "Generic reentrancy exploits"
  - "Storage collision attacks"
known_false_positives:
  - "Multi-sig transactions": "Legitimate multi-sig may call dangerous functions"
references:
  - "EVM opcodes: CALL, DELEGATECALL, CREATE2 collision space"
```

### AEG-008
```yaml
title: "Unusual gas price for contract type"
category: "transaction-analysis"
severity: medium
description: "Gas price significantly higher or lower than normal for this contract type — possible manipulation"
detection_logic:
  - condition: "ABS(gas_price - median_gas_price_contract_type) / median > 10"
    field: "tx.gas_price"
    threshold: "10x deviation from contract type median"
    notes: "Build per-contract gas price distribution, flag outliers"
signals:
  - "gas_price_outlier": "Gas price 10x+ from normal for contract type"
  - "first_interaction_high_gas": "First interaction with contract uses unusually high gas"
related_exploits:
  - "EVM transaction ordering attacks"
known_false_positives:
  - "Congestion events": "Network congestion causes legitimate gas spikes"
references:
  - "Etherscan gas tracker, Dune analytics"
```

### AEG-009
```yaml
title: "Contract with no proxy upgrade pattern has admin key"
category: "access-control"
severity: medium
description: "Non-upgradeable contract still has a single EOA admin key — no timelock, no multisig"
detection_logic:
  - condition: "is_proxy == false AND has_admin_key == true AND admin_key is EOA"
    field: "contract.is_upgradeable, contract.admin_key.type"
    threshold: "admin is EOA (not multisig, not governance)"
    notes: "Single EOA admin = ruggable at any time"
signals:
  - "single_eoa_admin": "Contract has single EOA admin with no timelock"
  - "no_timelock": "No timelock delay on admin actions"
related_exploits:
  - "Numerous rug pulls — typical DeFi exploit pattern"
known_false_positives:
  - "Personal wallets": "Contracts designed for single-owner use (art NFTs, etc.)"
references:
  - "Contract bytecode analysis: delegation pattern detection"
```

### AEG-010
```yaml
title: "Unusual method call frequency on dormant contract"
category: "transaction-analysis"
severity: medium
description: "Contract inactive for months suddenly receives method calls — possible exploit prep"
detection_logic:
  - condition: "contract.dormant_months > 3 AND call_frequency_now > 10x_baseline"
    field: "contract.last_active, tx.frequency"
    threshold: "Dormant 3+ months, sudden spike in activity"
    notes: "Often preludes exploit as attacker tests or prepares infrastructure"
signals:
  - "dormant_contract_active": "Quiet contract suddenly receiving activity"
  - "increasing_call_frequency": "Call frequency trending up over recent blocks"
related_exploits:
  - "Multiple slow-prep exploits"
known_false_positives:
  - "Contract migration": "Team migrating to new implementation"
  - "Rebranding events": "Previously-delisted token relisted"
references:
  - "On-chain activity analysis tools: Dune, Nansen"
```

---

## Categories

| Category | Code | Description |
|----------|------|-------------|
| Bridge Exploit | `bridge` | Cross-chain bridge vulnerabilities |
| Oracle Manipulation | `oracle` | Price feed manipulation |
| Access Control | `access` | Privilege escalation, auth bypass |
| Token Exploit | `token` | Minting, burning, transfer issues |
| Transaction Analysis | `tx-analysis` | Behavioral anomalies |
| Reentrancy | `reentrancy` | Reentrant call patterns |
| Front-running | `frontrun` | MEV, sandwich attacks |

---

## Priority Levels

| Priority | Severity | Guardian Action |
|----------|----------|----------------|
| P1 | Critical | Reject tx immediately |
| P2 | High | Flag for WATCH, may escalate |
| P3 | Medium | Log and monitor |
| P4 | Low | Note only |

---

## Next Rules to Add

- [ ] Reentrancy pattern detection (check no reentrant calls in same tx)
- [ ] Unverified source code submission
- [ ] Liquidity removal immediately after deposit (same transaction)
- [ ] Flash loan: borrow > 50% of pool liquidity in single tx
- [ ] Unusual contract deployment activity from known exploiterEOA
- [ ] Rapid governance parameter changes (no timelock)

---

*Add new rules above. Format: rule_id = AEG-{3-digit sequence}. Update version number when adding rules.*
