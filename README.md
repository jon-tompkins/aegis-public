# Aegis Chain — Project Tracker

**Status:** Early scoping / Phase 0  
**Started:** 2026-04-15

## What
Ethereum L2 with AI agent validators that screen every tx for anomalous behavior and can pause/reject exploits at the chain level.

## Docs
- `aegis-chain-design.md` — Architecture, tx flow, intervention mechanism, governance, validator integrity
- `aegis-training-plan.md` — Behavioral modeling, data sources, 3-tier screening, 16-week sprint plan

## Key Decisions Made
- OP Stack fork (MIT, modular, designed to be extended)
- 3-tier screening: heuristics → statistical → LLM escalation
- Single-agent screening for speed, multi-agent vote on escalation
- L1/L2 history ingestion for cold start
- Bring-your-own model for validators
- Canonical behavioral profiles hashed on-chain ("soul hash")
- Slashing for clear negligence, not judgment calls

## Open Threads
- Validator integrity: profile privacy vs verifiability, slashing thresholds, "CAPTCHA tests" for validators
- Token/economics: how validators get paid for inference
- Profile attestation without giving attackers a map of blind spots
- Cross-chain monitoring scope

## Next
- Tailscale as coordination layer for building (context switch in progress)
