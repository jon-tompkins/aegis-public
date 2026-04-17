# Clark — Session Handoff

**Date:** 2026-04-17
**Previous session:** web-based Claude Code (claude.ai/code)
**This session:** local `claude` CLI
**User:** Jonto (jon-tompkins)
**Repo:** `jon-tompkins/aegis-public` (the only repo you're authorized to touch)

---

## Who you are

You are **Clark** — one of two coordinating agents working on Aegis, a layer-2 Ethereum chain with AI validators. Bob is the other. You hand work back and forth via GitHub labels:

- `clark` on an issue = **in your queue**, your turn
- `Bob` on an issue = **out of your queue**, his turn
- `Bob` + `tenet/done` = you think the issue is finished, awaiting Bob's close
- `Bob` + `tenet/backlog` (or `tenet/in-progress`) = you couldn't finish, needs Bob to take it further

Convention is documented in `.claude/commands/clark-loop.md` — read it before the first tick.

## What to start with

Run this once the session is alive:

```
/loop 10m /clark-loop
```

It invokes the slash command at `.claude/commands/clark-loop.md`, which does one full pass of clark-labeled issues every 10 min. It'll tick once immediately, then every 10 min while this terminal stays open.

## Current state on `main`

Last commit by previous session: **`af43517`** — "Grind: advance #7, #12, #13, #14".

Bob has been pushing too (he's on `main` directly). Head of `main` as of handoff also includes Bob's:
- `docs/specs/staking-systems.md`, `hack-taxonomy.md`, `memory-strategy.md`, `byo-model.md`
- `scripts/tier1_detector.py` (T1-001..T1-006 — you added T1-007..T1-010)
- Rewrites of `intent-mapping.md`, `soul-hash.md`, `guardian.md`, `agent-comms.md` (your earlier versions preserved at `*.v0.md` alongside)

**Always `git pull origin main` at the start of each tick** — Bob may have pushed between your runs.

## Issue status snapshot at handoff

| # | Title | State | Labels |
|---|---|---|---|
| #7 | Intent Mapping | Clark-done, awaiting Bob close | `Bob` + `tenet/done` |
| #8 | Training Pipeline | Handed back, not done (needs network) | `Bob` + `tenet/backlog` |
| #9 | Agent Comms | Handed back, not done (needs live Manifold hub) | `Bob` + `tenet/backlog` |
| #10 | Soul Hash | Bob's draft on main; hadn't reached this on last tick | check labels |
| #11 | Guardian | Bob resolved as "ship later" | probably closed or Bob+done |
| #12 | Economics | Clark-done, awaiting Bob close | `Bob` + `tenet/done` |
| #13 | Memory / Off-chain store | Clark-done, awaiting Bob close | `Bob` + `tenet/done` |
| #14 | Hack Taxonomy / T1 rules | Clark-done, awaiting Bob close | `Bob` + `tenet/done` |

**First thing each tick:** refresh this via the `clark` label filter, not this table. State drifts.

## Key repo orientation

```
aegis-public/
├── aegis-chain-design.md           # top-level architecture
├── aegis-training-plan.md          # 16-week plan, 3-tier screening
├── docs/specs/                     # canonical specs
│   ├── intent-mapping.md           # profile store (Bob's current version)
│   ├── intent-mapping.v0.md        # Clark's pre-merge draft, kept for diff
│   ├── soul-hash.md                # Bob + Clark co-authored
│   ├── soul-hash.v0.md             # pre-merge
│   ├── economics.md                # staking-systems findings merged in
│   ├── economics-model.csv         # per-validator P&L
│   ├── byo-model.md                # Bob: screening I/O proto
│   ├── staking-systems.md          # Bob: EigenLayer / UMA / DeFi-in-a-Box
│   ├── hack-taxonomy.md            # Bob: exploit patterns
│   ├── memory-strategy.md          # Bob: Tenet / teacups / MRI
│   ├── off-chain-store.md          # Clark: Postgres persistence for above
│   ├── agent-comms.md              # Bob: Manifold v0 decision
│   ├── agent-comms.v0.md           # Clark pre-merge
│   ├── guardian.md                 # Bob: ship-later decision
│   └── guardian.v0.md              # Clark pre-merge
├── indexer/                        # Rust workspace (skeleton)
│   ├── crates/types/                # aligned w/ intent-mapping.md schema
│   ├── crates/ingest/               # AlchemySource stub
│   ├── crates/features/             # extract_block → TxFeatureRow
│   ├── crates/profile/              # ProfileStore trait + MemoryStore
│   ├── crates/screener/             # Screener trait + Tier1RuleEngine
│   ├── bin/aegis-indexer/           # CLI: backfill / stream
│   └── sql/001_initial_schema.sql   # ClickHouse DDL matching Bob's spec
├── scripts/
│   ├── tier1_detector.py            # T1-001..T1-010 rule engine (Python)
│   └── exploits/
│       ├── exploits.json            # 10 seed exploits for backtest
│       └── README.md
└── .claude/
    ├── commands/clark-loop.md       # your loop prompt — read it
    └── HANDOFF.md                   # this file
```

## Active open questions to be aware of

These surfaced in recent handoff comments and may come back on `clark`:

1. **SSZ endianness** — `intent-mapping.md` says `UInt256` big-endian, SSZ canon is little-endian. Flagged in the DDL header + Rust types module. Blocks real test vectors for #7 and #10.
2. **Epoch cadence** — 12h vs 1d. Affects `soul-hash.md` grace-window logic and `profile_epoch` snapshot cost.
3. **Testnet privacy posture** — fully public vs public-hash / private-detail. Bob picked Mode B (public-hash / private-detail) in `soul-hash.md`. Confirm that's also the answer for `intent-mapping.md`.
4. **Teacup oracle** — who scores `outcome_score = ±1` in `off-chain-store.md`. Council works but is slow.
5. **Inflation tail, insurance pricing, council composition** — three items on `economics.md` I left for Jonto.

If Bob sends these back labeled `clark`, you have context.

## Sandbox limitations that tripped the previous session

The previous session ran in an environment without:
- Internet to crates.io / npm / pypi (couldn't `cargo check` the indexer workspace)
- A live Manifold hub (couldn't test the agent comms interface)
- Direct access to the user's laptop

Your local CLI session **doesn't have those limits**. Things you can now actually do:
- `cd indexer && cargo check` to validate the Rust workspace compiles against real crate pins
- If Manifold is running on the user's laptop (`ws://localhost:8768`), you can test the agent registration flow for #9
- Run `python3 scripts/tier1_detector.py ...` against real RPC-fetched data

When a clark-labeled issue is blocked only by one of those, this session can unblock it. Check if you're on a networked box before deciding to hand something back to Bob for "sandbox limits" reasons.

## Conventions the previous session established

- **Commits to `main`** directly. Jonto OK'd this. No feature branches unless explicitly asked.
- **Commit message style:** one-line summary, blank line, what-and-why paragraphs. Trailer: `https://claude.ai/code/session_015YDnZivGE2so6FD7NgoWFC` (this session will have its own URL; use whichever Claude Code CLI surfaces).
- **Be frugal with GitHub comments.** One summary per issue is enough. Don't narrate intermediate work.
- **Always `git pull origin main` at start of each tick** (Bob may have pushed).
- **Labels are the handoff signal.** No other coordination mechanism — Bob doesn't read comments to decide what's his.

## What NOT to redo

The previous session already:
- Set up `.github/workflows/{setup-labels,clark-monitor}.yml`
- Wrote `.claude/commands/clark-loop.md`
- Landed v0 drafts at `docs/specs/*.v0.md` (don't modify those — reference only)
- Did the #12 staking-systems merge, the #13 off-chain store spec, the #14 T1 rule extension + exploit DB seed, the #7 DDL reconciliation

If any of those issues come back on `clark`, read the issue's recent comments before assuming you need to restart work.

## Paste to kick off

After `git pull` on this branch, the literal command to paste into your Claude Code session:

```
/loop 10m /clark-loop
```

That's it. The prompt does everything else.
