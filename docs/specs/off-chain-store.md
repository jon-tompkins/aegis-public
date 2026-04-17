# Off-Chain Store — Teacups, MRI, Trust Ledger Persistence

**Spec Version:** 1.0 (draft)
**Author:** Clark
**Date:** 2026-04-17
**Status:** Draft
**Tracks:** [#13](https://github.com/jon-tompkins/aegis-public/issues/13)
**Related:** [`memory-strategy.md`](./memory-strategy.md), [`agent-comms.md`](./agent-comms.md), [`soul-hash.md`](./soul-hash.md)

---

## Purpose

Bob's [`memory-strategy.md`](./memory-strategy.md) establishes *what* Aegis keeps off-chain (teacups, MRI snapshots, trust-ledger grades) and *why they stay off-chain* (they're non-deterministic — admitting them onto the critical path would break soul-hash verification). This spec answers *where and how* they get persisted.

Core constraint, restated:

> **The screening hot path reads only canonical profiles (`#7`) + current tx.
> Teacups / MRI / trust-ledger are written after screening, read by training
> pipelines — never by validators during a screening decision.**

This spec is the boundary enforcer — a storage layer physically separate from the screening path.

## Goals

- One storage home for all non-deterministic memory artifacts.
- Clear write-side interface the validator agent runner uses after each screening decision.
- Clear read-side interface the training pipeline, MRI renderer, and trust ledger rank() use.
- Durable across validator restarts; shared across the validator set.
- Enforce — at the storage layer — that artifacts cannot leak into screening input.

## Non-goals

- Replacing on-chain profile storage ([`intent-mapping.md`](./intent-mapping.md)).
- Enabling deterministic agent memory (that's Tenet's design goal and is explicitly deferred per `agent-comms.md`).
- Consumer-facing API — this is validator-operator infra.

---

## Artifacts in scope

From [`memory-strategy.md`](./memory-strategy.md):

| Artifact | What it is | Who writes | Who reads |
|---|---|---|---|
| **Teacup** | One screening debrief (`trigger`, `ground_state`, `observation`, `outcome_score`, `topic`) | Validator agent, after screening | Training pipeline (#8); periodic FP / TP rate jobs |
| **MRI snapshot** | Mesh topology at a point in time (atlas, sophia, bottleneck, bleed, glossolalia) | MRI renderer (cron) | Ops / dashboards only |
| **Trust-ledger grade** | Outcome-based grade per validator per domain | Escalation resolver (after council vote) | Validator-selection ranker; slashing decisions |
| **Mesh query record** | Aegis-specific "has anyone seen this?" query + responses | Validator originator + responder agents | Training pipeline, teacup enricher |

Profile data is **not** in scope — it lives in ClickHouse per [`intent-mapping.md`](./intent-mapping.md).

---

## Storage choice — v0

**Postgres 16** as primary, with JSONB payload columns.

Rationale:
- **Transactional integrity** across teacup + grade writes in a single unit of work.
- Mature indexing on both scalar columns (for rank queries) and JSONB (for payload filters).
- Well-understood ops story — most teams already run it.
- Logical replication for the shared-across-validators story.

Rejected:
- **TENET SQLite** (referenced in memory-strategy.md) — fine for single-agent use, but validators need a shared store. Could still run a TENET-compatible front-end on top of this Postgres if interop matters later.
- **ClickHouse** — overkill for write-heavy small-row workloads; optimized for analytics scans not the transactional read path the trust ledger needs.
- **Neo4j / graph DB** — MRI would benefit, but not enough to pull in a second store for v0. MRI snapshots land as JSON in Postgres.

### Replication model

```
                          ┌─────────────────┐
                          │ Shared primary  │  Postgres 16
                          │ aegis-mem-01    │  write-heavy
                          └────────┬────────┘
                                   │ logical replication
                   ┌───────────────┼───────────────┐
                   ▼               ▼               ▼
           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
           │ Validator A  │ │ Validator B  │ │ Training     │
           │ read replica │ │ read replica │ │ read replica │
           └──────────────┘ └──────────────┘ └──────────────┘
```

Validators write to the primary (their own teacups and grades) and read from their own local replica for recency-insensitive queries. The training pipeline reads from a dedicated replica. MRI renderer reads wherever.

Note — this is still *off* the screening hot path; these reads never influence a screening decision.

---

## Schema

All tables live in schema `aegis_mem`.

### `teacups`

```sql
CREATE TABLE aegis_mem.teacups (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filed_by          BYTEA NOT NULL,              -- validator ethereum address (20 bytes)
    filed_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    topic             TEXT NOT NULL,               -- e.g. "tier1_screening", "escalation_vote"
    trigger           TEXT NOT NULL,               -- what prompted the observation
    ground_state     TEXT NOT NULL,               -- what was true before
    observation       TEXT NOT NULL,               -- what happened
    outcome_score     SMALLINT NOT NULL,           -- -1, 0, +1; NULL not allowed
    glyph             TEXT,                        -- optional visual marker
    subject_tx        BYTEA,                        -- tx hash the teacup describes, if any
    subject_address   BYTEA,                        -- address the teacup describes, if any
    epoch             BIGINT NOT NULL,             -- epoch at time of filing
    payload           JSONB NOT NULL DEFAULT '{}',  -- extra context (model output, profile snapshot ref, etc.)

    CONSTRAINT outcome_valid CHECK (outcome_score BETWEEN -1 AND 1)
);

CREATE INDEX teacups_topic_filed_at ON aegis_mem.teacups (topic, filed_at DESC);
CREATE INDEX teacups_filed_by       ON aegis_mem.teacups (filed_by);
CREATE INDEX teacups_subject_tx     ON aegis_mem.teacups (subject_tx) WHERE subject_tx IS NOT NULL;
CREATE INDEX teacups_subject_addr   ON aegis_mem.teacups (subject_address) WHERE subject_address IS NOT NULL;
CREATE INDEX teacups_epoch          ON aegis_mem.teacups (epoch);
```

### `trust_grades`

```sql
CREATE TABLE aegis_mem.trust_grades (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    validator         BYTEA NOT NULL,              -- graded validator address
    domain            TEXT NOT NULL,               -- "bridge", "lending", "dex", ...
    score             NUMERIC(5,4) NOT NULL,       -- 0.0000..1.0000
    task_id           TEXT NOT NULL,               -- identifier for the graded task (e.g. escalation vote id)
    graded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    graded_by         BYTEA NOT NULL,              -- council / oracle that issued the grade
    slash_threshold   NUMERIC(5,4),                -- below this triggers slash review
    rationale_hash    BYTEA,                        -- hash of the rationale (on-chain or elsewhere)

    CONSTRAINT score_valid CHECK (score BETWEEN 0 AND 1)
);

CREATE INDEX trust_grades_validator_domain ON aegis_mem.trust_grades (validator, domain);
CREATE INDEX trust_grades_graded_at        ON aegis_mem.trust_grades (graded_at DESC);
```

### `mri_snapshots`

```sql
CREATE TABLE aegis_mem.mri_snapshots (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    captured_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    atlas_data         JSONB NOT NULL,              -- nodes, edges, holes
    sophia             JSONB,                       -- dense_regions, score, gradient
    bottleneck         JSONB,                       -- perceived, actual, displacement
    bleed              JSONB,                       -- curvature decay over time
    glossolalia        JSONB,                       -- coordination_pressure delta
    validator_count    INT NOT NULL,
    agent_count        INT NOT NULL
);

CREATE INDEX mri_captured_at ON aegis_mem.mri_snapshots (captured_at DESC);
```

### `mesh_queries`

```sql
CREATE TABLE aegis_mem.mesh_queries (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    originated_by     BYTEA NOT NULL,              -- validator that asked
    originated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    query_text        TEXT NOT NULL,
    subject_tx        BYTEA,                        -- optional: tx the query is about
    subject_address   BYTEA,                        -- optional: address the query is about
    responses         JSONB NOT NULL DEFAULT '[]',  -- [{by, at, observation, confidence}]
    folded_into_teacup UUID REFERENCES aegis_mem.teacups(id)  -- if aggregation produced a teacup
);

CREATE INDEX mesh_queries_originated_by ON aegis_mem.mesh_queries (originated_by);
CREATE INDEX mesh_queries_originated_at ON aegis_mem.mesh_queries (originated_at DESC);
```

---

## Write-side API

Per validator agent runner, called **after** the screening decision is finalized — never before, never during.

```python
# aegis_memory/client.py  (sketch)

class MemoryClient:
    """Write-side client. Intentionally has no read methods that could
    be called during screening — separate ReadClient for that path."""

    def file_teacup(
        self,
        topic: str,
        trigger: str,
        ground_state: str,
        observation: str,
        outcome_score: int,  # -1, 0, +1
        epoch: int,
        subject_tx: Optional[bytes] = None,
        subject_address: Optional[bytes] = None,
        glyph: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> UUID: ...

    def record_grade(
        self,
        validator: bytes,
        domain: str,
        score: float,
        task_id: str,
        graded_by: bytes,
        slash_threshold: Optional[float] = None,
        rationale_hash: Optional[bytes] = None,
    ) -> UUID: ...

    def file_mesh_query_response(
        self,
        query_id: UUID,
        observation: str,
        confidence: float,
    ) -> None: ...
```

Enforcement: this client's connection string points only at the primary. The validator process can hold only this client in the screening module; the `ReadClient` (below) lives in a separate module imported by training / ops code only.

## Read-side API

```python
# aegis_memory/read.py  (sketch)

class ReadClient:
    """Read path. NOT imported by validator screening code.
    Imported by: training pipeline, MRI renderer, trust-ledger ranker,
    council tooling."""

    def teacups_for_subject(self, tx: Optional[bytes] = None,
                            address: Optional[bytes] = None,
                            topic: Optional[str] = None,
                            limit: int = 100) -> List[Teacup]: ...

    def trust_rank(self, domain: str) -> List[Tuple[bytes, float]]: ...

    def validator_domain_score(self, validator: bytes, domain: str) -> Optional[float]: ...

    def latest_mri(self) -> Optional[MriSnapshot]: ...

    def mesh_queries_pending(self, for_validator: bytes,
                             limit: int = 10) -> List[MeshQuery]: ...
```

## Boundary enforcement

The non-functional invariant is the whole point of this spec. Enforcement layers:

1. **Import graph (compile-time):** validator screening module imports only `aegis_memory.client`. `aegis_memory.read` is in a separate package. A CI lint fails the build if any file under `validator/screening/**` imports anything from `aegis_memory.read`.
2. **Connection credentials (runtime):** validator agent gets write-only DB credentials at startup. Read creds are never mounted in the screening container.
3. **Audit log (post-hoc):** Postgres logs every read + write with the client role. A quarterly audit confirms no `screening-*` role ever issued a `SELECT` against `aegis_mem.*`.

The first two prevent mistakes; the third catches them if they slip.

## Retention

| Artifact | Retention |
|---|---|
| Teacups | 2 years warm, then cold-storage export; used for training provenance |
| Trust grades | Indefinite — part of the validator's durable reputation |
| MRI snapshots | 30 days warm, then 1-per-day down-sample for a year |
| Mesh queries | 90 days warm, then cold — raw queries aren't as valuable as the teacups they fold into |

## Integration points

- **Training pipeline (#8):** consumes `teacups` as weak-labels; down-weights txs that were filed with `outcome_score = -1` (false positives).
- **Trust ledger consumer:** reads `trust_grades`, produces the validator-ranking list used at escalation-routing time.
- **Agent comms (#9):** Manifold task broadcast writes into `mesh_queries`; responder task results append to the `responses` array.
- **Council tooling:** writes to `trust_grades` after each confirmed-exploit or rejected-dispute outcome.

## Open questions

1. **Teacup oracle** — who scores `outcome_score = +1/-1`? Council-after-the-fact works but is slow. Cheaper feedback: on-chain confirmed-exploit labels + statistical FP sampling.
2. **Cross-validator teacup aggregation** — when two validators file teacups about the same tx with different `outcome_score`, how do we aggregate for training? Simple average, or trust-weighted?
3. **Postgres sizing** — at ~10M tx/mo and say 5% teacup rate, that's ~500k teacups/mo, ~6M/year. Well within Postgres comfort. Confirm once screening volume firms up.
4. **TENET compatibility** — do we front-end this store with a TENET-compatible API so single-agent memory tooling (outside Aegis) can read it? Low priority; list as v0.5 if anyone actually wants it.
5. **Sharding by domain** — trust grades segment cleanly by domain (bridge vs lending vs dex). Worth sharding early, or one table + partitioning later?

## Acceptance criteria

- [x] This spec (draft)
- [ ] Bob sign-off on: storage choice (Postgres), boundary-enforcement approach (import graph + creds + audit)
- [ ] Schema migration file at `indexer/sql/002_offchain_memory.sql` (Postgres dialect)
- [ ] Reference `aegis_memory` Python package with `MemoryClient` + `ReadClient` split
- [ ] Lint check that blocks any import of `aegis_memory.read` from the screening module
- [ ] Integration example showing a validator filing a teacup after screening a tx
- [ ] Retention / cold-storage spec for each artifact
