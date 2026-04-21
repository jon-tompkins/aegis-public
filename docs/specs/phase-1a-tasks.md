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

- [ ] **Rule T1.3 — transferFrom by unauthorized caller**
  - Detect `transferFrom(owner, attackerEOA, ...)` where `msg.sender` is neither `owner` nor approved
  - Need to track allowance state for monitored addresses
  - ⚠️ HUMAN DECISION NEEDED: How do we track allowances? Full allowance map or just check current approval?

- [ ] **Rule T1.4 — Unlimited approval**
  - Detect approval amount = `uint256.max` (`2**256 - 1`) or > 10× historical balance
  - Need historical balance lookback (use Alchemy `getTokenBalances` or `alchemy_getTokenMetadata`)
  - ⚠️ HUMAN DECISION NEEDED: What's the 10× threshold source? User's max historical balance? Protocol's max?

- [ ] **Rule T1.5 — Fresh approval + new contract call**
  - Track: for each monitored address, when was the last approval given to an EOA?
  - If same address uses a new (unknown) contract within N blocks of fresh approval → flag
  - ⚠️ HUMAN DECISION NEEDED: What is N? Default 10 blocks? Configurable?

- [ ] **Run all rules against pending tx stream**
  - Pipeline: Alchemy tx → parse → run RuleRegistry → collect hits → emit for attestation

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

- [ ] **Endpoints**
  - `POST /monitor` — add address to monitoring set
  - `DELETE /monitor/:address` — remove address
  - `GET /monitor` — list all monitored addresses
  - `GET /flags?address=0x…&since=ts` — fetch historical flags, paginated
  - `WS /stream` — push new flags to connected clients in real time

- [ ] **WebSocket client manager**
  - Maintain set of connected WS clients
  - Broadcast new flags to all connected clients on new attestation
  - Handle client connect/disconnect gracefully

- [ ] **Health check + readiness**
  - `GET /health` — liveness
  - `GET /ready` — checks Alchemy connection + Postgres connection

### Testing

- [ ] **Unit tests for rules**
  - Mock `PendingTx` fixtures for each rule
  - Test each rule in isolation
  - Cover known true positives from historical exploits

- [ ] **Integration test: full pipeline**
  - Mock Alchemy WS with known pending tx
  - Verify attestation produced and persisted
  - Verify signature valid

- [ ] **Test against real exploit transactions**
  - Pull Ronin exploit txs, verify T1 rules detect them

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
