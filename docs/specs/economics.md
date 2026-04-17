# Economics & Incentives

**Status:** Draft (tracks [#12](https://github.com/jon-tompkins/aegis-public/issues/12))
**Phase:** 0 — design
**Related:** [`aegis-chain-design.md` §Validator Integrity](../../aegis-chain-design.md)

---

## Purpose

Fund validator inference, reward honest screening, punish negligence — without making the chain economically unattractive or centralizing around the cheapest model.

## Goals

- Validators profitably run Tier 1+2 on 100% of txs and Tier 3 on escalations.
- Users pay a predictable premium over a vanilla L2; target ≤2× base gas at mainnet v1.
- Incentives favor model diversity, not a cheapest-model race.
- Slashing punishes clear negligence, not judgment calls.

## Revenue sources

| Source | How | Pros | Cons |
|---|---|---|---|
| **Gas surcharge** | `base_gas + aegis_fee`, fee to validator pool | Aligns cost with usage | Higher sticker price |
| **Inflation** | Native `AEGIS` emission to active validators | Bootstraps early | Dilutive; not sustainable long-term |
| **MEV share** | Validators get a cut of proposer MEV | Extra upside | Pulls focus toward MEV over screening |
| **Insurance premium** | High-TVL protocols pay for extra scrutiny | Direct revenue from protected value | Uneven for non-paying protocols |

**v1 mix:** gas surcharge (primary) + bounded inflation (bootstrap) + optional insurance tier for high-TVL protocols.

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

## Token (AEGIS) utility

- **Stake** — required to validate, slashable
- **Settlement** — gas surcharge paid in ETH; inflation paid in AEGIS
- **Governance** — vote on council seats, slashing params, profile epoch cadence
- **Not required** for users to transact

## Anti-capture

- **Model-diversity bonus:** small multiplier for validators running uncommon models — discourages everyone running the same cheap inference.
- **Restaked ETH path:** allow validating with restaked ETH (EigenLayer AVS) alongside native AEGIS so the validator set isn't purely token-holder-captured.
- **Council term limits + staggered rotation** against long-term human-layer capture.

## Numeric model

First-pass per-validator P&L under v1 assumptions lives in [`economics-model.csv`](./economics-model.csv). Summary from the base case:

| Line | Value |
|---|---|
| Monthly validator pool (gas + inflation + insurance) | **$6.73M** |
| Per-validator share (75 validators) | **$89.7k / mo** |
| Per-validator infra + T3 cost | **$830 / mo** |
| Per-validator gross profit | **~$88.8k / mo** |
| User cost per tx (base L2 + surcharge) | **$0.008** |
| Surcharge multiple over vanilla L2 | **1.67×** (target ≤2×) |
| Break-even surcharge (infra only) | **$0.000087 / tx** |

Assumptions and sensitivities are in the CSV. Numbers are placeholders for the v1 discussion — every row is tuneable.

## Acceptance criteria

- [x] `docs/specs/economics.md` (this doc)
- [x] Numeric model in `docs/specs/economics-model.csv`
- [ ] Slashing parameter table with rationale per value
- [ ] Token allocation & emission schedule (placeholder percentages fine)
- [ ] Model-diversity bonus spec + capture-resistance analysis
- [ ] Decision: native-stake-only vs. restaked-ETH path for v1

## Open questions

- Inflation tail — cap total supply, or indefinite low inflation?
- Insurance tier pricing — oracle off TVL, or self-declared?
- How do we keep MEV-share from turning validators into builders who de-prioritize screening?
- Governance quorum for changing slashing parameters — how conservative?
