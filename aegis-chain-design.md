# Aegis Chain — AI-Secured L2 Design Doc

**Status:** Early scoping  
**Date:** 2026-04-15  
**Author:** Bob (with Jonto)

---

## Vision

An Ethereum L2 where validators are AI agents that understand normal behavior and can intervene when something doesn't make sense. Security is a property of the chain itself, not a reliance on audits, bug bounties, or hope.

**Core thesis:** The only scalable defense against novel on-chain attacks is judgment at the consensus layer—"does this transaction make sense?"—applied by every validator, to every transaction, in real time.

---

## Architecture

### Three Layers

```
┌─────────────────────────────────────┐
│        Intervention Layer           │  Validators signal/pause/reject
│   (consensus on flags, threshold)   │  based on anomaly confidence
├─────────────────────────────────────┤
│        Observation Layer            │  Off-chain AI models build
│   (behavioral profiles, anomaly     │  behavioral models per address
│    detection, escalation)           │  and per contract, async
├─────────────────────────────────────┤
│        Execution Layer              │  Standard EVM, deterministic
│   (optimistic rollup or ZK)         │  execution as usual
└─────────────────────────────────────┘
```

### Key Principle: Observation ≠ Consensus

The execution layer stays deterministic. AI judgment happens **off-chain** in the observation layer. The intervention layer is a lightweight **threshold voting mechanism** — validators don't need to agree on *why* something is suspicious, just *that* it is.

---

## Transaction Flow

```
Tx submitted
    │
    ▼
┌──────────────┐
│ Single agent │◄── Fast pre-check (<100ms target)
│ screening    │    Agent has address/contract behavioral profile
└──────┬───────┘
       │
       ├── Looks normal ──► Execute immediately
       │
       └── Something off ──► Escalate to validator set
                                  │
                           ┌──────▼───────┐
                           │ Multi-agent  │    Validators independently evaluate
                           │ vote         │    within short window (~1-2s)
                           └──────┬───────┘
                                  │
                           ┌──────▼───────┐
                           │ Threshold    │    e.g. >2/3 flag = pause/reject
                           │ decision     │    Below threshold = execute with flag logged
                           └──────────────┘
```

**This is the critical design choice:** A single agent screening keeps latency near-zero for the vast majority of txs. Only suspicious ones pay the multi-agent deliberation cost. The escalation path is the safety net.

### Latency Targets

| Path | Target | Rationale |
|------|--------|-----------|
| Normal tx (no flag) | <100ms | Agent pre-check only, no consensus overhead |
| Escalated tx | 1-2s | Multi-agent vote, still within L2 block time |
| Emergency pause | <5s | Council or supermajority can halt |

---

## Behavioral Modeling

### What Validators Learn

**Per-address profiles:**
- Typical transaction patterns (time, frequency, contract interactions)
- Value ranges (usual tx sizes, daily volumes)
- Counterparty graph (who they interact with)
- Protocol usage patterns (which protocols, which functions)

**Per-contract profiles:**
- Normal call patterns and parameter ranges
- TVL movement patterns
- User interaction distributions
- Upgrade/governance history

### Cold Start: L1 Data Ingestion

As an L2, we have a massive advantage: addresses already have history on Ethereum mainnet and other L2s. On chain deploy:

1. **Ingest L1/L2 history** — index historical tx data for addresses that bridge in
2. **Pre-train behavioral models** — before an address ever touches Aegis, we already know its patterns
3. **Contract classification** — map known contract types (DEX, lending, bridge, etc.) with normal behavior templates
4. **Bridge monitoring** — watch cross-chain flows for known exploit patterns

This means validators start with context, not from zero.

---

## Intervention Mechanism

### Flag Types

| Level | Meaning | Action | Who Triggers |
|-------|---------|--------|-------------|
| 🟢 Clear | Normal behavior | Execute | Single agent |
| 🟡 Watch | Unusual but not malicious | Execute + log | Single agent |
| 🟠 Escalate | Potentially malicious | Hold for vote | Single agent |
| 🔴 Pause | Likely exploit | Reject + pause address/contract | Validator supermajority |
| ⬛ Emergency | Active exploit in progress | Halt chain | Council or >90% validators |

### Dispute & Recovery

- Paused addresses/contracts can be unpinned via governance
- False positive appeals handled by human council
- Escalated but unconfirmed txs can be resubmitted after cooldown
- All flags are on-chain and auditable

---

## Validator Architecture

### Requirements

- Each validator runs an AI inference endpoint alongside the standard rollup node
- Validators must stake (slashable for poor performance or collusion)
- No single model provider requirement — diversity is a feature, not a bug

### Model Diversity

The system is stronger when validators use different models/approaches:
- Different LLM providers (ZAI, Anthropic, OpenAI, local models)
- Different behavioral modeling techniques
- Different anomaly thresholds

**Consensus on action, not reasoning.** This is what makes non-deterministic AI compatible with blockchain consensus.

### Inference Cost Challenge

This is the hardest technical problem. Targets:

| Approach | Pros | Cons |
|----------|------|------|
| Small fast models for screening | Low latency, low cost | Less capable judgment |
| Larger models for escalation only | Cost efficient | Escalation latency |
| Specialized fine-tuned models | Best accuracy per cost | Training overhead |
| Behavioral heuristics + LLM fallback | Cheapest baseline | Less adaptive |

**Likely architecture:** Tiered — lightweight heuristics + small model for screening, larger model only on escalation. Goal: average cost < $0.001/tx.

---

## Governance

### Phase 1: Human Council

- ~7-12 DeFi OGs and security researchers
- Veto power over agent decisions
- Approve/reject emergency pauses
- Set behavioral baselines and thresholds
- Manage model diversity requirements

### Phase 2: Progressive Decentralization

- Council decisions become advisory
- On-chain governance for parameter changes
- Validator set expands
- Community-driven security policies

### Phase 3: Full Autonomy

- Agents handle routine security decisions independently
- Council intervenes only for novel attack categories
- Governance manages protocol parameters, not individual decisions

---

## Adversarial Considerations

### Known Attack Vectors on the System Itself

1. **Gradual poisoning** — attacker slowly normalizes malicious behavior to shift agent baselines. *Mitigation: human council review of baseline shifts, conservative drift limits*
2. **Model manipulation** — attacker tries to influence which models validators run. *Mitigation: model diversity requirements, open-source model encouragement*
3. **MEV exploitation** — agents with inside info on flagging could front-run. *Mitigation: encrypted mempool, commit-reveal for flags*
4. **Sybil addresses** — create many new addresses with no history to avoid profiling. *Mitigation: new addresses have stricter default thresholds, bridge history is weighted*

### Philosophy

We can't stop every adversarial attack on the system itself. The goal is to make attacks *more expensive than the exploits they prevent*. Even partial coverage dramatically improves the security landscape vs. today's "hope the audit was good enough."

---

## Technical Stack (Tentative)

| Component | Options |
|-----------|---------|
| Rollup framework | OP Stack, Arbitrum Orbit, Polygon CDK, custom |
| AI inference | ZAI (cheap), local models, hybrid |
| Behavioral DB | ClickHouse / TimescaleDB for on-chain analytics |
| Vector store | For behavioral similarity search |
| Indexer | Custom or existing (Envio, Goldsky, Sentio) |
| Validator staking | Native token, Ethereum-re-staked |

---

## Validator Integrity & Slashing Design *(in progress)*

### The Problem

How do we ensure validators are actually screening txs honestly, without prescribing a specific model?

### Slashing Conditions (proposed)

| Condition | Severity | Rationale |
|-----------|----------|-----------|
| Approved a confirmed exploit (clear-cut) | Full slash | Negligence — any reasonable model should have flagged this |
| Failed to load current behavioral profiles | Partial slash | Not running the agreed-upon ground truth |
| Missed screening timeout (>2s no response) | Small slash | Availability requirement |
| Consistently outvoted by other validators | Warning → slash | Pattern suggests broken or dishonest model |
| Judgment call disagreement | No slash | Different models can disagree on edge cases — that's expected |

### The "Soul Hash" — Verifiable Behavioral Ground Truth

Validators bring their own models, but the **behavioral profiles** (the shared understanding of normal) are canonical:

1. Chain maintains a **canonical profile dataset** — updated each epoch
2. Dataset is hashed and committed on-chain (Merkle root)
3. Validators must prove they loaded the correct profiles (hash attestation in block header)
4. If a validator's block references a stale or wrong profile hash, block is rejected

```
Block Header Extension:
  profile_root: 0xabc...    // Merkle root of current behavioral profiles
  screening_result: flag    // 🟢🟡🟠🔴
  screening_sig: 0xdef...   // Validator's signature on the screening outcome
```

This is analogous to Bitcoin's rule: "if you aren't running the right code, your blocks are rejected."
We can't verify the model, but we can verify the data it was given.

### Still Noodling On

- **Profile attestation without leaking profiles:** If profiles are public, attackers can study them to find blind spots. If private, how do you verify the hash? Encrypted commit-reveal?
- **Gradual vs sudden slashing:** Should there be a warning period before slashing? How many false approvals before you lose stake?
- **Appeals process:** What if a validator gets slashed for a judgment call that looked like negligence?
- **Model performance benchmarking:** Should validators periodically be tested against known exploits (like a CAPTCHA for validators)? Pass the test or lose the right to validate.

---

## Open Questions

1. **Rollup type:** Optimistic (simpler, faster to ship) or ZK (stronger guarantees, harder to build)?
2. **Token model:** What incentivizes validators to run expensive inference? Gas surcharge? Inflation? MEV sharing?
3. **Model standardization:** Do we specify a minimum model capability for validators? How do we verify?
4. **Cross-chain monitoring:** How much do we ingest from L1/other L2s? Full indexing or just bridge events?
5. **Privacy:** Can validators see transaction content pre-execution? Implications for MEV.
6. **Legal:** Does pausing transactions create liability? Need legal framework for intervention.

---

## Phased Roadmap

### Phase 0: Research & Spec (Now)
- Detailed technical spec
- Behavioral modeling research & prototypes
- Validator economics design
- Council formation (informal)

### Phase 1: Testnet (3-6 months)
- OP Stack fork with agent validators
- Basic behavioral profiling (heuristic + small model)
- Single-agent screening + escalation
- Human council for all interventions
- Test with historical exploits as validation

### Phase 2: Mainnet v1 (6-12 months)
- Production rollup deployment
- L1 history ingestion for cold start
- Multi-model validator set
- Governance framework live
- Target: detect & pause known exploit categories

### Phase 3: Maturation (12-18 months)
- Fine-tuned models for DeFi-specific detection
- Novel exploit detection
- Progressive decentralization
- Cross-chain behavioral tracking

---

*"The only way to stop novel attacks is to have every validator ask: does this make sense?"*
