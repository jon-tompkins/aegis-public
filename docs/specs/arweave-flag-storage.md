## Aegis Flag Storage — Arweave-Canonical + Postgres Hot Cache

**Spec Version:** 0.1 (draft)
**Author:** Bob
**Date:** 2026-04-23
**Status:** Draft — for Jonto/Clark review
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
- [ ] Pre-fund ~$20.
- [ ] Publish the monitor's EIP-191 signer pubkey at `/agent-identity`, and also upload a signed identity statement to Arweave (one-time). Record the Arweave tx id in infra docs.
- [ ] Apply the Alembic migration that adds `arweave_tx_id` + `arweave_confirmed_at`.
- [ ] Ship the writer task (Fargate sidecar or in-process background task — in-process is simpler for Phase 1a).
- [ ] Add CloudWatch metrics: `arweave_writer_queue_depth`, `arweave_writer_confirm_latency_ms`, `arweave_wallet_balance_usd`.
- [ ] Alarm: queue depth > 1000 OR wallet balance < $5.

---

## Open questions

1. **Bundler:** Irys vs Ardrive Turbo vs others — Irys is the default choice, open to alternatives if Jonto has a preference.
2. **Agent-identity anchoring:** do we want the signer pubkey itself committed to Arweave at install, or is the `/agent-identity` HTTP endpoint enough for Phase 1a? Bob's lean: anchor it on Arweave. One-time cost, removes a trust assumption.
3. **Delete semantics:** Arweave is permanent by design. If a flag is emitted in error, we cannot delete the canonical record — we can only emit a correcting follow-up flag. Confirm this is acceptable; it's consistent with "flags are append-only attestations, not editable records."
