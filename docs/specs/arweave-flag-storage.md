## Aegis Flag Storage — Arweave-Canonical + Postgres Hot Cache

**Spec Version:** 0.2
**Author:** Bob
**Date:** 2026-04-23 (v0.1) → 2026-04-29 (v0.2 — open questions resolved)
**Status:** Accepted — Jonto delegated open-question calls to Bob on 2026-04-29
**Tracks:** [#28](https://github.com/jon-tompkins/aegis-public/issues/28) decision 4 (decentralized storage)
**Related:** [`infrastructure.md`](./infrastructure.md), [`phase-1a-tasks.md`](./phase-1a-tasks.md), [`screening-rules.md`](./screening-rules.md)

---

## Purpose

Aegis has a non-negotiable architectural rule: canonical Aegis data does not live in 3rd-party centralized services. For Phase 1a this applies to the signed flag attestations that `aegis-monitor` emits. Until Aegis L2 exists, flag attestations must persist to decentralized storage.

This spec answers *where* and *how* Phase 1a flags get written, read, verified, and cached — without blocking the hot path or compromising the `/stream` WS latency budget.

---

## Goals

- **Canonical source of truth** for every emitted flag lives on Arweave, not in a 3rd-party DB.
- **Anyone** can independently fetch a flag from a public Arweave gateway, recompute the canonical body, and verify the monitor's EIP-191 signature against the agent's published pubkey — no access to our infra required.
- **UI latency budget preserved** — `/flags` and `/stream` stay fast (sub-100ms p95) by reading from a Postgres hot cache that is a derived index of Arweave, not a source of truth.
- **Hot-path never blocks on Arweave** — signing latency, WS broadcast, and flag insertion cannot be gated on an external gateway call.
- **Cache is rebuildable from canonical storage** — if Postgres is lost or diverges, it can be reconstructed by scanning Arweave for Aegis-tagged transactions.

## Non-goals

- **Querying Arweave directly from the UI.** GraphQL over Arweave is fine for audit but not suitable as the primary read path for live dashboards.
- **Storing `monitored_addresses` on Arweave.** This is operator config, not canonical attestation data; it stays in Postgres.
- **Batching / merkle-commitment optimisations.** Phase 1a writes one Arweave record per flag. Batching is deferred to Phase 1b (where L2 commitments make it natural).
- **On-chain flag commitments.** Out of scope until L2 exists. Phase 1a is Arweave-only; migration path sketched at the end.

---

## Why Arweave (not IPFS, not L2)

| Substrate | Fit for Phase 1a flags |
|---|---|
| **Arweave** | Permanent, append-only, public, per-item cost paid once. Exactly matches the audit-trail requirement. Mature bundled-tx providers (Irys/Turbo) give instant addressability. |
| **IPFS** | Content-addressed, but persistence requires a pinning service — which is itself a centralized dependency or a new ops problem. No intrinsic permanence. Reject. |
| **Aegis L2** | Correct long-term home. Does not exist in Phase 1a. Chicken-and-egg: can't ship monitor until storage is solved. Deferred to Phase 1b. |

---

## Canonical record format

The existing `Attestation` schema already emits a deterministic signed body. We use it as-is.

**On Arweave, each flag is stored as one transaction with:**

### Data (payload)

The raw bytes of `Attestation.model_dump_json()` with `sort_keys=True, separators=(",", ":")`.

Equivalent to `AttestationBody.canonical_json()` + a `"sig"` field merged in, serialised with the same deterministic rules. This keeps verification trivially symmetrical:

```
sig           = record["sig"]
body          = {k: v for k, v in record.items() if k != "sig"}
message_bytes = canonical_json(body)   # sorted keys, no whitespace
recovered     = eth_account.recover_message(encode_defunct(message_bytes), signature=sig)
assert recovered == published_agent_pubkey
```

`Attestation.canonical_json()` (inherited from `AttestationBody`) is already the exact byte sequence signed under EIP-191. The spec line in `aegis_monitor/schemas.py` explicitly says: *"any change to the canonical serialisation breaks every prior signature. Treat this class as a wire-format contract."* Arweave pins us to that contract in public.

### Tags (indexable metadata)

Arweave transaction tags are key-value pairs queryable via GraphQL on any gateway. We use them purely for discoverability, never as the trust surface — the signed body is authoritative.

```
App-Name              : aegis-monitor
App-Version           : 0.1
Content-Type          : application/json
Aegis-Agent-Id        : <monitor agent id>
Aegis-Tx-Hash         : 0x<64 hex>
Aegis-Monitored-Addr  : 0x<40 hex>
Aegis-Rule-Id         : t1.approve_to_eoa
Aegis-Rule-Version    : t1-v0.1
Aegis-Severity        : high
Aegis-Ts-Ms           : 173...
```

A third-party auditor can run one GraphQL query — "all transactions where `App-Name = aegis-monitor` and `Aegis-Agent-Id = <ours>`" — and get the complete, independently-verifiable flag history.

**Note:** the tags duplicate fields that also live in the body. The body is canonical. If a tag ever disagrees with the signed body, the body wins and the tag is a bug.

---

## Write path

Hot path must not block on Arweave. Decoupled writer via outbox pattern.

### Flow

```
┌─────────────────────┐
│ Rule hit            │  (screening engine)
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ AttestationSigner   │  EIP-191 sign (already implemented)
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ Insert into `flags` │  + outbox row: (flag_id, status='pending')
│ (one txn, atomic)   │  ← commit point: downstream can read immediately
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ WS /stream broadcast│  fire-and-forget, unchanged
└─────────────────────┘

          ══════════════════════  async, out-of-band  ══════════════════════

┌─────────────────────┐
│ Arweave writer task │  background coroutine (or separate worker)
│ loops outbox        │
└─────────┬───────────┘
          ▼
┌─────────────────────┐     success     ┌─────────────────────────────────┐
│ POST signed bytes   │────────────────▶│ UPDATE flags SET arweave_tx=...,│
│ to Irys/Turbo       │                 │   outbox status='confirmed'     │
│ with tags           │                 └─────────────────────────────────┘
└─────────┬───────────┘
          │ failure
          ▼
┌─────────────────────┐
│ Exp. backoff retry, │  bounded (e.g. 10 attempts over ~1 hr)
│ then alert + park   │  row stays 'pending' until resolved
└─────────────────────┘
```

### Schema delta (Alembic migration)

Additive only — safe on a running Phase 1a:

```sql
ALTER TABLE flags
  ADD COLUMN arweave_tx_id        TEXT       NULL,
  ADD COLUMN arweave_confirmed_at TIMESTAMPTZ NULL;

CREATE INDEX ix_flags_arweave_pending
  ON flags (id)
  WHERE arweave_tx_id IS NULL;
```

The partial index is the outbox queue — no separate table needed. The writer task selects `FOR UPDATE SKIP LOCKED` off that index.

### Bundler choice: Irys (Turbo equivalent)

- Settles on Arweave permanently.
- Accepts sub-100 KB items at marginal cost (Aegis flags are ~500–800 bytes).
- Returns a tx id synchronously; the item is gateway-addressable within seconds.
- Paid in fiat/USDC or AR — no need to hold AR on the hot wallet long-term.

**Wallet:** one hot key in Secrets Manager. Top up monthly. Budget below.

---

## Read path

### Primary: Postgres hot cache (unchanged semantics)

`/flags` and `/stream` continue to read from the `flags` table. Response shape extends `FlagResponse` with two optional fields:

```python
class FlagResponse(BaseModel):
    id: int
    attestation: Attestation
    created_at: datetime
    arweave_tx_id: str | None         # null while pending confirmation
    arweave_confirmed_at: datetime | None
```

Clients that don't care about the audit trail ignore these fields. The UI renders a small "audit: arweave ↗" affordance once populated.

### Verification: `GET /flags/{id}/proof`

Returns everything a third party needs to verify independently, without trusting our Postgres:

```json
{
  "arweave_tx_id": "abc...",
  "gateway_url": "https://arweave.net/abc...",
  "canonical_body_bytes_b64": "...",
  "sig": "0x...",
  "signer_address": "0x...",
  "verify_howto": "docs/specs/arweave-flag-storage.md#verifying-a-flag"
}
```

The client can fetch the gateway URL, SHA-256 the body, recover the signer from the sig, and confirm it matches the published `signer_address`. No Aegis server in the trust path.

### Cache rebuild (operator tool, not hot path)

A one-shot script that walks the Arweave GraphQL index for `App-Name = aegis-monitor` and writes any missing flags back into Postgres. Useful for:

- Fresh-install of a read replica.
- Recovering from a Postgres data-loss incident.
- Periodic (e.g. weekly) divergence audit — any Arweave record not represented in Postgres is a writer bug or a data loss event.

---

## Verifying a flag (third-party procedure)

Publishing this is the point — anyone can do it with just the tx id and our agent pubkey:

```bash
# 1. Fetch the canonical record
curl -s https://arweave.net/<arweave_tx_id> > flag.json

# 2. Extract body + sig
jq 'del(.sig)' flag.json \
  | jq -cS .                            # sorted keys, no whitespace
  > body.json
SIG=$(jq -r .sig flag.json)

# 3. Recover the signer (pseudocode; any EIP-191 lib works)
python - <<'PY'
import json
from eth_account.messages import encode_defunct
from eth_account import Account

body = open('body.json', 'rb').read()
sig  = open('/dev/stdin').read().strip()  # or read from env
msg  = encode_defunct(body)
print(Account.recover_message(msg, signature=sig))
PY
```

If the recovered address equals the agent's published pubkey, the flag is authentic. If it doesn't match — or if the body has been mutated in any way — verification fails.

The agent's pubkey is published at `/agent-identity` on the monitor and (separately) pinned to Arweave itself at install time so the identity statement is also tamper-evident.

---

## Cost model

### Per-flag cost

- Flag JSON size: ~500–800 bytes worst case (long `reason_structured` blobs push the upper end).
- Irys free-tier threshold (as of writing): sub-100 KB items are free. **Verify current threshold before production.** If the free tier is removed, per-item cost is still fractional cents — Arweave bundled item pricing is roughly $0.000001–$0.00001 per flag at $10/GB.

### Steady state

Realistic monitoring load: ~1–10 flags/minute across the full watched-address set.

```
10 flags/min × 800 B × 60 × 24 × 30 = ~350 MB/month
```

At $10/GB Arweave bundled pricing: **~$3.50/month** worst case, likely **< $1/month** in practice.

### Attack burst

Spec's worst-case assumption: 100 flags/minute during a coordinated attack for ≤1 hour.

```
100 flags/min × 800 B × 60 = ~5 MB per attack hour
```

**~$0.05 per attack hour.** Irrelevant to the budget.

### Wallet top-up

Pre-fund the Irys wallet with ~$20/quarter. CloudWatch alarm on balance < $5.

---

## Failure modes

| Failure | Blast radius | Mitigation |
|---|---|---|
| Arweave gateway down | Writer task backs off, flags stay `pending` in outbox. Hot path unaffected. | Retry with exp. backoff; alert after 1 hr of queue growth |
| Irys API down | Same — writer task parks work in outbox | Same |
| Hot wallet out of funds | All writes park in outbox | CloudWatch alarm on wallet balance; manual top-up |
| Postgres lost | Flags already confirmed to Arweave are recoverable | Cache rebuild script (see above) |
| Canonical format change | Every prior signature would break | Never happens — `canonical_json()` is a wire-format contract. Add a versioned wrapper instead |
| Tag injection / wrong tags | Discoverability breaks for those flags | Body is authoritative; tags are a convenience index. Nightly reconciler detects divergence |
| Sig key compromise | Attacker could forge attestations | Rotate pubkey on `/agent-identity` + publish rotation notice to Arweave. Historical flags remain verifiable under the old key |

---

## Phase 1b migration path

Once Aegis L2 ships, the canonical home for flag commitments moves on-chain. Proposed evolution:

1. **Keep Arweave** as the full-payload audit trail. It's cheap and already works.
2. **Add an L2 commitment layer.** Each flag (or each batch of N flags) posts a `keccak256(canonical_body_bytes)` commitment to an Aegis L2 contract, along with the Arweave tx id. On-chain verification becomes: given a flag, fetch from Arweave, hash, compare to the on-chain commitment.
3. **Batching.** Once we have the L2, it's natural to roll up N flags into a merkle root and commit the root only — Arweave still holds individual records.

None of that changes the Phase 1a on-disk format. The `Attestation` wire contract and the Arweave tag schema are designed to survive the L2 migration untouched.

---

## Operator checklist (Phase 1a deploy)

- [ ] Generate a fresh Irys wallet keypair. Private key → Secrets Manager.
- [ ] Pre-fund Irys wallet ~$20 (USDC or AR via Irys top-up).
- [ ] Generate the monitor's EIP-191 signing keypair. Private key → Secrets Manager.
- [ ] Run `scripts/upload-agent-identity.py` to anchor the signer pubkey on Arweave. Commit the returned tx id to `infra/arweave-identity.json`.
- [ ] Verify `/agent-identity` returns the signer pubkey **and** the `arweave_identity_tx_id`.
- [ ] Apply the Alembic migration that adds `arweave_tx_id` + `arweave_confirmed_at` (and `supersedes` on `flags`).
- [ ] Ship the writer task (in-process background task is simpler for Phase 1a; promote to a sidecar if it becomes contention-heavy).
- [ ] Add CloudWatch metrics: `arweave_writer_queue_depth`, `arweave_writer_confirm_latency_ms`, `arweave_wallet_balance_usd`.
- [ ] Alarm: queue depth > 1000 OR wallet balance < $5.

---

## Resolved decisions (v0.2 — 2026-04-29)

Jonto delegated these calls on 2026-04-29 ("make a call and run, no strong opinion"). Recorded here so the rationale survives.

### 1. Bundler — **Irys** (confirmed)

Irys is the lowest-friction option for Phase 1a:
- Mature SDK in JS + Python; we're a Python shop.
- Free-tier covers <100 KB items; flag attestations are ~500–800 B, so steady-state cost is effectively zero.
- Funding accepts USDC + AR; no need to hold AR long-term.
- Returns the Arweave tx id synchronously and the item is gateway-addressable within seconds — fits the writer-task latency budget.
- Ardrive Turbo is functionally equivalent but adds an Ardrive account dependency and a less Python-friendly path. Reject for Phase 1a.

**Switch criterion:** if Irys becomes unavailable or pricing changes materially, the writer task is the only Aegis-side dependency — Bundlr-protocol-compatible alternatives drop in by changing the endpoint URL and SDK package. No data-format coupling.

### 2. Agent-identity anchoring — **Anchor pubkey on Arweave at install**

Required, not optional. The whole point of Arweave-canonical attestations is that a third party can verify a flag without trusting any Aegis-operated server. If the signer pubkey itself is only published at `/agent-identity` (an Aegis-operated HTTP endpoint), then a malicious operator could swap the published pubkey to match a forged signature retroactively. Anchoring the pubkey on Arweave at install closes that gap.

**Implementation:**
- One-time at agent install: emit an Arweave tx whose body is a small JSON identity statement signed by the agent's private key:
  ```json
  {
    "agent_id": "aegis-monitor-prod",
    "version": "0.1",
    "signer_address": "0x...",
    "issued_at": "2026-04-29T00:00:00Z",
    "supersedes": null
  }
  ```
- Tags: `App-Name: aegis-monitor`, `App-Type: identity`, `Aegis-Agent-Id: <id>`, `Aegis-Signer-Address: 0x...`.
- Resulting Arweave tx id is recorded in infra docs (and surfaced by `/agent-identity` as `arweave_identity_tx_id` for cross-reference).
- **Key rotation:** publish a new identity statement with `supersedes: <previous_tx_id>`. Historical flags remain verifiable against the historical pubkey — the chain of identity statements is the audit trail.

**Operator runbook addition (added to checklist below):**
> Generate signing keypair → upload signed identity statement to Arweave → record returned tx id in `infra/arweave-identity.json` (committed to the repo) → ship.

### 3. Append-only semantics — **Confirmed: corrections are follow-up flags, never deletes**

Arweave permanence is an intentional property, not a workaround. An erroneous flag is corrected by emitting a follow-up flag whose `reason_structured` references the prior flag's id and supersedes it. Both records remain on Arweave; clients reading flag history present the latest non-superseded record per `(agent_id, tx_hash, rule_id)` tuple by default, with a "show full history" affordance.

**Schema implication:** the `Attestation` body grows an optional `supersedes` field (mirroring the identity-statement pattern):

```python
class AttestationBody(BaseModel):
    # ... existing fields ...
    supersedes: int | None = None   # prior flag id this correction replaces
```

This is an additive, optional field. It does not break the canonical-json wire-format contract for any prior signed attestation (those omit the field entirely; canonical json drops null/absent fields uniformly). All prior signatures remain verifiable.

**UI implication:** the `/flags` list endpoint takes an optional `?include_superseded=true` query param. Default is to hide superseded records.

**Audit guarantee:** because Arweave is permanent, even a superseded flag is retrievable forever. A future investigation can always reconstruct exactly what the agent claimed and when, including subsequent corrections. This is the property that makes the system trustworthy.

---

## Follow-on tasks unblocked by these decisions

- [ ] Add `supersedes: int | None` to `AttestationBody` (additive, no signature break).
- [ ] Add `?include_superseded=true` query param to `GET /flags`.
- [ ] Add `POST /flags/{id}/correct` operator endpoint that emits a superseding flag (with audit log of who issued the correction).
- [ ] Implement `scripts/upload-agent-identity.py` — one-shot tool used during install to anchor the pubkey on Arweave.
- [ ] Surface `arweave_identity_tx_id` from `/agent-identity` once the upload script has been run.
- [ ] Wire Irys SDK into the writer task; smoke-test against Irys devnet first.
