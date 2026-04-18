# Economics & Incentives

**Status:** Draft (tracks [#12](https://github.com/jon-tompkins/aegis-public/issues/12))
**Phase:** 0 — design
**Related:** [`aegis-chain-design.md` §Validator Integrity](../../aegis-chain-design.md), [`staking-systems.md`](./staking-systems.md)
**Incorporates:** Bob's `staking-systems.md` findings + Jonto's 2026-04-17 gas-token decision.

---

## Purpose

Fund validator inference, reward honest screening, punish negligence — without making the chain economically unattractive or centralizing around the cheapest model.

## Goals

- Validators profitably run Tier 1+2 on 100% of txs and Tier 3 on escalations.
- Users pay a predictable premium over a vanilla L2; target ≤2× base gas at mainnet v1.
- Incentives favor model diversity, not a cheapest-model race.
- Slashing punishes clear negligence, not judgment calls.
- Core DeFi primitives (AMM, lending, bridging) run natively on the chain so fees flow to validators structurally, not just through gas surcharge.

## Architecture (after merging `staking-systems.md`)

Four-layer stack:

```
┌─────────────────────────────────────┐
│ L4: UMA-style council                │  Bonded dispute / DVM vote on escalations.
│      Bond + dispute + vote           │
├─────────────────────────────────────┤
│ L3: EigenLayer AVS (v2, deferred)    │  Restaked-ETH path. Designed-for, not
│      Designed-for pluggability       │  built in v1.
├─────────────────────────────────────┤
│ L2: Aegis native staking (v1)        │  Validator bonds AEGIS + ETH.
│      AEGIS stake, ETH stake          │  Slashable for screening negligence.
├─────────────────────────────────────┤
│ L1: Ethereum consensus               │  Base settlement. ETH is the money.
│      ETH staking, OP Stack L2        │
└─────────────────────────────────────┘
```

## Revenue sources

| Source | How | v1 status | Notes |
|---|---|---|---|
| **Gas surcharge** | `base_gas + aegis_fee`, fee to validator pool | ✅ primary | Paid in ETH (or chain-native stable), **not AEGIS** — Jonto decision 2026-04-17 |
| **Chain-native AMM fees** | Aegis embeds Solidly-style AMM; swap fees → validator pool | ✅ | Per DeFi-in-a-Box |
| **Chain-native lending interest** | Aave-style pool lending; spread → validator pool | ✅ | Per DeFi-in-a-Box |
| **Chain-native bridging fees** | LayerZero-style native bridge; fees → validator pool | ✅ | Per DeFi-in-a-Box |
| **Inflation** | Native `AEGIS` emission to active validators | ✅ (bounded bootstrap) | Capped schedule TBD |
| **Insurance premium** | High-TVL protocols pay for enhanced scrutiny | ⚠️ optional | Pricing open question |
| **MEV share** | Validators get a cut of proposer MEV | ❌ v1 | Pulls focus from screening; revisit v2 |
| **Restaked-ETH yield (EigenLayer AVS)** | ETH restakers delegate; extra yield | ❌ v1, ✅ v2 | External dep risk for v1 |

**v1 mix:** gas surcharge + chain-native DeFi fees + bounded inflation + optional insurance tier. Users never pay gas in AEGIS.

## Gas token decision (Jonto — 2026-04-17)

**Users pay gas in ETH or a chain-native stablecoin. NOT AEGIS.**

Rationale:
- AEGIS price volatility would propagate directly into user gas cost.
- Removes AEGIS speculative premium from every transaction.
- Lowers onboarding friction: users need ETH (which they already have) instead of acquiring a new token just to transact.

AEGIS remains required for **staking and governance** — not transacting.

## Cost sanity check

From [`aegis-training-plan.md`](../../aegis-training-plan.md): ~$700/mo per validator at ~10M txs ≈ **$0.00007/tx**. At 50–100 validators the per-tx validator cost pool is **$0.004–$0.007** — well within a reasonable L2 surcharge.

## Slashing (starting values, to tune)

| Condition | Severity | Escalation |
|---|---|---|
| Approved a post-facto-confirmed exploit | 100% | Immediate after council confirmation |
| Stale `profile_root` (see [soul-hash.md](./soul-hash.md)) | 1% per offense | Capped at 10% per epoch |
| Screening timeout >2s | 0.1% per offense | Warn at 3, slash at 5 in 24h |
| Consistently outvoted on escalations | Warning | Pattern review after 100 disagreements |

### Validator CAPTCHAs

Periodic replay of known exploits injected into the screening queue, marked as drills post-hoc. Failing = warning; repeated failure = slash. Anti-memorization: drills mutate parameters over time.

## Council — UMA-style bond + dispute + DVM

For escalation arbitration (not real-time screening), Aegis adapts UMA's optimistic oracle pattern:

```
Guardian / validator flags suspicious tx
    │
    ▼
Assertion posted with bond (bond scaled to claim severity)
    │
    ├── No disputer within window → accepted automatically
    │
    └── Disputed → council vote (DVM analogue)
                  │
                  ├── Confirmed exploit → 100% slash + bond rewarded to disputer
                  │
                  └── False positive → assertion bond slashed; asserter rewarded nothing
```

| Parameter | v1 value | Notes |
|---|---|---|
| Liveness window | 15 min | Fast path for L2 cadence; UMA uses hours |
| Bond size | Scales with claimed loss (0.1% of TVL at risk) | Prevents frivolous claims |
| Council size | 7 (5-of-7 quorum) | Term-limited, staggered rotation |
| Vote duration | 6h (v1) → 24h (later) | UMA DVM is 48–96h; too slow for chain rhythm |

**Not** used for real-time screening (latency too high). Council handles disputes and policy, not the hot path.

## Chain-native DeFi — per DeFi-in-a-Box

Core primitives embedded in the chain:

| Primitive | Style | Purpose |
|---|---|---|
| AMM | Solidly / Uniswap v3 | Fee generation; LP for validators |
| Pool lending | Aave / Compound | Validator can borrow against staked position |
| Bridging | LayerZero / Across / native | Cross-chain asset movement |
| Governance / gauges | Curve / Solidly | Validator voting on protocol params |

Fee routing:
```
AMM swap fees ────────────┐
Lending interest spread ──┤→ Validator pool ──→ per-validator share
Bridging fees ────────────┤                      (after infra + T3 cost)
Gas surcharge ────────────┘
Inflation (AEGIS) ────────→ Validator pool (bounded schedule)
```

**Agents as hands-off protocol managers** (per DeFi-in-a-Box): threshold-based intervention on TVL / utilization anomalies, not active trading. Anomalies file as teacups → feeds training pipeline (see [`memory-strategy.md`](./memory-strategy.md)).

## Token (AEGIS) utility

- **Stake** — required to validate, slashable
- **Governance** — vote on council seats, slashing params, profile epoch cadence, protocol param changes
- **Not required** for users to transact (gas = ETH or stable; see above)
- **Not a speculative trading vehicle in v1** — no MEV share, no protocol utility beyond stake + governance

## Anti-capture

- **Model-diversity bonus:** small multiplier for validators running uncommon models — discourages everyone running the same cheap inference.
- **Council term limits + staggered rotation** against long-term human-layer capture.
- **Restaked ETH path designed for** (EigenLayer AVS in v2) so the validator set won't be purely AEGIS-token-captured once that ships.
- **Domain-specific reputation** (trust ledger, see `memory-strategy.md`) so a single captured domain doesn't corrupt the whole validator set.

## Numeric model

First-pass per-validator P&L under v1 assumptions lives in [`economics-model.csv`](./economics-model.csv). Summary from the base case (gas surcharge + inflation + insurance only — DeFi primitive fees not yet modeled):

| Line | Value |
|---|---|
| Monthly validator pool (gas + inflation + insurance) | **$6.73M** |
| Per-validator share (75 validators) | **$89.7k / mo** |
| Per-validator infra + T3 cost | **$830 / mo** |
| Per-validator gross profit | **~$88.8k / mo** |
| User cost per tx (base L2 + surcharge) | **$0.008** |
| Surcharge multiple over vanilla L2 | **1.67×** (target ≤2×) |
| Break-even surcharge (infra only) | **$0.000087 / tx** |

**Not yet in the model** — chain-native DeFi fee flows (AMM / lending / bridging). Those are upside over the base case; worth modeling once TVL and fee-tier assumptions firm up.

Every row is tuneable. Open-question rows are explicitly flagged in the CSV.

## Acceptance criteria

- [x] `docs/specs/economics.md` (this doc)
- [x] Numeric model in `docs/specs/economics-model.csv`
- [x] Gas-token decision incorporated (ETH / stable, not AEGIS)
- [x] EigenLayer path deferred to v2 with design-for-pluggability
- [x] UMA-style council pattern captured
- [x] Chain-native DeFi revenue captured (per DeFi-in-a-Box)
- [ ] Model DeFi-primitive fee flows in the CSV (TVL × fee tier)
- [ ] Slashing parameter table with per-value rationale
- [ ] AEGIS allocation & emission schedule (placeholders OK)
- [ ] Model-diversity bonus spec + capture-resistance analysis
- [ ] Council composition: tokenholders vs designated set
- [ ] Insurance tier pricing: TVL-indexed oracle vs self-declared

## Open questions (for Bob / Jonto)

1. **Inflation tail** — cap total supply, or indefinite low inflation?
2. **Insurance pricing** — TVL oracle, or self-declared tier?
3. **Council composition** — UMA-style token holders, or designated multisig set with term limits?
4. **EigenLayer timeline** — do we publish the v2 AVS interface now so ecosystem can build against it, or wait until v1 ships?
5. **Chain-native DeFi scope** — just AMM + lending, or full DeFi-in-a-Box stack (CDP stable, NFT marketplace, etc.)?
6. **AEGIS genesis allocation** — who gets what at launch? Validators, early users, treasury, team?
