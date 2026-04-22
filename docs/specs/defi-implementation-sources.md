# DeFi Implementation Sources — Aegis Chain

**Spec Version:** 0.1  
**Author:** Bob (research)  
**Date:** 2026-04-22  
**Status:** Research Complete — fork candidates identified  
**Drives:** Aegis Chain-native DeFi primitives, Phase 1b implementation  

---

## Overview

Aegis is EVM-compatible. For each DeFi primitive, we need open-source, battle-tested, audited contracts we can fork and deploy with minimal modification. This doc identifies the canonical sources.

---

## AMM — Solidly (Volatile + StableSwap)

### Recommended Fork

**Repository:** `velodrome-finance/velodrome-v2`  
**License:** MIT  
**Language:** Solidity  
**Source:** https://github.com/velodrome-finance/velodrome-v2  

### Why Velodrome V2

- Most actively maintained Solidly-family fork
- >$1B TVL on Optimism (battle-hardened under live conditions)
- Both volatile pairs AND stableSwap pools (what we need)
- MIT license — no commercial restrictions
- Implements the full Solidly V2 AMM: vote-locked emissions, gauge system,FeeDistributor

### What's Forkable

```
velodrome-v2/
├── contracts/
│   ├── Token.sol              # GRO token (our baseline governance)
│   ├── VotingEscrow.sol       # Vote-locked ve(TOKEN) — core of Curve/Solidly model
│   ├── GaugeController.sol    # Emission allocation by gauge weight
│   ├── FeeDistributor.sol     # Distributes protocol fees to ve(TOKEN) holders
│   ├── pools/
│   │   ├── base/
│   │   │   ├── StableSwap.vyper        # Stablecoin AMM (low slippage, peg maintenance)
│   │   │   └── VolatileSwap.vyper      # Volatile asset AMM
│   │   └── Factory.sol                  # Deploys new pools
│   └── Gauge.sol             # Per-pool gauge — distributes emissions
```

### What We Modify

- Replace GRO token with our own governance token (AEGIS)
- Update FeeDistributor to route fees to Aegis validator pool
- Gauge weights controlled by Aegis governance (not vote-locked speculative farming)
- Strip or modify the token-vesting/team-emission schedules

### Key Integration Points

- **Pool creation:** Any approved asset pair can deploy a new pool via Factory
- **LP tokens** go to liquidity providers; protocol collects trading fees
- **Gauge system** controls which pools get emission incentives — agents interact here
- **FeeDistributor** pulls trading fees from pools and distributes to ve(AEGIS) holders (validators)

### Audit Status

- Multiple rounds of audits
- Live since ~2022 on Optimism with no critical exploits
- Vyper compilation (note: requires vyper compiler)

---

## Lending — Aave V3

### Recommended Fork

**Repository:** `aave/aave-v3-core`  
**License:** Apache 2.0  
**Language:** Solidity  
**Source:** https://github.com/aave/aave-v3-core  

### Why Aave V3

- Industry standard for lending protocols
- Multiple full audit rounds (OpenZeppelin, Trail of Bits, SigmaPrime, ABDK, Certora)
- Deployed at scale (>$10B TVL across V2+V3)
- Upgradeable proxy pattern (long-term maintainability)
- Built-in isolation mode, credit delegation, risk parameters per asset

### What's Forkable

```
aave-v3-core/
├── contracts/
│   ├── protocol/
│   │   ├── PoolAddressesProvider.sol         # Central registry — all contract addresses
│   │   ├── Pool.sol                          # Main lending entry point
│   │   │   ├── supply()
│   │   │   ├── borrow()
│   │   │   ├── repay()
│   │   │   └── withdraw()
│   │   ├── PoolConfigurator.sol              # Admin control: add assets, set params
│   │   ├── protocols/
│   │   │   ├── logic/
│   │   │   │   ├── ValidationLogic.sol
│   │   │   │   └── GenericLogic.sol
│   │   │   └── token/
│   │   │       ├── AToken.sol                # Yield-bearing deposit token
│   │   │       ├── StableDebtToken.sol
│   │   │       └── VariableDebtToken.sol
│   │   └── libraries/
│   │       ├── LogicLibrary.sol
│   │       └── ReserveConfiguration.sol       # Asset params: LTV, liquidation threshold, etc.
│   └── helpers/
│       └── Mocks.sol                          # Test mocks
```

### What We Modify

- Strip AAVE/STKAAVE governance integration (not needed on Aegis)
- Replace governance token with AEGIS
- Update interest rate models (currently tied to Aave token economics)
- PoolConfigurator access controlled by Aegis validators (not multisig)
- Remove or modify isolation mode for assets not in Aegis's approved list

### Key Integration Points

- **Pool.sol** is the main entry — Aegis monitor agent calls `supply()` and `borrow()` via signed transactions
- **PoolConfigurator** is where risk management agents update parameters: `setLiquidationThreshold()`, `setLTV()`, `setReserveInterestRateStrategy()`
- **AToken** accrues yield automatically — no separate claim step
- **Credit delegation** allows a supplier to allow a borrower to draw against their credit line without moving funds

### Audit Status

Full multi-round audit by OpenZeppelin, Trail of Bits, SigmaPrime, ABDK, Certora. Reports in `/audits` folder.

---

## CDP Stablecoin — GHO

### Recommended Fork

**Repository:** `aave/GHO-token`  
**License:** Apache 2.0  
**Language:** Solidity  
**Source:** https://github.com/aave/GHO-token  

### Why GHO

- Aave's own CDP stablecoin, built on Aave V3
- Minted by supplying collateral through Aave pools
- Governed via Aave governance (we replace with Aegis governance)
- No external liquidity backing — overcollateralized via user-supplied assets
- Simple, auditable, production-deployed

### What's Forkable

```
GHO-token/
├── contracts/
│   ├── GhoToken.sol                # ERC20 stablecoin — mint/burn by authorized roles
│   ├── GhoOracle.sol                # Price oracle for GHO/USD (Chainlink or custom)
│   ├── GhoAaveFacilitator.sol       # Core CDP logic — borrow GHO against Aave collateral
│   └── interfaces/
│       ├── IGhoToken.sol
│       └── IGhoAaveFacilitator.sol
```

### What We Modify

- Replace Aave governance role with Aegis validators
- `GhoOracle` — use Aegis's own guardian price feeds (not Chainlink dependency)
- `GhoAaveFacilitator` — minting limits, collateral factors, liquidation bonuses set by Aegis risk agents
- Strip the Aave-specific discount mechanism (not needed for Aegis deployment)

### Key Integration Points

- **GhoAaveFacilitator** manages the debt ceiling and bucket size (max mintable GHO per epoch)
- Risk agents adjust `setBucketSize()` and `setFacilitatorFee()` on-chain via governance
- GHO minted by depositing collateral into the facilitator → receives GHO at 1:1 USD
- Liquidation: if collateral drops below liquidation threshold, GHO is auctioned off

### Audit Status

Deployed on Ethereum mainnet since ~2023. Smart contracts audited as part of Aave's overall audit process.

---

## Forking Strategy

### Principle: Fork Clean, Modify Deliberately

1. **Fork the repo as-is** — commit the full upstream source before modifying anything
2. **Make surgical changes** — only what's needed to adapt to Aegis (token name, governance, fee routing)
3. **Keep audit trails** — document what changed from upstream and why
4. **Run all tests** — upstream tests must pass before Aegis modifications

### Required Changes Per Primitive

| Primitive | Token Swap | Governance | Fee Routing | Interest Model |
|-----------|-----------|-------------|-------------|----------------|
| Velodrome V2 | GRO → AEGIS | Vote-locked → validator-staked | → validator pool | Unchanged |
| Aave V3 | Remove STKAAVE | Aave Gov → Aegis validators | → validator pool | Adjust to Aegis economics |
| GHO | Remove Aave Gov | Aave Gov → Aegis validators | → validator pool | Strip discount |

### What We Keep Identical

- Core math (AMM bonding curves, lending interest rate formulas, liquidation mechanics)
- Upgradeable proxy patterns
- Access control modifiers (only initial admin, then governance)
- Event signatures (important for indexing)

---

## Reference Links

| Primitive | Repo | License |
|-----------|------|---------|
| AMM (Velodrome V2) | https://github.com/velodrome-finance/velodrome-v2 | MIT |
| Lending (Aave V3) | https://github.com/aave/aave-v3-core | Apache 2.0 |
| CDP Stablecoin (GHO) | https://github.com/aave/GHO-token | Apache 2.0 |

---

## Next Steps

1. **Clone repos** — fork to Aegis GitHub org or import into local repo
2. **Audit the diffs** — what exactly changed vs upstream for each primitive
3. **Run full test suites** — confirm no breaking changes from upstream
4. **Add Aegis-specific modifications** — AEGIS token, validator governance, fee routing
5. **Deploy to testnet** — validate integration across all three primitives

---

*Version history: v0.1 — 2026-04-22 — Bob — initial fork research*
