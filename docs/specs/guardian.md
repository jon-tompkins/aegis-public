# Guardian vs Validating Agent — Design Decision

**Spec Version:** 1.0  
**Author:** Bob  
**Date:** 2026-04-17  
**Status:** Resolved  
**References:** aegis-chain-design.md, issue #11

---

## Decision: Ship Later, Keep in Design

**Do not block testnet on Guardians.** The single-agent screening layer already provides first-line defense. Add Guardian as a distinct concept in v1 if measurable gap emerges.

---

## What We Already Have

The Aegis design already describes a two-tier screening architecture:

```
Tx submitted
    │
    ▼
┌──────────────┐
│ Single agent │ ◄── First line: address/contract behavioral profile
│ screening    │     Latency target: <100ms
└──────┬───────┘
       │
       ├── Normal ──► Execute
       │
       └── Suspicious ──► Escalate to validator set
                              │
                        Multi-agent vote (1-2s)
                        Threshold: >2/3 flag → pause/reject
```

This first-line screening **is** the Guardian role. It just wasn't named that way.

---

## What Clark's "Guardian" Adds

Clark's spec formalizes the Guardian as:

| Guardian Property | Aegis Equivalence | Status |
|-----------------|------------------|--------|
| Opt-in per user | Not yet designed | Open |
| ~50ms response budget | <100ms already spec'd | Align |
| Local/TEE preferred | Own model, BYO | Align |
| Co-signs UserOps (EIP-4337) | Not designed | Ship later |
| Stake/bond | Not in v0 | Ship later |

The **EIP-4337 integration** and **per-user opt-in** are the new parts. Everything else is already in the existing design under "single-agent screening."

---

## The Real Question: Opt-In or Universal?

**Option A — Universal first-line screening (current design)**
- Every tx goes through single-agent screening before hitting the chain
- No user opt-in needed
- Validators cover everyone equally
- Simpler trust model

**Option B — Guardian as opt-in RPC replacement**
- Users choose a Guardian agent (like choosing an RPC provider)
- Guardian monitors that user's addresses specifically
- Better per-user context
- Adds trust complexity (which Guardian? what if it misbehaves?)

**Decision: Option A for v0.** Universal first-line screening means Guardians don't add trust assumptions to the base protocol. We can add opt-in Guardian layer on top later without changing the core.

---

## Revised Transaction Flow

```
Tx submitted
    │
    ▼
┌──────────────────────────────────────┐
│  First-Line Screening (Guardian)      │ ◄── Built into protocol
│  Single agent, <100ms                   │     All txs pass through
└──────────────┬───────────────────────┘
               │
               ├── Normal ──► Execute
               │
               └── Flagged ──► Validator Set
                                     │
                               Multi-agent vote
                               >2/3 flag → pause/reject
```

---

## Guardian v1 Scope (Future)

If we add Guardians in a later version:

```
Guardian = First-Line Screening Agent + Per-User Context + EIP-4337 Co-Signer

User opts in:
  → Selects Guardian agent
  → Guardian monitors their addresses
  → Guardian co-signs UserOps (EIP-4337 AA)
  → Guardian can pause own txs proactively

Protocol never requires Guardians.
```

---

## Open Questions (Deferred)

1. **EIP-4337 integration:** Do we want Guardian co-signing on day one, or add AA support later?
2. **Guardian directory:** If users choose Guardians, who runs the directory? How do we prevent Guardian capture?
3. **MEV leakage:** If Guardians see txs before submission, can they MEV Extract?
4. **Guardian economics:** How do Guardians get paid? Flat fee per monitored address? Fraction of caught exploits?

---

## Conclusion

The Guardian/validator split already exists in the design. The first-line single-agent screening **is** the Guardian. The naming is a clarification, not a new feature.

The open items in Clark's spec are valid v1+ work but don't block testnet:
- EIP-4337 integration (later)
- Per-user opt-in (later)
- Guardian stake/bond (later)

**Recommendation:** Close this issue as resolved, add Guardian naming to the design doc, and defer EIP-4337 integration to v1+.

---

## Acceptance Criteria

- [x] Decision: ship later, Guardians are v1+ work
- [x] Guardian = first-line screening (already in design)
- [x] Protocol uses universal first-line, opt-in Guardian on top
- [ ] Update Aegis design doc to use "Guardian" naming
- [ ] EIP-4337 Guardian module (deferred to v1)
- [ ] Guardian threat model (deferred)
