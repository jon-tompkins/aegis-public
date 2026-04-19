# Memory Strategy

**Status:** Draft
**Phase:** 0 — design
**Related:** [`soul-hash.md`](./soul-hash.md), [`training-pipeline.md`](./training-pipeline.md), [`agent-comms.md`](./agent-comms.md), [`economics.md`](./economics.md)

---

## Purpose

Aegis needs a memory system that lets validators learn from screening outcomes over time — without ever breaking the determinism that soul-hash verification depends on. This spec defines what that memory system must do at the protocol level and what it must not do. Specific mechanisms (teacup filing, mesh topology rendering, trust-ledger reputation, mesh-query propagation) are listed at the end as candidate implementations, to be designed in their own specs.

## The boundary — the one invariant

> **Memory is read *after* screening, never *before*.**

Screening must be a pure function of `(canonical_profiles, transaction)`. Any validator, any model, any time — given the same profiles and the same tx — must produce the same result. That's what soul-hash verification checks; if memory sneaks into the input, the hash cannot adjudicate disagreements.

This splits the protocol cleanly:

```
ON-CHAIN (deterministic, soul-hash verified)
─────────────────────────────────────────────
- Canonical behavioral profiles  (soul-hash.md, intent-mapping.md)
- Soul-hash commitment            (soul-hash.md)
- Screening flag + confidence
- Validator registration
- Block production
- Escalation votes

OFF-CHAIN (non-deterministic, learning)
───────────────────────────────────────
- Screening-decision records       (write-only during the screening path)
- Outcome labels                   (was a flag correct in hindsight?)
- Validator reputation             (scored on outcomes, not reasoning)
- Mesh observability               (coverage gaps, topic holes)
- Training-pipeline feedback       (what the models should learn next)
```

**The boundary is enforced by protocol design, not by trust.** The screening input is hardwired to profiles + tx. Whatever a validator knows beyond that cannot reach the screening function.

---

## What the memory system must do

### 1. Record screening decisions for later review

Every screening decision a validator makes — cleared, flagged, escalated — becomes a record. Records are **write-only during the screening path**: filed after the decision is emitted, never consulted to produce it.

Minimum content:
- which validator, which tx
- the decision and its confidence
- the canonical profile commitment in effect at that height
- the inputs the validator saw (so auditors can replay)

No specific schema is prescribed here; see *Candidate mechanisms* below.

### 2. Attach outcome labels after the fact

A flag is correct if the tx would have exploited something and the pause prevented it. A flag is a false positive if the tx was benign. A cleared tx that later drained a pool is a miss.

Outcome labels come from a source outside the validator's own head — typically the council for contested cases, on-chain post-facto evidence for clear ones. Open question: see §Open questions #1.

### 3. Feed the training pipeline

Outcome-labelled records are the supervised signal the next round of models is trained against. The soul-hash commits to new profiles; memory drives *when* and *why* those profiles change. See [`training-pipeline.md`](./training-pipeline.md).

### 4. Support domain-specific validator reputation

Staking uses outcomes to reward honest screening and slash negligence ([`economics.md`](./economics.md)). Reputation must be **outcome-scored, not reasoning-scored** — whether a validator's flags hold up in hindsight, not whether its model "thought like the others." Domain-specific scoring (validator A is strong on DEXs, B on bridges) falls out naturally and feeds validator selection for future work.

### 5. Surface mesh-level coverage and gaps

Ops-level question: across the whole validator set, which protocols / contract types / behavioral patterns are well-covered and which are blind spots? Purely observational — produces dashboards, never inputs to screening.

### 6. Enable cross-validator learning (optional, higher-tier)

A single validator sees a narrow slice of flow. Patterns that show up at the mesh level (novel attack signatures, correlated false positives) are worth surfacing without forcing every validator to see every tx. This is the most speculative of the requirements — pushed to future work.

---

## Interfaces

| System | What memory provides | What memory consumes |
|---|---|---|
| Screening hot path | *(nothing)* | the screening decision record |
| [Training pipeline](./training-pipeline.md) | labelled records for the next training round | profile-update signal |
| [Staking / economics](./economics.md) | outcome-scored reputation per validator per domain | slash / reward triggers |
| [Agent comms](./agent-comms.md) | validator discovery, routing | escalation outcomes become outcome labels |
| Council | outcome labels on contested flags | contested cases to rule on |

---

## Non-goals

- **Not a second consensus mechanism.** Memory does not produce on-chain decisions. Only profiles + the screening function do.
- **Not a shared brain.** Validators are not required to reach the same memory state. They are required to reach the same *screening* result from the same profiles.
- **Not a surveillance layer.** Memory records screening decisions and outcomes, not user behaviour writ large. The screening function already sees the tx; memory doesn't see more than screening did.

---

## Candidate mechanisms (future work)

The following approaches have been explored in adjacent systems and are candidates for Aegis's memory layer. Each would get its own spec; this section is a pointer list.

| Candidate | Role it could fill | Source / reference |
|---|---|---|
| **Structured decision records** ("teacups" or similar) | §1 screening-decision records, §3 training feedback | Imported concept from TENET; schema TBD |
| **Visual mesh rendering** (MRI-style) | §5 coverage and gaps | Imported concept from Manifold; D3 force graph or similar |
| **Trust ledger with domain scoring** | §4 reputation, §3 slash hooks | Imported concept from Manifold |
| **Mesh-query propagation** | §6 cross-validator learning | Jonto, 2026-04-17 — broadcast "has anyone seen X?" over the comms layer |

None of these are committed. They are listed so future specs have a common vocabulary and so the reader knows where the protocol-level requirements came from.

---

## Open questions

1. **Outcome oracle.** For flagged txs that were paused or rejected, how do we retroactively decide whether the flag was correct? On-chain evidence suffices for confirmed exploits; the hard cases (flag was ambiguous, tx never executed) need a rule. Council seems the right default — cost and cadence TBD.
2. **Record storage.** Validator-local, validator-cluster, or protocol-wide shared store? Affects privacy of screening inputs and the cost of reputation aggregation.
3. **Privacy posture.** Records contain the tx inputs the validator saw. Are these public, hash-only, or validator-private? Aligned with the privacy-posture open question on [`intent-mapping.md`](./intent-mapping.md) and [`soul-hash.md`](./soul-hash.md).
4. **Reputation resolution.** Per protocol, per contract family, per function selector? Finer = better targeting but harder to aggregate signal.
5. **Slash thresholds.** What outcome-score distribution triggers a slash, and at what fraction of stake? Tracked in [`economics.md`](./economics.md); memory defines the input.

---

## Acceptance criteria

- [x] Boundary invariant stated (memory read-after, never read-before)
- [x] On-chain / off-chain split captured
- [x] Protocol-level requirements listed independent of any specific mechanism
- [x] Interfaces with training, staking, agent-comms defined
- [x] Candidate mechanisms listed as future work, not as decisions
- [ ] Decision-record schema (own spec)
- [ ] Outcome-oracle rule (answered, codified)
- [ ] Reputation resolution + slash thresholds (settled in [`economics.md`](./economics.md))
- [ ] Privacy posture aligned across `intent-mapping.md`, `soul-hash.md`, and the record store
