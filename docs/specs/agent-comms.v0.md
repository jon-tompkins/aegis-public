> **v0 note — Clark's pre-merge draft, preserved for diff.**
>
> Bob's current version is [`agent-comms.md`](./agent-comms.md). That's the canonical one.
> This file exists so we can diff and recover anything Bob's rewrite dropped.
> Run `git diff docs/specs/agent-comms.v0.md docs/specs/agent-comms.md` to compare.

---

# Agent Communication Network

**Status:** Research / scoping (tracks [#9](https://github.com/jon-tompkins/aegis-public/issues/9))
**Phase:** 0 — design, **blocked on research**
**Related:** [`aegis-chain-design.md`](../../aegis-chain-design.md), [soul-hash.md](./soul-hash.md)

---

## Purpose

Design how the validator set and supporting agents communicate: flag gossip, escalation votes, profile distribution, heartbeats.

**User note:** *"Manifold is an external product that allows for agent communication. Not relevant here unless we use it as the basis for agent-validator comms — but we need to do research before deciding. Tenet is an agent memory system we can also evaluate for shared agent memory — also needs to be evaluated."*

So this issue has **two research tracks** before any implementation:

1. **Agent comms layer** — Manifold vs. libp2p vs. hand-rolled gossip.
2. **Shared agent memory** — Tenet (evaluate), or none (each validator self-contained).

## Requirements (independent of which product we pick)

### Channels

| Channel | Payload | Latency | Delivery |
|---|---|---|---|
| `screening.flag` | single-agent flag on a tx (🟢🟡🟠) | <100ms end-to-end | best-effort broadcast |
| `escalation.vote` | validator vote on escalated tx | <1s round-trip | reliable, quorum-aware |
| `profile.update` | incremental profile deltas between epochs | seconds | reliable, in-order per address |
| `profile.root` | new `profile_root` at epoch boundary | eventual | reliable, signed |
| `validator.heartbeat` | liveness + screening latency stats | 1s cadence | best-effort |

### Properties

- Authenticated (BLS or similar), all messages signed by sender validator.
- Partition-tolerant — short splits shouldn't wedge consensus; validators fall back to conservative defaults.
- Rate-limited per channel; a noisy validator can't DoS the network.
- Observable — metrics + audit log of who said what.

## Candidate stacks

| Option | Pros | Cons | Next step |
|---|---|---|---|
| **Manifold (external)** | Purpose-built for agent comms | External dependency; unknown SLAs/licensing | Review repo/docs, confirm it covers our channels |
| **libp2p gossipsub** | Battle-tested in Ethereum consensus | Generic; we build the agent layer | Estimate effort vs. Manifold |
| **NATS / Redpanda** | Operationally simple, strong ordering | Centralized broker unless clustered; not p2p-native | Probably only for internal ops, not validator comms |
| **Hand-rolled** | Full control | Large build + audit surface | Only if nothing else fits |

**Research exit criteria (before committing):**
- Confirm each required channel maps to a Manifold primitive with acceptable latency.
- Confirm license and governance of Manifold.
- Confirm we can run Manifold embedded in a validator process (or a sidecar with a clean boundary).

## Shared agent memory — separate evaluation

Question: should validators share a memory layer (e.g. "here's what this address did five minutes ago, already judged"), or should each validator be fully self-contained?

**Tenet as a candidate** — evaluate:
- What memory primitives does it expose (episodic, semantic, vector)?
- Consistency / freshness model?
- Does it conflict with the soul-hash determinism requirement (shared memory must not make `profile_root` ambiguous)?
- Privacy — same concerns as [intent-mapping.md](./intent-mapping.md).

**Alternative:** no shared memory. Validators rely only on the canonical `profile_root` dataset. Simpler, more deterministic, but loses some efficiency on re-evaluation.

## Acceptance criteria

- [ ] Link to Manifold source/docs in this doc
- [ ] Link to Tenet source/docs in this doc
- [ ] Research writeup: Manifold primitives vs. our required channels
- [ ] Research writeup: Tenet memory model vs. determinism / privacy constraints
- [ ] Decision: comms stack for v0
- [ ] Decision: shared memory yes/no for v0
- [ ] Signed-message schema + versioning
- [ ] 3-validator local testbed exchanging flags via the chosen stack

## Open questions

- Where does the comms layer live — in-process library, sidecar, or remote service?
- Does escalation vote go over the agent-comms layer, or directly over OP Stack P2P (latency vs. infra reuse)?
- Does the chosen stack provide ordering strong enough for escalation votes, or do we add a light consensus shim?
- Shared memory on or off — and if on, how does it interact with soul hash?
