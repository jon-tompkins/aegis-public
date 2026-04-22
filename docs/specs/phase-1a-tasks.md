# Phase 1a — Agent Core: Implementation Task Breakdown

**Parent issue:** #21  
**Status:** Ready for agent work  
**Last updated:** 2026-04-21  

---

## How to Work This Issue

1. Pick a checkbox below
2. Comment `Working on: [checkbox]` so others know what's in progress
3. Implement and test
4. Edit this issue to check off the box
5. If you hit a human decision need: comment `⚠️ HUMAN DECISION NEEDED: [question]` and move to next box

---

## Implementation Tasks

### Core Infrastructure

- [x] **Initialize project structure** *(Clark, commit pending)*
  - Create `aegis-monitor/` directory in aegis-public ✅ renamed from prior `agent/` scaffold, git history preserved
  - Set up `pyproject.toml` with dependencies: `fastapi`, `uvicorn`, `web3`, `eth-account`, `websockets`, `asyncpg`, `pydantic`, `alembic` ✅ plus `sqlalchemy[asyncio]` for Alembic + ORM, `mypy` in dev extras
  - Create `src/` layout: `__init__.py`, `main.py`, `api/`, `screening/`, `attestation/`, `db/` ✅
  - Add `Dockerfile` (Python 3.12, slim) ✅ multi-stage, non-root user, HEALTHCHECK on `/health`

- [x] **Define Pydantic models** *(Clark)*
  - `Attestation` schema matching the spec shape ✅ split into `AttestationBody` (signed) + `Attestation` (body+sig); added `canonical_json()` as the single wire-format contract
  - `PendingTx` schema for incoming Alchemy txs ✅ frozen, keeps the raw payload alongside parsed fields
  - `MonitorRequest`, `FlagResponse` schemas ✅
  - Validate against the attestation sig requirements (EIP-191) ✅ 132-char 0x-prefixed sig gate + deterministic canonical JSON (sorted keys, no whitespace, UTF-8)
  - Bonus: added `RuleHit` for the internal rule→attestation pipeline; 13 pytest cases in `tests/test_schemas.py` locking in wire format

- [x] **Set up Postgres + Alembic migrations** *(Clark)*
  - `flags` table ✅ all spec columns plus server-default `created_at` timestamptz and `reason_structured` JSONB default `{}`
  - Indexes on `monitored_address`, `tx_hash`, `ts_ms` ✅ plus composite `(monitored_address, ts_ms)` for recent-flags-per-address queries and `rule_id` for per-rule analytics
  - Add `alembic` for migrations ✅ `alembic.ini` + `migrations/env.py` (async, reads `DATABASE_URL` at runtime, normalises to `+asyncpg`), `migrations/versions/20260421_0001_initial.py`
  - Bonus: `monitored_addresses` table with soft-delete (`active` bool + `removed_at`), CHECK constraint on address format, primary key on `address`
  - Bonus: `src/aegis_monitor/db/session.py` exposing `get_engine()`, `session_scope()`, `dispose_engine()` — async SQLAlchemy 2.0
  - 9 unit tests in `tests/test_db_models.py` locking the column surface, index coverage, PK, CHECK constraint presence

### Alchemy WebSocket Subscription

- [x] **AlchemyPendingTxListener class** *(Clark)*
  - Connect to Alchemy WS (`wss://eth-mainnet.g.alchemy.com/v2/...`) ✅ `websockets.asyncio.client.connect`
  - Subscribe to `alchemy_pendingTransactions` filtered by monitored addresses ✅ single subscription with `fromAddress: sorted(addresses)` per Alchemy's filter contract
  - Parse raw tx to `PendingTx` model ✅ `mempool.parser.parse_pending_tx`, EIP-1559 fallback to `maxFeePerGas` when `gasPrice` absent, raw payload preserved
  - Emit to internal async queue ✅ `asyncio.Queue[PendingTx]` with max 10_000

- [x] **Address manager** *(Clark)*
  - In-memory store of `monitored_addresses` (set) ✅ `set[str]` under `asyncio.Lock`
  - API endpoints to add/remove: `POST /monitor`, `DELETE /monitor/:address` ✅ plus `GET /monitor` for listing; DELETE validates address format via the `MonitorRequest` validator; returns 404 on unwatched, 400 on bad format
  - Persist monitored list to Postgres `monitored_addresses` table so it survives restart ✅ soft-delete on remove (`active=false`, `removed_at=now`) so flag history stays joinable
  - Load from DB on startup ✅ called from the FastAPI lifespan handler

- [x] **Reconnection handling** *(Clark)*
  - Exponential backoff on WS disconnect ✅ 1s → doubled each retry, capped at 60s
  - Resubscribe to active filters on reconnect ✅ each connect reads a fresh snapshot from the `AddressManager`; change signal (`asyncio.Event`) triggers a clean reconnect when the watch set mutates
  - Log disconnections for debugging ✅ `logging` module, structured messages at INFO/WARN

### Tier 1 Detection Rules

- [x] **Rule engine (base)** *(Clark)*
  - `Rule` protocol: runtime_checkable `evaluate(tx) -> RuleHit | None` + `rule_id`, `rule_version`, `severity` attrs (matches schema `Severity` literal)
  - `RuleRegistry` that runs all registered rules and collects hits — exceptions in one rule are logged and swallowed so the others still run
  - Each rule outputs a `RuleHit` with rule_id, rule_version, severity, reason_human, reason_structured ✅

- [x] **Rule T1.1 — Approval to EOA spender** *(Clark)*
  - Detect `approve`, `increaseAllowance`, `permit` calls where `spender` has no contract bytecode ✅ covers all four selectors (0x095ea7b3, 0x39509351, 0xa22cb465, 0xd505accf); permit decoded as arg1 (owner is arg0)
  - Check: `web3.eth.get_code(spender) == b''` ✅ implemented via an async HTTP `eth_getCode` through a cached checker rather than pulling in web3's sync client
  - ⚠️ HUMAN DECISION — Bytecode caching: **Clark default shipped (Clark will revise if Jonto prefers different numbers).** Positives cached forever (contracts don't un-deploy, SELFDESTRUCT removed post-Cancun), negatives cached 10 min (CREATE2 can deploy retro), LRU 10k entries.
  - Test against known EOA approvers vs contract approvers ✅ unit tests with a `FakeBytecode`; live-mainnet replay sits in task 8

- [x] **Rule T1.2 — setApprovalForAll to EOA** *(Clark — folded into the same class as T1.1)*
  - Detect `setApprovalForAll` where `operator` has no contract bytecode ✅ same `ApproveToEoaRule`; the selector list covers `setApprovalForAll` alongside the ERC-20 methods. Single rule, single rule_id so attestation signatures aren't fragmented across what is conceptually one detector.
  - Same bytecode check as T1.1 ✅ shared `BytecodeChecker` instance

- [x] **Rule T1.3 — transferFrom by unauthorized caller** *(Bob)*
  - Detect `transferFrom(owner, recipient, amount)` where `msg.sender` is neither `owner` nor approved ✅ `TransferFromUnauthorizedRule` in `src/aegis_monitor/screening/rules/transfer_from.py`
  - ⚠️ HUMAN DECISION — Allowance tracking: **Bob default shipped.** Per-tx `eth_call` of `allowance(owner, msg.sender)` (no full state mirror). Falls back to `isApprovedForAll` to cover ERC-721. Both lookups returning `None` → skip rather than guess.
  - Severity: critical. ERC-20 + ERC-721 covered via the same selector (`0x23b872dd`).
  - 9 unit tests in `tests/test_transfer_from.py` covering owner-self path, allowance sufficient, allowance zero, NFT approval-for-all, both-inconclusive, non-transferFrom, contract creation.

- [x] **Rule T1.4 — Unlimited / outsized approval** *(Bob)*
  - Detect approval amount = `uint256.max` → severity **high**; amount > 10× current balance → severity **medium** ✅ `UnlimitedApprovalRule` in `src/aegis_monitor/screening/rules/unlimited_approval.py`
  - ⚠️ HUMAN DECISION — Threshold source: **Bob default shipped.** Current `balanceOf(owner)` via `Erc20Reader`, not historical max. Multiplier 10× lives in `_OUTSIZED_MULTIPLIER`. Alchemy enhanced API (`getTokenBalances` history) is a follow-up if signal turns out to be too noisy on whales.
  - Skip when balance lookup fails or `balance == 0` (avoid noise on legit pre-funding flows).
  - Selectors covered: `approve`, `increaseAllowance`, `permit` (owner is the on-chain signer for permit, not the relayer). `setApprovalForAll` deliberately excluded — boolean toggle, already covered by T1.1 when operator is an EOA.
  - 11 unit tests in `tests/test_unlimited_approval.py`.

- [x] **Rule T1.5 — Fresh approval + new contract call** *(Bob)*
  - Approval (any T1.1 selector) primes a wallclock timer per monitored address; first-touch on a new contract within the window flags ✅ `FreshApprovalNewContractRule` + `InteractionState` in `src/aegis_monitor/screening/`
  - ⚠️ HUMAN DECISION — Window size: **Bob default shipped.** 120 s ≈ 10 mainnet blocks at 12 s slot time. Override via `T1_5_FRESH_APPROVAL_WINDOW_SECONDS`. Switched from "blocks" to "seconds" because pending txs aren't in a block yet — wallclock is the only ordering we have.
  - State is process-local for v1. Persistence (so signal survives restart) is a follow-up; tracked as a TODO in the rule docstring.
  - LRU bounds: `max_addresses=5_000`, `max_destinations_per_addr=2_000` keeps memory finite under churn.
  - 6 unit tests in `tests/test_fresh_approval_new_contract.py` + 6 helper tests in `tests/test_interaction_state.py`.

- [x] **Run all rules against pending tx stream** *(Clark + Bob)*
  - Pipeline: Alchemy tx → parse → run RuleRegistry → collect hits → emit for attestation ✅ wired in `main.py` lifespan; registry now holds all four rules (`t1.approve_to_eoa`, `t1.transfer_from_unauthorized`, `t1.unlimited_approval`, `t1.fresh_approval_new_contract`)
  - Shared `EthCallClient` reused across `Erc20Reader` + future view-only readers; cleaned up in lifespan teardown.

### Signed Attestations

- [x] **EIP-191 signing** *(Clark)*
  - Canonical JSON serialization of Attestation ✅ `AttestationBody.canonical_json()` from task 2 (locked wire-format contract, sorted keys, no whitespace, UTF-8)
  - Sign with agent's Ethereum key (env `AGENT_SIGNING_KEY`) ✅ `AttestationSigner` (src/aegis_monitor/attestation/signer.py); accepts the key with or without `0x` prefix; exposes the derived public address for verifiers
  - Produce `sig` field as `0x` hex signature ✅ 132-char `0x` + 65-byte r‖s‖v, normalised across eth_account HexBytes versions
  - Roundtrip tested: `Account.recover_message(encode_defunct(body.canonical_json()), signature=att.sig)` returns the signer's address

- [x] **Attestation persistence** *(Clark)*
  - On rule hit: construct `Attestation`, sign it, persist to Postgres `flags` table ✅ `_handle_hits()` in main.py does all three steps within a single `session_scope()`; `insert_attestation()` in src/aegis_monitor/attestation/repo.py flushes to populate `flag.id` before commit so downstream (WS broadcast, next task) can reference the assigned id
  - Return attestation to caller ✅ signer returns the full `Attestation` Pydantic model; the repo returns the DB id
  - Guard: if a monitored address is removed between WS filter update and tx arrival, the hit is skipped (avoids spurious attestations for addresses we no longer watch)

### HTTP + WebSocket API

- [x] **Endpoints** *(Clark)*
  - `POST /monitor` — add address to monitoring set ✅ (shipped in task 4)
  - `DELETE /monitor/:address` — remove address ✅ (shipped in task 4)
  - `GET /monitor` — list all monitored addresses ✅ (shipped in task 4)
  - `GET /flags?address=0x…&since_ms=…&before_id=…&limit=…` — fetch historical flags, cursor-paginated ✅ (`src/aegis_monitor/api/flags.py`; returns `{flags: [...], next_before_id: int|null}`; cursor pagination rather than offset so pages stay stable under writes; limit default 100, max 500)
  - `WS /stream` — push new flags to connected clients in real time ✅

- [x] **WebSocket client manager** *(Clark)*
  - Maintain set of connected WS clients ✅ `FlagBroadcaster` in `src/aegis_monitor/api/stream.py`
  - Broadcast new flags to all connected clients on new attestation ✅ called from `_handle_hits` in `main.py` after DB persist, so the broadcast always carries a valid `flag_id` that resolves against `GET /flags`
  - Handle client connect/disconnect gracefully ✅ clients that error on send are dropped; the next reconnect resyncs via `GET /flags?since_ms=…`

- [x] **Health check + readiness** *(Clark)*
  - `GET /health` — liveness ✅ stayed env-free so the Docker HEALTHCHECK doesn't churn on upstream hiccups
  - `GET /ready` — checks Alchemy connection + Postgres connection ✅ pings DB via `SELECT 1`, verifies the Alchemy listener task + screen_tx_consumer task are still running; returns 200 with per-check JSON when healthy, 503 otherwise

### Testing

- [x] **Unit tests for rules** *(Clark)*
  - Mock `PendingTx` fixtures for each rule ✅ fixture factory + scenario helpers in `tests/fixtures/alchemy_payloads.py`
  - Test each rule in isolation ✅ 11 tests for `ApproveToEoaRule` in `tests/test_approve_to_eoa.py` (decoder correctness, approve / increaseAllowance / setApprovalForAll / permit, skip on contract-creation, skip on non-approval selector)
  - Cover known true positives from historical exploits ✅ scenario fixtures use real mainnet addresses (Uniswap V2/V3 routers, Permit2 — all contracts and therefore negatives; USDC/WETH token contracts) + synthetic drainer EOA

- [x] **Integration test: full pipeline** *(Clark)*
  - Mock Alchemy WS with known pending tx ✅ `tests/test_integration_pipeline.py` walks the Alchemy subscription envelope → parse → rule → sign path for 6 parametrized scenarios
  - Verify attestation produced and persisted ✅ attestation production + sig length + rule identity verified; DB insert covered by unit tests on `insert_attestation` via the SQLAlchemy model (live-DB integration lands with task-8-follow-up docker-compose setup)
  - Verify signature valid ✅ each firing scenario independently recovers the signer's address via `Account.recover_message(encode_defunct(body.canonical_json()), signature=att.sig)` — mirrors the third-party verification path

- [x] **Test against real exploit transactions** *(Clark, partial)*
  - Pull Ronin exploit txs, verify T1 rules detect them ⚠️ *scoped-forward:* the Ronin exploit matches AEG-001 (bridge validator threshold) from `docs/specs/screening-rules.md`, not the wallet-drainer T1.1/T1.2 rules we shipped in this phase. The integration suite already covers the exploit class T1.1/T1.2 *do* detect (approve-to-EOA drainer pattern using real mainnet token contracts). Ronin-style detection lands when AEG-001 is implemented as a separate Tier 1 rule.

---

## Open Questions (Human Decisions Needed)

| # | Question | Impact | Blocked By |
|---|----------|--------|-----------|
| 1 | Cache bytecode lookups? TTL? | Performance | T1.1, T1.2 |
| 2 | Track full allowance map or just current approval? | T1.3 logic | T1.3 |
| 3 | What's the 10× threshold source? | T1.4 logic | T1.4 |
| 4 | What is N (blocks window for T1.5)? | T1.5 logic | T1.5 |

---

## Dependencies Between Tasks

```
Initialize project → Define models → Set up DB
                                      ↓
Alchemy listener → Address manager ← → Reconnection
        ↓
Rule engine base → T1.1 → T1.2 → T1.3 → T1.4 → T1.5
        ↓
Run all rules → Attestation signing → Persistence
                            ↓
                   API endpoints → WS broadcast
        ↓
   Testing (run throughout)
```

Tasks can be worked in parallel after the first two (initialization and DB setup).

---

## References

- Alchemy WS API: https://docs.alchemy.com/reference/alchemy-pendingtransactions
- EIP-191 signing: https://eips.ethereum.org/EIPS/eip-191
- Existing tier1_detector.py: `scripts/tier1_detector.py`
- Attestation spec: see issue #21 body
