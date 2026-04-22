# DeFi Implementation — Task Breakdown by Primitive

**Parent issue:** #30  
**Status:** Task list for Clark  
**Last updated:** 2026-04-22  

---

## How to Work This

Each primitive gets its own issue. Work the checklist inside each issue. Flag human decisions in #29 (Human Questions).

---

## Issue #31 — AMM (Velodrome V2 Fork)

**Spec:** `docs/specs/defi-implementation-sources.md`  
**Labels:** `aegis`, `tenet/backlog`, `open-contribution`, `area:code`

### Checklist

- [ ] **Clone velodrome-v2 to aegis-public**
  - `git clone https://github.com/velodrome-finance/velodrome-v2`
  - Push to `aegis-public/velodrome-v2`

- [ ] **Run upstream test suite — confirm passing**
  - `forge install` then `forge test`
  - Note any failures before modifications

- [ ] **Apply Aegis modifications**
  - [ ] Replace GRO token → AEGIS (rename + new contract)
  - [ ] Replace FeeDistributor routing → Aegis validator pool
  - [ ] Update VotingEscrow to accept AEGIS staking
  - [ ] Strip or modify team/emission vestings (not needed for Aegis)
  - [ ] Update GaugeController to route emissions to validator-controlled gauges

- [ ] **Run tests after modifications**
  - All tests pass post-modification
  - Note failures and fix

- [ ] **Deploy to testnet (Aegis OP Stack or local devnet)**
  - `forge script deploy` or equivalent

- [ ] **Validate: create a volatile pair + stableswap pool**
  - Test swap, add liquidity, verify fee accrual

- [ ] **Validate: cross-primitive integration**
  - GHO can be swapped on Aegis Velodrome deployment

---

## Issue #32 — Lending (Aave V3 Fork)

**Spec:** `docs/specs/defi-implementation-sources.md`  
**Labels:** `aegis`, `tenet/backlog`, `open-contribution`, `area:code`

### Checklist

- [ ] **Clone aave-v3-core to aegis-public**
  - `git clone https://github.com/aave/aave-v3-core`
  - Push to `aegis-public/aave-v3-core`

- [ ] **Run upstream test suite — confirm passing**
  - Hardhat test suite
  - Note any pre-existing failures

- [ ] **Apply Aegis modifications**
  - [ ] Remove STKAAVE governance integration
  - [ ] Replace PoolConfigurator admin → Aegis validators (risk agents)
  - [ ] Strip or replace AAVE token from interest rate model calculations
  - [ ] Update fee routing → validator pool
  - [ ] Update PoolAddressesProvider with Aegis-specific contract registry

- [ ] **Run tests after modifications**
  - All tests pass post-modification

- [ ] **Deploy to testnet**
  - Hardhat deployment scripts

- [ ] **Validate: supply + borrow flow**
  - Supplier deposits ETH, borrows a second asset
  - Verify interest accrual, health factor, liquidation

- [ ] **Validate: cross-primitive integration**
  - Deposited collateral can be used to mint GHO via CDP

---

## Issue #33 — CDP Stablecoin (GHO Fork)

**Spec:** `docs/specs/defi-implementation-sources.md`  
**Labels:** `aegis`, `tenet/backlog`, `open-contribution`, `area:code`

### Checklist

- [ ] **Clone GHO-token to aegis-public**
  - `git clone https://github.com/aave/GHO-token`
  - Push to `aegis-public/gho-token`

- [ ] **Run upstream test suite — confirm passing**
  - Note any pre-existing failures

- [ ] **Apply Aegis modifications**
  - [ ] Replace Aave governance → Aegis validators
  - [ ] Replace GhoOracle → Aegis guardian price feeds
  - [ ] Update GhoAaveFacilitator bucket size control → risk management agents
  - [ ] Update facilitator fee routing → validator pool

- [ ] **Run tests after modifications**

- [ ] **Deploy to testnet**

- [ ] **Validate: mint GHO against Aave-supplied collateral**
  - Deposit collateral, mint GHO, verify 1:1 USD peg
  - Verify liquidation if collateral drops below threshold

- [ ] **Validate: cross-primitive integration**
  - GHO trades on Aegis Velodrome deployment
  - GHO used as borrow asset in Aegis Aave deployment

---

## Cross-Cutting Open Questions

| # | Question | Impact | Posts to |
|---|----------|--------|----------|
| 1 | Foundry vs Hardhat as deployment toolchain? | Affects all 3 | Post in #29 |
| 2 | Separate repos or monorepo for 3 primitives? | Repo structure | Post in #29 |
| 3 | Who approves parameter changes — multisig or agent thresholds? | Risk management design | Post in #29 |
| 4 | Vyper compiler setup for Velodrome? | AMM build pipeline | Post in #29 |

---

## Dependencies

```
#30 (parent) — tracks all 3 primitives

#31 (AMM) → done first
#32 (Lending) → depends on #31 (GHO needs Aave collateral)
#33 (CDP/GHO) → depends on #31 + #32
```

All three should be deployable independently initially, but cross-primitive validation needs all three deployed.

---

## Reference

- Velodrome V2: https://github.com/velodrome-finance/velodrome-v2
- Aave V3 Core: https://github.com/aave/aave-v3-core
- GHO Token: https://github.com/aave/GHO-token
