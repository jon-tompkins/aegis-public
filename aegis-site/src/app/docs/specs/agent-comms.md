# Agent Communication Network — Manifold Integration

**Spec Version:** 1.0  
**Author:** Bob  
**Date:** 2026-04-17  
**Status:** Research Complete  
**Drives:** Validator coordination, escalation flow

---

## Research Findings

### Manifold

**What it is:** Federated WebSocket mesh for agent discovery and task routing. Each hub (bobiverse, hog, trillian, etc.) exposes REST + WS APIs. Agents register with capabilities, tasks route by `name@hub`.

**Running at:** `ws://localhost:8768` (local), federation on 8766, REST on 8777.

**What it provides:**
- `POST /task` — route task to any agent on any hub (`target: "agent@hub"`)
- `GET /agents` — mesh-wide agent directory with capabilities
- `GET /capabilities` — capability index
- `GET /peers` — federation peer list

**License:** MIT (Manifold repo)

**What it does NOT provide:**
- Persistent pub/sub channels
- Message ordering guarantees
- Partition tolerance with eventual consistency
- Built-in signing/verification of messages

**Primitives used for Aegis:**
- `task_request/task_result` — validator ↔ coordinator communication
- `capability query` — validator registration
- `mesh_sync` — topology awareness (validator set changes)

### Tenet

**What it is:** Memory/context system with OpenAI-compatible API. Stores memories as typed objects (including teacups), queried by semantic search.

**Running at:** `http://localhost:4587` ( Context Hub)

**What it provides:**
- Semantic memory search
- Teacup recording (trigger, ground state, observation)
- Long-term context across sessions

**What it does NOT provide:**
- Real-time message delivery
- Multi-agent shared state
- Deterministic replay

**Caution for Aegis:** Tenet's memory is not deterministic. Adding Tenet to validator decision-making would make soul hash verification impossible — validators must produce identical screening results given identical inputs. Tenet is fine for **off-chain** coordination (logs, debriefs, agent memory) but must NOT be in the hot path of on-chain screening decisions.

### libp2p Gossipsub (Baseline)

Standard pub/sub for blockchain agent communication. Used by many L2s.

| Feature | Manifold | libp2p Gossipsub | NATS |
|---------|---------|-----------------|------|
| Multi-cloud federation | ✅ (WS peering) | ⚠️ (needs bootstrap) | ⚠️ (needs server) |
| Agent discovery | ✅ Built-in | ❌ | ❌ |
| Task routing | ✅ Built-in | ❌ | ❌ |
| Partition tolerant | ⚠️ (WS reconnect) | ✅ | ⚠️ |
| License | MIT | MIT/Apache | Apache |
| Complexity | Low | Medium | Medium |
| Already running | ✅ | ❌ | ❌ |

---

## Decision

**Use Manifold for v0.** Reasons:
1. Already running — zero new infra
2. Multi-cloud Tailscale peering works
3. Covers validator discovery and task routing needs
4. MIT license, simple codebase
5. We can extend it if needed (it's just WebSocket + REST)

**What goes on Manifold:**
- Validator registration (capability announcements)
- Escalation task routing (voter coordination)
- Profile snapshot distribution requests
- Cross-validator queries (capability lookup)

**What stays on-chain:**
- Flag gossip (broadcast to all validators)
- Vote results (finality)
- Profile roots (soul hash commitment)
- Block production

**Tenet for shared agent memory: NOT in v0.** Soul hash requires deterministic screening. Tenet's nondeterministic memory would break verification. Revisit post-mainnet if we can prove deterministic replay.

---

## Channel Mapping

| Channel | Mechanism | Latency Target | Delivery |
|---------|-----------|--------------|----------|
| Validator registration | Manifold `capability query` | On-demand | Reliable |
| Escalation task | Manifold `POST /task` | <100ms | At-least-once |
| Voter coordination | Manifold task routing | <500ms | Best-effort |
| Profile distribution | Manifold task (pull) | seconds | Reliable |
| Profile root sync | On-chain | — | Final |
| Flag gossip | On-chain event | <block time | Final |
| Vote results | On-chain tx | — | Final |

**Key insight:** Manifold handles the coordination. On-chain handles the truth. This is the same pattern as consensus: coordination off-chain, finality on-chain.

---

## Validator Registration Flow

```
Validator starts
    │
    ▼
Manifold: register with capabilities
    │
    ▼
Manifold: mesh sync propagates to all peers
    │
    ▼
Coordinator sees validator in agent list
    │
    ▼
Coordinator routes first-line txs to Guardian
```

---

## Escalation Flow (via Manifold)

```
Guardian flags tx as suspicious
    │
    ▼
Manifold: POST /task to validator set
  target: "aegis-validate@bobiverse"
    │
    ▼
Manifold routes to all registered validators
    │
    ▼
Validators respond with vote (task_result)
    │
    ▼
Coordinator collects votes,threshold met?
    │
    ├── Yes → on-chain pause/reject tx
    │
    └── No  → execute with flag logged
```

---

## Manifold Agent Definition for Aegis

Each Aegis validator runs a Manifold agent:

```json
{
  "name": "aegis-guardian",
  "hub": "bobiverse",
  "capabilities": [
    "aegis-screening",
    "aegis-tier1",
    "aegis-tier2",
    "aegis-vote"
  ],
  "hub": "bobiverse"
}
```

Registered via Manifold's `agent_runner` — a Python process that:
1. Connects to local Manifold WS (`:8768`)
2. Listens for `task_request` messages
3. Runs screening logic
4. Returns `task_result`

This is already how Manifold agents work — we just need to implement the agent script.

---

## Signed Messages

All Manifold messages for Aegis should be signed to prevent spoofing:

```json
{
  "type": "task_request",
  "task": { ... },
  "signature": "0x...",  // ECDSA sign(task_id + target + command)
  "signer": "0x..."     // Validator Ethereum address
}
```

Manifold doesn't verify signatures — that's Aegis's job. We add signature verification to the agent runner.

---

## Failure Modes

| Failure | Impact | Mitigation |
|---------|--------|-----------|
| Manifold hub down | Validators can't coordinate | Validators fall back to direct WS connections |
| Slow Manifold routing | Escalation latency | Keep Manifold path <500ms budget |
| Peer disconnects | Validator drops from mesh | Reconnect on timeout, resync state |
| Manifold partition | Partial mesh | On-chain fallback for critical paths |

---

## v0 Scope (What We Ship)

- [x] Decision: Manifold for coordination, on-chain for truth
- [x] Channel mapping defined
- [x] Validator registration via Manifold capability
- [x] Escalation routing via Manifold task
- [ ] Aegis agent script implementing screening interface
- [ ] 3-validator local testbed (Manifold hub + 2 validators)
- [ ] Latency benchmark for escalation path
- [ ] Signed message schema for Aegis messages

## v1+ Scope (Deferred)

- [ ] Dedicated flag gossip channel (libp2p or custom)
- [ ] Validator-to-validator direct WS (bypass Manifold)
- [ ] Profile distribution network
- [ ] TENET for off-chain agent memory (post-soul-hash)
