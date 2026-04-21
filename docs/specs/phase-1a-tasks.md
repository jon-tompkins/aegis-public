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

- [ ] **Initialize project structure**
  - Create `aegis-monitor/` directory in aegis-public
  - Set up `pyproject.toml` with dependencies: `fastapi`, `uvicorn`, `web3`, `eth-account`, `websockets`, `asyncpg`, `pydantic`, `alembic`
  - Create `src/` layout: `__init__.py`, `main.py`, `api/`, `screening/`, `attestation/`, `db/`
  - Add `Dockerfile` (Python 3.12, slim)

- [ ] **Define Pydantic models**
  - `Attestation` schema matching the spec shape
  - `PendingTx` schema for incoming Alchemy txs
  - `MonitorRequest`, `FlagResponse` schemas
  - Validate against the attestation sig requirements (EIP-191)

- [ ] **Set up Postgres + Alembic migrations**
  - `flags` table: `id, tx_hash, monitored_address, rule_id, rule_version, severity, reason_human, reason_structured (jsonb), agent_id, ts_ms, sig, created_at`
  - Indexes on `monitored_address`, `tx_hash`, `ts_ms`
  - Add `alembic` for migrations

### Alchemy WebSocket Subscription

- [ ] **AlchemyPendingTxListener class**
  - Connect to Alchemy WS (`wss://eth-mainnet.g.alchemy.com/v2/...`)
  - Subscribe to `alchemy_pendingTransactions` filtered by monitored addresses
  - Parse raw tx to `PendingTx` model
  - Emit to internal async queue

- [ ] **Address manager**
  - In-memory store of `monitored_addresses` (set)
  - API endpoints to add/remove: `POST /monitor`, `DELETE /monitor/:address`
  - Persist monitored list to Postgres `monitored_addresses` table so it survives restart
  - Load from DB on startup

- [ ] **Reconnection handling**
  - Exponential backoff on WS disconnect
  - Resubscribe to active filters on reconnect
  - Log disconnections for debugging

### Tier 1 Detection Rules

- [ ] **Rule engine (base)**
  - `Rule` protocol: `matches(tx: PendingTx) -> bool` + `severity`, `rule_id`, `rule_version`
  - `RuleRegistry` that runs all registered rules and collects hits
  - Each rule outputs a `RuleHit` with rule_id, severity, reason_human, reason_structured

- [ ] **Rule T1.1 — Approval to EOA spender**
  - Detect `approve`, `increaseAllowance`, `permit` calls where `spender` has no contract bytecode
  - Check: `web3.eth.get_code(spender) == b''` (no code)
  - ⚠️ HUMAN DECISION NEEDED: Should we cache bytecode lookups? For how long? TTL?
  - Test against known EOA approvers vs contract approvers

- [ ] **Rule T1.2 — setApprovalForAll to EOA**
  - Detect `setApprovalForAll` where `operator` has no contract bytecode
  - Same bytecode check as T1.1

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

- [ ] **EIP-191 signing**
  - Canonical JSON serialization of Attestation (deterministic — sorted keys, no whitespace)
  - Sign with agent's Ethereum key (_env: `AGENT_SIGNING_KEY`)
  - Produce `sig` field as `0x` hex signature

- [ ] **Attestation persistence**
  - On rule hit: construct `Attestation`, sign it, persist to Postgres `flags` table
  - Return attestation to caller

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
