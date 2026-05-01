# Chain-Native DeFi Primitives

**Status:** Draft v0.2 (tracks [#15](https://github.com/jon-tompkins/aegis-public/issues/15))
**Phase:** 0 — design
**Related:** [`staking-systems.md`](./staking-systems.md) §Chain-Native DeFi Primitives, [`economics.md`](./economics.md) §Revenue sources, [`memory-strategy.md`](./memory-strategy.md), `defi-implementation-sources.md` (downstream — needs sync to v3 fork target)
**Reference:** Berachain (Proof-of-Liquidity), Jonto's *DeFi in a Box* (2024-06-21)

---

## Purpose

Aegis embeds core DeFi primitives at the chain level so fees accrue structurally, not by policy. Validators are paid to screen every tx; this spec defines the non-gas revenue surfaces that make the economics work at low chain usage.

All protocol fees route to a single chain-native `FeeAccumulator` contract. Distribution from `FeeAccumulator` (validator share, LP rebates, gauge bribes, treasury, etc.) is governed by the token spec, owned separately by Jonto and not pinned in this document.

Scope of this doc: **AMM + pool lending + native stable (GHO fork)** for v1. Bridging is covered in a separate spec (gated by cross-chain security review). Gauge weights and emission policy are baseline-supported in the AMM choice (Velodrome lineage) but are tuned in the forthcoming token spec rather than here.

## Guiding principles

1. **Chain owns the primitives.** Contracts are OP Stack predeploys, deployed at genesis with deterministic addresses. TVL cannot migrate away by forking — the chain IS the protocol.
2. **Agents monitor, don't trade.** Validator agents watch protocol invariants (TVL, utilization, health factor) and act only on threshold breach. No discretionary market-making.
3. **Fee flow is structural, not a kickback.** Protocol fees route to the validator pool at the contract level. Governance tunes splits; it does not authorize transfers.
4. **Fork proven code, don't reinvent.** Aegis is not a DeFi chain marketing DeFi — it's a screening chain that happens to embed DeFi to sustain validator income. Use battle-tested forks.

---

## v1 primitive selection

| Primitive | v1 choice | Why | Rejected alternatives |
|---|---|---|---|
| AMM | **Velodrome v3 fork** (Solidly lineage: pooled stableswap + concentrated-liquidity volatile pools, ve(3,3) gauge layer) | Pooled stableswap captures stable→stable flow with minimal slippage — the dominant L2 swap pattern for screened tx. ve(3,3) gauge layer aligns naturally with the `FeeAccumulator` distribution model and the forthcoming token spec. Slipstream-style CL pools cover volatile pairs. Battle-hardened on Optimism (>$1B TVL). MIT-licensed. | *Uniswap v3 alone*: no native stableswap; we'd ship a separate Curve fork to cover stables. *Balancer weighted*: more complex, less liquidity per dollar. *Curve standalone*: stable-only, no volatile coverage. |
| Native stable | **GHO fork** (CDP stable, Aave-collateralized) | The chain-native stable IS the CDP. GHO is overcollateralized via AegisLend positions — no separate CDP primitive, no peg-management surface beyond what GHO already handles. Aave/Aegis lineage means the same risk framework covers both lending and stable mint. | *MakerDAO-style standalone CDP*: separate collateral system, separate risk model, doubles the surface for no benefit when GHO already exists. *Algorithmic stables*: rejected on first principles. |
| Pool lending | **Aave v3 fork** | Isolation mode, e-mode, siloed risk per asset. Most mature risk parameter framework. Portal concept already matches the chain-native thesis. Required base for the GHO fork. | *Compound v3 (Comet)*: single-borrow-asset-per-market is clean but inflexible. *Morpho*: great UX but relies on an underlying pool (Aave/Compound) — circular dependency on a chain that has none yet. |
| Bridging | **Deferred** — separate spec | Bridge security is a single-point-of-failure class on its own. Covered in `bridging.md` (TBD). For v1, canonical messaging goes through OP Stack's native L1↔L2 bridge. | — |
| Governance / gauges | **Baseline supported (Velodrome ve(3,3) layer); policy in token spec** | Gauge layer ships with the AMM fork. Emission weights, vote-locking, bribe routing, and validator participation are defined in the forthcoming token spec, not here. | — |

### Contract lineage

Each primitive is a **hard fork** with a small set of minimal modifications:

- **AegisAMM** — fork of Velodrome v3 (Solidly lineage: pooled stableswap + concentrated-liquidity volatile pools + ve(3,3) gauge layer) at a pinned commit. Modifications limited to (a) fee-routing hook → `FeeAccumulator`, (b) predeploy genesis state, (c) governance token wired to AEGIS rather than upstream's GRO. The gauge controller and FeeDistributor are retained but rebound to chain-native addresses.
- **AegisLend** — fork of Aave v3 at a pinned commit. Modifications limited to (a) reserve-factor recipient = `FeeAccumulator`, (b) `ACL_ADMIN` bound to a governance timelock, (c) e-mode categories pre-seeded for ETH-correlated assets, (d) a GHO facilitator slot reserved for the AegisStable fork.
- **AegisStable** — fork of [`aave/GHO-token`](https://github.com/aave/gho-core) at a pinned commit. Mint via AegisLend collateral positions (no separate CDP primitive). Modifications limited to (a) facilitator routing of carry/discount fees → `FeeAccumulator`, (b) governance role bound to the same timelock as AegisLend, (c) Aave-specific discount mechanism stripped or rebound.
- **FeeAccumulator** — chain-native predeploy. Single recipient for all protocol fees from AegisAMM, AegisLend, and AegisStable. Distribution policy (validator share, LP rebates, gauge bribes, treasury) is set by the token spec and applied via governance; `FeeAccumulator` is the structural choke point, not the policy.

No custom math on the primitives themselves. No novel AMM/lending/stable invariants. Any divergence from upstream is a change the chain has to maintain forever — keep it minimal. `FeeAccumulator` is the one new contract Aegis owns end-to-end.

---

## Fee routing

All protocol-level fees flow to a single chain-native predeploy: `FeeAccumulator`. Onward distribution (validator share, LP rebates, gauge bribes, treasury) is defined by the token spec — not by this document. `FeeAccumulator` exists so that the *capture* mechanism is structural and the *distribution* mechanism can evolve via governance without re-touching the primitives.

```
AegisAMM     ─┐
AegisLend    ─┼──► FeeAccumulator ──► distribution per token spec (TBD)
AegisStable  ─┘
```

### AMM fee flow (Velodrome v3 model)

```
Swap → LP fee + protocol fee
        │           │
        ▼           ▼
   Pool LPs    FeeAccumulator
              (via FeeDistributor → accumulator hook)
```

Velodrome v3 splits per-pool fees between LPs and a protocol-level FeeDistributor. Aegis rebinds the FeeDistributor recipient to `FeeAccumulator` at the factory level; it is not a mutable owner field. Per-tier protocol-fee bps are governance-tunable but routing is not.

| Pool type | Default protocol fee bps | Notes |
|---|---|---|
| Stableswap (Solidly stable) | TBD (token spec) | Dominant flow; conservative bps to preserve LP depth |
| CL volatile (Slipstream-style) | TBD (token spec) | Per-tier (0.05% / 0.30% / 1.00% pools) |

Specific bps numbers are deliberately deferred to the token spec since they trade off LP APR against the size of the `FeeAccumulator` inflow, which is a tokenomics decision, not a primitives decision.

### Lending fee flow (Aave v3 model)

```
Borrower interest → (1 - ReserveFactor) to suppliers
                    ReserveFactor         to FeeAccumulator
```

| Asset tier | Reserve factor | Notes |
|---|---|---|
| Blue-chip (ETH, stETH, WBTC) | 10% | Low vol, tight spread |
| Stables (USDC, USDT, DAI) | 15% | High utilization expected |
| Correlated LSTs | 15% | E-mode enabled |
| Long-tail | 25% | Higher risk, higher reserve |

**Mechanism:** Aave v3's `ReserveConfiguration.reserveFactor` is the lever. Aegis hardcodes `treasury` (the reserve-factor recipient) to `FeeAccumulator` at the `PoolConfigurator` level; the admin cannot redirect it.

### Native-stable (GHO fork) fee flow

```
GHO mint/borrow interest + facilitator carry → FeeAccumulator
```

GHO's facilitator pattern accrues a borrow-side rate that, in upstream Aave, routes to the Aave treasury. Aegis rebinds this to `FeeAccumulator`. Liquidation bonuses on AegisLend collateral backing GHO debt remain with liquidators (Aave-native), unchanged.

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
- **Fee recipient (`FeeAccumulator`)** is a genesis constant in the implementation storage layout of every primitive (AegisAMM, AegisLend, AegisStable). Upgrading an implementation cannot change it without council quorum + 48h timelock visibility. The `FeeAccumulator`'s onward distribution policy is governed by the token spec; fee *capture* is structural here.
- **Risk parameters** (LTV, liq. threshold, reserve factor) are governable via the same timelock. Council publishes rationale per change.
- **Freeze path:** any council member + 2 others can trigger a 24h freeze on a primitive (pause new deposits/borrows) without full quorum. Designed for suspected exploit response — see [`guardian.md`](./guardian.md).

### TVL migration resistance

Aegis contracts are OP Stack predeploys at deterministic addresses. A fork of the chain inherits the same addresses and therefore the same fee routing — there is no way to run "AegisAMM without the protocol fee" and still be on Aegis. Running elsewhere is allowed but out-of-network; the fee-capture premise rests on L2-native flow preferring the chain's canonical primitives.

---

## Berachain reference

Berachain's Proof-of-Liquidity (PoL) is the nearest live analogue: the chain deploys BEX (Balancer-style AMM), Bend (Compound-fork lending), and Honey (CDP stable), and validator rewards are tied to LP activity on those primitives via bribes and BGT emissions.

**What Aegis takes:**
- Chain-deploys-primitives thesis
- Fees route structurally through chain-native contracts (single `FeeAccumulator`), not via off-chain policy
- Protocol-manager framing for validator agents
- **CDP stable in v1.** Aegis ships a GHO fork as the chain-native stable, collateralized via AegisLend — no separate CDP primitive

**What Aegis doesn't take:**
- **BGT-style direct coupling of validator rewards to LP-gauge voting.** Aegis keeps validator income anchored to screening work first; the gauge layer (Velodrome ve(3,3) lineage) is shipped but how it interacts with `FeeAccumulator` distribution and validator pay is set by the token spec, not by mimicking PoL.
- **Tri-token model (BERA/BGT/HONEY).** Aegis has one governance token (AEGIS) plus the chain-native stable (GHO fork). Stake + governance utility lives on AEGIS; the stable is purely a debt instrument.

---

## Acceptance criteria

- [x] v1 primitive contract choices named and justified (Velodrome v3 fork, Aave v3 fork, GHO fork)
- [x] Fee-routing mechanism specified at contract-hook level (recipient = `FeeAccumulator` for AMM protocol fee, lending reserve factor, GHO facilitator carry)
- [x] `FeeAccumulator` introduced as the single chain-native fee sink; onward distribution explicitly deferred to the token spec
- [x] Agent threshold tables (AMM + lending) with signals, defaults, actions, cadence
- [x] Liquidation model (Aave-native, agents non-privileged)
- [x] Per-asset risk seed table
- [x] Ownership / upgrade path with timelock + freeze
- [x] Berachain reference section with explicit take / don't-take (updated for v1 CDP stable inclusion)
- [ ] Per-tier protocol-fee bps (AMM stableswap + CL pools) — blocked on token spec
- [ ] `FeeAccumulator` distribution policy (validator share, gauge bribes, treasury splits) — owned by token spec
- [ ] `FeeAccumulator` contract stub + test vectors: fee accrual over 1000 simulated swaps
- [ ] AegisStable (GHO fork) facilitator parameters: bucket size, carry rate — token spec input
- [ ] Bridging spec (`docs/specs/bridging.md`) — separate issue
- [ ] Oracle plan: Pyth integration design — post-v1, separate spec

---

## Open questions (for Bob / Jonto)

1. **Per-tier protocol-fee bps (AMM).** The AMM ships with stableswap + CL volatile pools; bps per tier are deferred to the token spec because they trade off LP APR against `FeeAccumulator` inflow. This spec records the routing; the numbers land with the token spec.
2. **Router / aggregator integration.** Velodrome v3 ships its own router. v1 recommendation: ship the upstream router unchanged, let third-party aggregators (Li.Fi, 1inch, KyberSwap) integrate the chain. Aegis-branded UX router can come post-v1.
3. **Velodrome v3 composition (TBD with Jonto).** "Velodrome v3" in this spec covers the Solidly stack: pooled stableswap pools, Slipstream-style CL pools for volatiles, and the ve(3,3) gauge + FeeDistributor layer. Confirm scope before fork-pin: do we take all three components, or stableswap + CL pools only with gauges deferred?
4. **`FeeAccumulator` distribution policy.** Owned by the forthcoming token spec. This spec only commits that *all* protocol fees route to `FeeAccumulator`; how it pays out (validator share, LP rebates, gauge bribes, treasury) is a token-spec concern. Validators need a credible commitment that *some* meaningful share is theirs — token spec to nail this down.
5. **Oracle dependency (planned: Pyth, post-v1).** Aave v3 requires a price oracle per asset. v1 can launch with Chainlink for blue-chip + a stopgap for long-tail; the planned destination is Pyth pull-oracle for cost. Pyth integration design lives in a separate post-v1 spec.

### Decisions log

- **2026-05-01** — Jonto: AMM = Velodrome v3 fork (pooled stableswap + CL volatile + ve(3,3) baseline). CDP scrapped in favor of GHO fork as native stable. Pyth = oracle plan, post-v1. Token spec owned separately by Jonto. All fees → single `FeeAccumulator` predeploy; distribution TBD in token spec.
