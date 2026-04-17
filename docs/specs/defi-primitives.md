# Chain-Native DeFi Primitives

**Status:** Draft (tracks [#15](https://github.com/jon-tompkins/aegis-public/issues/15))
**Phase:** 0 — design
**Related:** [`staking-systems.md`](./staking-systems.md) §Chain-Native DeFi Primitives, [`economics.md`](./economics.md) §Revenue sources, [`memory-strategy.md`](./memory-strategy.md)
**Reference:** Berachain (Proof-of-Liquidity), Jonto's *DeFi in a Box* (2024-06-21)

---

## Purpose

Aegis embeds core DeFi primitives at the chain level so fees accrue to the validator pool by construction, not by policy. Validators are paid to screen every tx; this spec defines the non-gas revenue surfaces that make the economics work at low chain usage.

Scope of this doc: **AMM + pool lending** for v1. Bridging is covered in a separate spec (gated by cross-chain security review); governance gauges land in v2.

## Guiding principles

1. **Chain owns the primitives.** Contracts are OP Stack predeploys, deployed at genesis with deterministic addresses. TVL cannot migrate away by forking — the chain IS the protocol.
2. **Agents monitor, don't trade.** Validator agents watch protocol invariants (TVL, utilization, health factor) and act only on threshold breach. No discretionary market-making.
3. **Fee flow is structural, not a kickback.** Protocol fees route to the validator pool at the contract level. Governance tunes splits; it does not authorize transfers.
4. **Fork proven code, don't reinvent.** Aegis is not a DeFi chain marketing DeFi — it's a screening chain that happens to embed DeFi to sustain validator income. Use battle-tested forks.

---

## v1 primitive selection

| Primitive | v1 choice | Why | Rejected alternatives |
|---|---|---|---|
| AMM | **Uniswap v3 fork** (concentrated-liquidity) | Most battle-tested concentrated-liquidity AMM. Composability is high: existing aggregators, router integrations, price-oracle consumers work out of the box. | *Solidly / ve(3,3)*: gauge voting is governance-heavy and couples AMM to tokenomics — out of scope for v1. *Balancer-style weighted*: more complex, less liquidity per dollar of capital. *Curve*: optimized for stable pairs only. |
| Pool lending | **Aave v3 fork** | Isolation mode, e-mode, siloed risk per asset. Most mature risk parameter framework. Portal concept already matches the chain-native thesis. | *Compound v3 (Comet)*: single-borrow-asset-per-market is clean but inflexible. *Morpho*: great UX but relies on an underlying pool (Aave/Compound) — circular dependency on a chain that has none yet. |
| Bridging | **Deferred** — separate spec | Bridge security is a single-point-of-failure class on its own. Covered in `bridging.md` (TBD). For v1, canonical messaging goes through OP Stack's native L1↔L2 bridge. | — |
| Governance / gauges | **v2** | v1 tuning is council-controlled (see [`economics.md`](./economics.md) §Council). Gauges + vote-escrow land when validator set is large enough to matter. | — |

### Contract lineage

Each primitive is a **hard fork** with a small set of minimal modifications:

- **AegisAMM** — fork of Uniswap v3-core and v3-periphery at a pinned commit. Modifications limited to (a) fee-routing hook, (b) predeploy genesis state, (c) a `ValidatorPool` address constant.
- **AegisLend** — fork of Aave v3 at a pinned commit. Modifications limited to (a) reserve-factor recipient = ValidatorPool, (b) `ACL_ADMIN` bound to a governance timelock, (c) e-mode categories pre-seeded for ETH-correlated assets.

No custom math. No novel invariants. Any divergence from upstream is a change the chain has to maintain forever — keep it minimal.

---

## Fee routing

All protocol-level fees flow to `ValidatorPool`, a single on-chain account that redistributes to validators per the formula in [`economics.md`](./economics.md) §Numeric model.

### AMM fee flow (Uniswap v3 model)

```
Swap → LP fee (tier-dependent) → 80% pool LPs, 20% ValidatorPool
                                       │
                                       └── `IUniswapV3PoolActions.collectProtocol`
                                           routed to ValidatorPool, not factory owner
```

| Fee tier | LP share | Validator share | Use case |
|---|---|---|---|
| 0.01% | 80% | 20% | Stable pairs |
| 0.05% | 80% | 20% | Correlated pairs (ETH/stETH) |
| 0.30% | 80% | 20% | Standard volatile pairs |
| 1.00% | 80% | 20% | Exotic / long-tail |

**Mechanism:** Uniswap v3 already supports a protocol fee (`feeProtocol`, 4-bit per token, 0–10% of LP fee). Aegis's fork extends this to 20% (2-bit encoding changed to allow 0–25%) and pins the recipient to `ValidatorPool` at the factory level — it is not a mutable owner field.

### Lending fee flow (Aave v3 model)

```
Borrower interest → (1 - ReserveFactor) to suppliers
                    ReserveFactor         to ValidatorPool
```

| Asset tier | Reserve factor | Notes |
|---|---|---|
| Blue-chip (ETH, stETH, WBTC) | 10% | Low vol, tight spread |
| Stables (USDC, USDT, DAI) | 15% | High utilization expected |
| Correlated LSTs | 15% | E-mode enabled |
| Long-tail | 25% | Higher risk, higher reserve |

**Mechanism:** Aave v3's `ReserveConfiguration.reserveFactor` is the lever. Aegis hardcodes `treasury` (the reserve-factor recipient) to `ValidatorPool` at the `PoolConfigurator` level; the admin cannot redirect it.

### What happens if an LP routes around the fee

They can't. Aegis's AMM is the chain-native one; forks of it on the same chain would share the same predeploy factory (you can't redeploy a predeploy). Forks on *other chains* route value off-chain and are out of Aegis's scope — the chain's value proposition is screening + fee capture for L2-native flow.

---

## Agent thresholds

Validator agents run a `protocol_watchdog` loop per primitive. Intervention is **parametric, not discretionary** — agents vote on param updates the way Aave's Risk DAO does, not on trades.

### AMM watchdog (AegisAMM)

| Signal | Threshold (v1 default) | Action on breach | Cadence |
|---|---|---|---|
| Total TVL per pool | < 5% of 7-day EMA | File teacup; flag for council review | Per block |
| Swap volume impulse | > 10× 1-hour EMA | File teacup; no auto-action | Per block |
| Price oracle deviation (if external) | > 2% vs TWAP | File teacup; Guardian may flag | Per block |
| Pool drained (`liquidity == 0`) | Instantaneous | File P0 teacup; council pager | Per block |

Agents do **not**:
- Add or remove liquidity on behalf of the chain
- Rebalance positions
- Execute arbitrage

Agents **do**:
- Vote (once per epoch) on protocol-fee tier adjustments
- File teacups on anomalies, which feed the training pipeline (`memory-strategy.md`)
- Post UMA-style bonded assertions ([`economics.md`](./economics.md) §Council) for sustained anomalies

### Lending watchdog (AegisLend)

| Signal | Threshold (v1 default) | Action on breach | Cadence |
|---|---|---|---|
| Asset utilization | > 95% for > 1h | File teacup; propose rate-curve kink adjustment next epoch | 1 min |
| Pool health factor (aggregate) | < 1.1 | File P1 teacup; council review | Per block |
| Position health factor | < 1.0 | Liquidation eligible (standard Aave mechanism) | Per block |
| Oracle price stale | > 15 min since last update | Pause borrows for that asset (existing Aave mechanism, agent-triggered) | 1 min |
| Reserve factor accrual | < 50% of projected 7-day | File teacup; investigate fee routing | Hourly |

**Liquidation mechanics** stay Aave-native: any address can call `liquidationCall`, liquidator receives collateral + bonus. Agents do not have privileged liquidator status — this avoids the "validator as MEV extractor" anti-pattern.

### Per-asset risk parameters (v1 seeds)

Seeded at genesis; adjustable via governance timelock.

| Asset | LTV | Liq. threshold | Liq. bonus | Reserve factor | E-mode |
|---|---|---|---|---|---|
| ETH | 80% | 82.5% | 5% | 10% | ETH-correlated |
| stETH / wstETH | 75% | 78% | 6% | 10% | ETH-correlated |
| WBTC | 70% | 75% | 7% | 10% | — |
| USDC | 77% | 80% | 4.5% | 15% | stablecoin |
| USDT | 74% | 76% | 4.5% | 15% | stablecoin |
| DAI | 75% | 77% | 5% | 15% | stablecoin |

Values mirror Aave v3 mainnet conservative tier as of 2026-04; tune post-launch based on observed realized vol.

---

## Ownership & upgrade path

```
Predeploy genesis address (immutable)
          │
          └── points to Proxy (immutable)
                    │
                    └── Implementation (upgradable via)
                              │
                              └── GovernanceTimelock (48h delay)
                                        │
                                        └── Council multisig (5-of-7, term-limited)
```

- **Implementations** are upgradable through the timelock — bug fixes and parameter hot-fixes ship this way.
- **Fee recipient (`ValidatorPool`)** is a genesis constant in the implementation storage layout. Upgrading the implementation cannot change it without council quorum + 48h timelock visibility.
- **Risk parameters** (LTV, liq. threshold, reserve factor) are governable via the same timelock. Council publishes rationale per change.
- **Freeze path:** any council member + 2 others can trigger a 24h freeze on a primitive (pause new deposits/borrows) without full quorum. Designed for suspected exploit response — see [`guardian.md`](./guardian.md).

### TVL migration resistance

Aegis contracts are OP Stack predeploys at deterministic addresses. A fork of the chain inherits the same addresses and therefore the same fee routing — there is no way to run "AegisAMM without the validator fee" and still be on Aegis. Running elsewhere is allowed but out-of-network; the fee-capture premise rests on L2-native flow preferring the chain's canonical primitives.

---

## Berachain reference

Berachain's Proof-of-Liquidity (PoL) is the nearest live analogue: the chain deploys BEX (Balancer-style AMM), Bend (Compound-fork lending), and Honey (CDP stable), and validator rewards are tied to LP activity on those primitives via bribes and BGT emissions.

**What Aegis takes:**
- Chain-deploys-primitives thesis
- Fees route to validators structurally (not via separate rewards contract)
- Protocol-manager framing for validator agents

**What Aegis doesn't take:**
- **BGT / vote-escrow governance coupling.** PoL ties validator rewards to LP-gauge voting, which creates a gauge-mafia dynamic. Aegis keeps validator rewards tied to screening work + structural fees; gauge systems are v2.
- **CDP stable at v1.** Honey adds a whole risk surface (peg management, PSM). Deferred.
- **Tri-token model (BERA/BGT/HONEY).** Aegis has one token (AEGIS) with stake+governance utility only.

---

## Acceptance criteria

- [x] v1 primitive contract choices named and justified (Uniswap v3 fork, Aave v3 fork)
- [x] Fee-routing mechanism specified at contract-hook level (protocol fee bps, reserve factor recipient)
- [x] Fee splits aligned with `economics.md` (AMM: 80/20 LP/Validator, lending: reserve-factor-to-ValidatorPool)
- [x] Agent threshold tables (AMM + lending) with signals, defaults, actions, cadence
- [x] Liquidation model (Aave-native, agents non-privileged)
- [x] Per-asset risk seed table
- [x] Ownership / upgrade path with timelock + freeze
- [x] Berachain reference section with explicit take / don't-take
- [ ] Test vectors: fee accrual over 1000 simulated swaps (blocked on ValidatorPool contract stub)
- [ ] Bridging spec (`docs/specs/bridging.md`) — separate issue
- [ ] Gauge / ve-model design — v2

---

## Open questions (for Bob / Jonto)

1. **Fee split numbers.** 80/20 AMM, 10–25% reserve factor lending — are these the right opening values, or should v1 launch more conservatively (say 90/10 AMM) and ratchet up? Impacts LP depth vs validator income tradeoff.
2. **Router / aggregator integration.** Uniswap v3 has a standard Router02. Do we ship an Aegis-branded router (brand, UX) or rely on third-party aggregators (Li.Fi, 1inch, KyberSwap) to integrate the chain? v1 recommendation: ship the upstream router unchanged, let aggregators find us.
3. **Oracle dependency.** Aave v3 requires a price oracle per asset. Chainlink on an L2 costs real money per update. Cheap paths: TWAP from AegisAMM pools (bootstrapping problem — needs TVL first), Pyth pull-oracle (attestation-per-read, cheaper), or a validator-agent-attested oracle (aligns with the chain's ethos but is a new primitive). Recommend starting with Chainlink for blue chips + Pyth for long-tail, revisiting once agent-attested oracle is proven.
4. **LP rewards beyond fees.** Berachain adds BGT emissions on top of LP fees. Aegis's 20% protocol take reduces LP APR relative to vanilla Uniswap v3 on the same volume. Do we need an LP-subsidy program in year one to bootstrap depth, or does the captive flow (L2-native screened tx) provide enough organic volume?
5. **CDP stable.** Out of scope for this spec. Call on whether a chain-native stable is a separate spec (`stable.md`) or not pursued at all.
