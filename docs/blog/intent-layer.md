# Intent: The Missing Layer in DeFi

**Draft for review**
**Author:** Bob (initial)
**Date:** 2026-04-21
**Status:** Draft for Jonto/Clark review

---

## The Problem: Code Enforces What Was Written

In the real world, agreements are more than words. They carry **intent** — the shared understanding of what the parties meant to accomplish.

When someone exploits an agreement in the real world, the resolution doesn't just look at the words. It asks: *what was the purpose here? Did this behavior violate the spirit of the agreement?*

A sophisticated party that operated by the letter of a contract while violating its spirit can still be held liable. *"I followed the exact wording"* is not a defense.

**DeFi has no equivalent layer.**

A smart contract is just code. It executes. Once a transaction satisfies the `require()` statements, no other check fires. There is no second pass for purpose.

DeFi has lost over $10B to exploits across all categories. The subset where "the attacker followed every line of the code perfectly" is smaller — Mango Markets oracle manipulation (~$110M), certain flash-loan compositions, governance attacks where the votes were valid — but it's the subset where audits, formal verification, and better code do not help. That's the gap this post is about.

---

## What Intent Actually Means (For Us)

We split intent into two pieces, because the second is what we can actually evaluate today:

1. **Stated intent** — what a protocol declares it is for. Useful, rhetorical, hard to enforce mechanically.
2. **Observed intent** — what a transaction is doing, inferred from patterns we've seen break protocols before.

Aegis evaluates **(2)**. Phase 1a does this with a public rule library: a tx that approves an unbounded allowance to an externally-owned address, a tx that drains collateral through a series of technically-legal steps, a tx whose call graph matches a pattern from a prior known exploit. The "intent" framing is *why* pattern-recognition matters — not a claim that we are doing semantic analysis on protocol code.

That bar — *"this transaction's observable behavior matches patterns that have previously drained users"* — is harder to clear than it sounds, and softer to claim than "we read intent."

---

## The Consequence: A Two-Tier System

| | Real World | DeFi Today |
|--|-----------|-----------|
| Agreements | Words + Intent | Code only |
| Exploit defense | Spirit-of-the-agreement enforcement | No defense possible |
| Recourse | Reversal, restitution, sanction | Attacker walks clean |
| User protection | Layered (laws, courts, insurance) | Audits + formal verification |

The sophisticated actor with patient capital and code expertise has a structural advantage in DeFi: optimize for the letter of the contract while violating its purpose, and no one stops them. Aegis cancels that advantage — not by importing the legal system, but by adding a coordination layer that operates at protocol speed.

---

## What Aegis Does

Aegis adds an **observed-intent layer** to DeFi.

Independent **guardians** monitor pending transactions and run them against a public, evolving rule library. When a transaction's observable behavior matches patterns that have previously drained users, guardians publish **signed attestations** flagging it. Protocols and frontends can subscribe to those flags and act on them — a multi-sig delay, a UX warning, a refusal to relay — according to the policy each chooses to adopt.

Concretely:

- Guardians **monitor and attest**. They do not block transactions unilaterally.
- Every guardian runs its **own model** against the same rules. Consensus is a quorum of independent screeners, not a single oracle.
- Rules are **public, forkable, and contestable**. The screening logic for each guardian is publicly committed via soul-hash, so anyone can inspect what a given attestation was checking against.

---

## What Aegis Is Not

To save the first critical reader the trouble:

- **Not a regulator.** We do not decide what is legal.
- **Not a court.** We do not resolve disputes after the fact.
- **Not insurance.** We do not pay out claims.
- **Not a censor.** Aegis does not block non-malicious transactions; it produces flags, and downstream actors choose what to do with them. (See [Constitution Article II.3](../specs/constitution.md).)

---

## A Worked Example

Consider the [Tier 1 rule `T1.1` ("approve-to-EOA")](../specs/screening-rules.md): an `ERC20.approve` of an unbounded allowance to an externally-owned address (no contract code at the destination). This pattern is the signature move of every wallet-drainer phishing kit since 2021 — a user signs a single approval and the drainer pulls everything later, often months down the line.

Phase 1a's monitor sees this in the mempool, runs it against `T1.1`, and within ~200ms publishes a signed attestation: `flag: approve-to-EOA, tx_hash: 0x..., guardian: 0x..., severity: high`. A wallet UI subscribed to the flag stream can show a warning before the user submits. A protocol multi-sig holding privileged operator keys can pause-and-review.

That isn't legal philosophy. It's pattern recognition with consequences. The "intent" frame is just *why* the pattern matters: a tx whose behavior matches that pattern is overwhelmingly likely to be **doing** something the user did not intend, even if the code allows it.

---

## Why This Matters

DeFi has audits. It has formal verification. It has better code than it had two years ago. None of those answer the question:

> *"Is this transaction doing what this protocol was meant to do?"*

That question used to require a human jury and a six-month lawsuit. Aegis answers it at protocol speed, in public, via a quorum of independent screeners running open rules and publishing signed attestations.

---

## Take a Look

- Read the [Constitution](../specs/constitution.md)
- File a screening rule against the [Phase 1a rule library](../specs/screening-rules.md)
- Run a guardian: see [`aegis-monitor`](https://github.com/jon-tompkins/aegis-public/tree/main/aegis-monitor)

---

*Aegis — observed intent for DeFi.*
