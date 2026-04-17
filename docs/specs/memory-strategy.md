# Memory Strategy Research — Tenet, Teacups, and Visual Memory for Aegis

**Research Version:** 1.0  
**Author:** Bob  
**Date:** 2026-04-17  
**Status:** Research Complete — Conditional Recommendation  

---

## Source Systems

### Teacups (from TENET / bobiverse)

A memory filing system for agent decisions.

```
Teacup {
    trigger: string       # What prompted the observation
    ground_state: string # What was true before
    observation: string  # What happened
    outcome_score: +1/-1/0  # Did this turn out well?
    filed_by: agent
    filed_at: timestamp
    topic: string
    glyph: emoji         # Visual marker
}
```

Stored in TENET memory DB (SQLite), recalled by topic/agent/tag.

**Key property:** Non-deterministic. Two agents filing the same event may produce different teacups. That's fine for learning — bad for verification.

### MRI — Manifold Rendering Interface (from Manifold/bobiverse)

Visual diagnostic of the cognitive mesh topology.

```
MRISnapshot {
    atlas_data: { nodes, edges, holes }
    sophia: { dense_regions, score, gradient }
    bottleneck: { perceived, actual, displacement }
    bleed: { curvature decay over time }
    glossolalia: { coordination_pressure delta }
    captured_at: timestamp
}
```

Renders as D3.js force-directed graph. Shows:
- Agent nodes (size = vocabulary size)
- Edge seams (shared vocab but no transition map)
- Sophia hot regions (high curvature = wisdom zones)
- Holes (topic space with no coverage)

### Trust Ledger (from Manifold/bobiverse)

Economic reputation system for agent interactions.

```
Claim { agent, task, domain, stake? }
Grade { agent, domain, score: 0-1, task_id, slash_threshold }
TrustLedger { record(grade), rank(claims), domain_score(agent, domain) }
```

Domain-specific. Referral chains via ledger absorption. Slash on poor outcomes.

---

## The Soul Hash Problem

**Aegis requires deterministic screening.**

All validators must reach the same screening result given the same transaction + canonical profiles. If Model A and Model B disagree on the same tx with the same profiles, the soul hash cannot determine which was correct.

This creates a hard constraint:

> **Any system that influences screening decisions must be deterministic and on-chain verifiable.**
> **Any system that records learning must be off-chain and must NOT influence screening.**

Teacups and Trust Ledger are non-deterministic → they cannot be in the screening hot path.
MRI is a visualization tool → it has no influence on decisions at all.

---

## Assessment

### Teacups for Aegis

**Use cases:**
- Track false positives: validator flagged a normal tx → negative teacup → feedback to training pipeline
- Track true positives: validator caught a real exploit → positive teacup → reward signal
- Record escalation outcomes: what did the multi-agent vote decide? Did the Guardian agree?
- Pattern learning: compound teacups across many similar txs → identify systematic false positive patterns

**Constraint:**
- Teacups MUST NOT be read during screening. They can only be written after screening completes.
- Teacups are agent-local (each validator files their own).
- Outcome scoring requires an oracle (did the tx actually exploit? did the pause save funds?).

**Architecture:**
```
Screening result produced
    │
    ▼
Aegis event (tx flagged, paused, rejected)
    │
    ▼
Teacup filed by validator agent (off-chain)
    │
    ▼
Periodic review: false positive rate per validator
    │
    ▼
Feeds back into training pipeline (#8) for model improvement
```

NOT: Teacup → influences next screening decision.

### MRI for Aegis

**Use cases:**
- Validator mesh topology: are all validators covering the same tx space? Are there holes?
- Guardian coverage: which addresses/contracts have no Guardian coverage?
- Attack surface visualization: show the topology of what the validator set knows vs doesn't
- Onboarding diagnostic: when a new validator joins, what topics does it know vs what does the mesh not cover?

**Architecture:**
- MRI is purely observational. It reads the validator registry and capability announcements.
- It produces HTML diagnostic pages.
- No write path to the protocol.

**Very low risk. High ops value.**

### Trust Ledger for Aegis

**Use cases:**
- Validator stake/slash on screening outcomes
- Domain-specific reputation: validator A is good at catching DEXs, validator B is good at bridges
- Referral: validator A trusts validator B's grading on lending protocols

**Constraint:**
- Grading must be on **outcomes** (did the tx exploit? did the pause save funds?), not on **reasoning** (did the model use the right threshold?).
- Reasoning is subjective across models. Outcomes are verifiable on-chain.

**Architecture:**
```
Tx screened → flagged
    │
    ├── Escalated → multi-agent vote
    │       │
    │       └── Vote outcome (confirm/sclear) → Grade filed
    │
    └── False positive appeal → council review → Grade filed

Grade { validator, domain, score, task_id }
    │
    └── TrustLedger.rank() → validator selection for future screening
```

Slash condition: Grade score < threshold AND stake was posted.

---

## The Boundary

```
ON-CHAIN (deterministic, soul-hash verified)
─────────────────────────────────────────────
- Canonical profiles (#7)
- Soul hash commitment (#10)
- Screening flag + confidence
- Validator registration
- Block production
- Escalation votes (threshold)

OFF-CHAIN (non-deterministic, learning)
───────────────────────────────────────
- Teacups (validator screening debriefs)
- MRI (validator mesh topology)
- Training pipeline (#8)
- Validator grading (outcome-based)
- Trust ledger (reputation)
```

**The boundary is enforced by protocol design, not by trust.**

A validator's teacup filing has no mechanism to influence their next screening decision. The screening input is always the canonical profiles + current tx. Memory is read after; never before.

---

## Integration Points

### With Manifold (#9)

Manifold handles validator coordination (escalation routing, capability registration). The memory systems layer on top:

- **Manifold** → validator discovery + task routing
- **Teacups** → screening decision records filed per validator
- **Trust Ledger** → stake + grading on outcomes
- **MRI** → topology diagnostics

### With Training Pipeline (#8)

Teacups are the feedback loop for model improvement:

```
Teacup (outcome_score = -1, false positive)
    │
    ▼
Training pipeline: this tx was normal, model was wrong
    │
    ▼
Retrain Tier 1/2 models with updated labels
    │
    ▼
New model weights → new profile snapshots
    │
    ▼
Soul hash commits to new profiles
```

The soul hash verifies the profiles were updated correctly. Teacups drive when to update.

---

## Recommendation

**Apply all three systems to Aegis, with the following constraints:**

1. **Teacups**: Off-chain only. File after screening. Never read before screening. Use for false positive tracking and training feedback.
2. **MRI**: Ops tool only. Visualize validator mesh coverage. No protocol influence.
3. **Trust Ledger**: On-chain stake/slash on screening outcomes. Domain-specific. Referral chains.

**What this gives Aegis:**
- Validators learn from outcomes (teacups) without breaking soul hash determinism
- Operators can see the validator mesh topology (MRI) 
- Economic accountability via stake/slash (Trust Ledger)
- All non-deterministic learning stays off the critical path

**Risk if done wrong:**
- Validator reads teacups before screening → non-deterministic results → soul hash verification fails
- Mitigation: protocol enforces that screening input = canonical profiles + tx only

---

## Open Questions

1. **Teacup oracle:** Who scores the outcome? The protocol knows if a tx was paused/rejected — but did that save funds or was it a false positive?需要一个裁判. Can the council serve this role?
2. **Teacup storage:** TENET or a dedicated DB? If validators file teacups, they need a shared store to aggregate across validators.
3. **MRI update cadence:** Real-time? Hourly? Daily? What's the performance cost of generating MRIs?
4. **Trust Ledger domain scope:** How fine-grained should domains be? Per protocol (DEX, lending)? Per contract type? Per function?
5. **Grading threshold:** What score triggers slash? What fraction of stake?

---

## Further Research: Mesh Query Network

**Suggested by Jonto — 2026-04-17**

Beyond passive MRI snapshots, agents could **actively query the mesh** when interesting or ambiguous events occur:

```
Validator notices unusual pattern
    │
    ▼
Post to mesh: "Has anyone seen this contract behavior before?"
    │
    ▼
Peer agents respond with observations, similar txs, context
    │
    ▼
Response aggregated → filed as teacup
    │
    ▼
Feeds training pipeline (#8) — enriches profile with mesh knowledge
```

**Why this matters for training:**
- Individual validators see limited tx history
- Mesh-wide observations compound into collective intelligence
- Novel attack patterns spotted by one validator can propagate to all
- Enriches teacups with peer context, not just local observation

**Implementation path:**
- Manifold task system already supports broadcast queries
- Extend agent runner to accept "mesh_query" tasks
- Responses filed as enriched teacups (local observation + peer context)
- This stays OFF the screening hot path — purely for training enrichment

**This also unlocks:**
- Cross-validator false positive detection
- Distributed pattern recognition (one agent sees pattern → queries mesh → all learn)
- Council consultation via mesh (agent uncertain → council agents respond)

**Status:** Further research. Low urgency, high potential for training quality.

---

## Next Steps

If this research is approved:

1. Define the teacup schema for Aegis screening decisions
2. Add MRI generation to the validator ops tooling
3. Design the Trust Ledger integration with the staking contract
4. Write the off-chain store spec (TENET or dedicated)
5. Implement the boundary enforcement (screening input = profiles + tx only)
6. **[Further research]** Design mesh query protocol using Manifold task broadcast
