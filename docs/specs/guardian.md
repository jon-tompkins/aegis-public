# Guardian Agents

**Status:** Draft / scoping (tracks [#11](https://github.com/jon-tompkins/aegis-public/issues/11))
**Phase:** 0 — design
**Related:** [`aegis-chain-design.md`](../../aegis-chain-design.md)

---

## Purpose

Scope whether Aegis needs a distinct **Guardian** role alongside consensus validators, and if so, define its interface and trust model.

**User framing:** *"Kind of like an RPC — something I opt into that monitors my address specifically and that I place some trust in. It can escalate to validators. It could have stake at stake. If the validators can manage everything, maybe not necessary — but it seemed like it would be efficient. We need to retain speed."*

## The core question

Do we need a Guardian layer at all?

| If validators can do it all | If Guardians are worth it |
|---|---|
| Simplest — one layer of AI screening | Offload personal-context checks from consensus |
| No extra trust assumptions to explain | Lower latency on the normal path |
| Easier economics | Opt-in premium security for users who want it |
| No risk of Guardian monoculture | Specialized per-user behavioral fit |

**Recommendation:** keep Guardians in the design as an optional, opt-in layer — but don't block testnet on them. Validators must cover the baseline; Guardians are additive.

## Two-layer model (if we keep Guardians)

```
┌──────────────────────────────────────┐
│ Validator set (chain-level)          │  Consensus screening.
│  - every tx, every validator         │  Protects the chain as a whole.
│  - staked, slashable, BYO model      │
└──────────────────────────────────────┘
                  ▲
                  │ escalations / signals
                  │
┌──────────────────────────────────────┐
│ Guardian (user-opt-in)               │  Personal behavioral fit.
│  - attached to a wallet / 4337 acct  │  Protects one user's assets.
│  - user chooses the provider         │
│  - optional stake (TBD)              │
└──────────────────────────────────────┘
```

Guardians screen **before** broadcast (or co-sign via 4337), so they can refuse txs the user themselves authorized but that look wrong.

## Relationship to validators

| Aspect | Validator | Guardian |
|---|---|---|
| Required | Yes (for consensus) | No (user opt-in) |
| Scope | Every tx | Only from/to this user's account |
| Stake | Yes, slashable | Optional (design choice) |
| Model | BYO, canonical profile | User-chosen, fully private |
| Authority | Pause / reject via vote | Refuses to co-sign |
| Trust model | N-of-M threshold | User's single (or chosen quorum) |

## Integration pattern

Cleanest path: **EIP-4337 smart account + Guardian module**. Guardian signs UserOps before bundling. Policies:

- **Required signer:** Guardian + user both sign.
- **Threshold:** Guardian can solo-authorize up to a value cap.
- **Revocation:** user can replace / remove Guardian at any time (with an optional on-chain timelock for safety against Guardian capture).

## Speed considerations

User constraint: "we need to retain speed."

- Guardian sits on the client → bundler path, off the hot chain-consensus path. Validators' <100ms budget is unaffected.
- Guardian response budget: **~50ms on the user's own connection**. Miss → fallback to user-only signature (configurable).
- Local Guardian (runs on user's device / wallet extension) is the default; remote Guardians are opt-in with latency trade-offs disclosed.

## Opt-in UX

- Wallet toggle: "Add a Guardian."
- Directory of Guardian services, plus self-host option.
- Risk tolerance preset (conservative / balanced / permissive).
- Guardian sees tx + its own private profile of the user's normal behavior.

## Capture resistance

| Risk | Mitigation |
|---|---|
| Single Guardian goes rogue / censors | Always-revocable; timeout fallback to user-only |
| Provider correlates users' tx patterns | Default to local or TEE deployment; open-source reference |
| Guardians become *de facto* centralization | Directory, no protocol preference, self-host encouraged |
| Guardian colludes with validators to front-run | Explicit anti-MEV clause in Guardian spec; reputation + economic penalty **outside** consensus |

## Stake — optional path

If we add optional stake:
- Guardian posts a small bond (native or restaked ETH).
- Slashed if they approve a tx that the validator set later confirms as exploit-of-the-user (e.g. drain, unauthorized approval).
- Not slashable on judgment calls.
- Lets users pick Guardians with skin in the game, and lets Guardians price their service.

Default: **no stake for v0**, revisit after real usage data.

## Acceptance criteria

- [ ] This spec + decision: ship or defer
- [ ] Reference EIP-4337 Guardian module contract (skeleton)
- [ ] Reference Guardian client reusing Tier 1/2 primitives from [training-pipeline.md](./training-pipeline.md)
- [ ] UX flow doc for opt-in / revoke
- [ ] Threat model including collusion / capture risks
- [ ] Explicit statement of what Guardians *cannot* do (no override of chain-level pause, no force on validator decisions)

## Open questions

- On-chain attestation of Guardian screening — needed for disputes, or stay fully off-chain?
- Can a Guardian share signals with validators (*"this user says this tx is legit, weight lower"*)? Privacy vs. UX trade-off.
- Marketplace/directory — protocol-run or third-party?
- Per-protocol recommended Guardian configs (lending protocol → recommended Guardian policy) — in or out of scope?
