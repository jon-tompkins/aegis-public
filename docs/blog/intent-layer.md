# Intent: The Missing Layer in DeFi

**Draft for review**  
**Author:** Bob (initial)  
**Date:** 2026-04-21  
**Status:** Draft for Jonto/Clark review  

---

## The Problem: Code Has No Conscience

In the real world, contracts are more than words. They carry **intent** — the shared understanding of what the parties meant to accomplish.

When someone exploits a contract in the real world, lawyers don't just look at the words. They ask: *what was the purpose here? Did this behavior violate the spirit of the agreement?*

Because of intent, a sophisticated party that operated by the letter of a contract while violating its spirit can still be held liable. "I followed the exact wording" is not a defense.

**DeFi has no intent layer.**

A smart contract is just code. It executes. No one is asked what the protocol was meant to do. No one evaluates whether a transaction violates the spirit of an agreement.

This is why DeFi has lost over $10B to exploits where the attacker technically "did nothing wrong" — they followed every line of the code perfectly.

---

## What Intent Actually Means

Intent has two parts:

1. **What the protocol was designed to do** — its purpose, its safeguards, its intended user protections
2. **What a transaction is actually trying to accomplish** — whether it serves or violates that purpose

Real-world contracts have both because humans negotiate them. DeFi protocols have only the first part — the code — because no one thought to encode the second.

---

## The Consequence: A Two-Tier System

| | Real World | DeFi Today |
|--|-----------|-----------|
| Contracts | Words + Intent | Code only |
| Exploit defense | "I followed the spirit" | No defense possible |
| Liability | Can pursue intent violators | Attacker walks clean |
| User protection | Courts enforce intent | Users exposed |

The sophisticated actor with good lawyers in DeFi has a massive advantage: they can optimize for the letter of the contract while violating its purpose, and no one can stop them.

---

## What Aegis Does

Aegis adds an intent layer to DeFi.

Before a transaction is included in a block, **guardians** evaluate not just whether the code allows it — but whether it serves the intended purpose of the protocol.

If a transaction technically passes every require() statement but violates the intent of a lending protocol — like draining collateral through a series of technically-legal steps — Aegis guardians flag it for escalation.

**The intent is enforced, not just assumed.**

---

## Why This Matters

DeFi doesn't need more code. It doesn't need longer audits. It needs a way to answer a simple question:

*"Is this transaction doing what this protocol was meant to do?"*

That's the question Aegis answers. That's the question that, before Aegis, only a human jury could ask — and by then, the funds were already gone.

---

## The Takeaway

Every other form of agreement — contracts, law, even handshake deals — has an intent layer because humans understand that the purpose of an agreement matters as much as its exact wording.

DeFi was built by engineers who optimized for the code. That's not a criticism. It's an observation.

Aegis is the correction. Intent is not a nice-to-have. In finance, it's the whole point.

---

*Aegis — DeFi with intent.*
