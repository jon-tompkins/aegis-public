# Aegis Constitution — Founding Document

**Version:** 0.1-draft  
**Author:** Bob (initial sketch)  
**Date:** 2026-04-20  
**Status:** Draft — for community review  

---

## Preamble

Aegis is a Layer 2 blockchain designed to protect users from exploit-driven losses. This document establishes the principles, rules, and conditions that govern Aegis and all who participate in it — human validators, AI agents, and end users.

By participating in Aegis, you agree to this constitution.

---

## Article I — Purpose

**Section 1.1 — Mission**  
Aegis exists to make decentralized finance safe for everyone. Not just technically secure — actually safe for users who lack the expertise to evaluate smart contract risk.

**Section 1.2 — The Core Problem**  
DeFi has lost over $10B to exploits since 2020. The victims are almost always end users — not sophisticated actors. Aegis exists to change that outcome.

**Section 1.3 — Scope**  
Aegis screens transactions before they reach the chain. It does not audit code. It does not guarantee contracts are bug-free. It detects and blocks malicious transaction patterns in real-time.

---

## Article II — Core Principles

**Section 2.1 — User Protection First**  
When protocol efficiency conflicts with user safety, user safety wins. Every design decision must answer: does this make users safer?

**Section 2.2 — Open and Verifiable**  
All screening logic is public. There are no secret rules, no backdoors, no hidden whitelists. Anyone can inspect, challenge, and fork the guardian logic.

**Section 2.3 — Censorship Resistance**  
Aegis may block malicious transactions. It may not block non-malicious transactions. The guardian system is a shield, not a weapon.

**Section 2.4 — Deterministic Screening**  
Screening decisions must be reproducible and deterministic. Two guardians watching the same transaction must reach the same conclusion. Non-determinism in screening breaks user trust and auditability.

**Section 2.5 — Minimal Veto Power**  
No single actor — human or agent — can unilaterally block a valid transaction. Escalation requires consensus or near-consensus among the guardian set.

---

## Article III — The Screening Protocol

**Section 3.1 — Tiered Architecture**  
All transactions pass through a tiered screening system:
- Tier 1: Deterministic heuristic rules (CPU, <1ms)
- Tier 2: Statistical model scoring (GPU, 30-50ms)
- Tier 3: Full LLM reasoning on escalated cases (<2s)

**Section 3.2 — Soul Hash Commitment**  
Guardian screening models are committed to a profile root (soul hash) stored on-chain. Users can verify which model version screened their transaction and audit its behavior.

**Section 3.3 — Escalation Path**  
Disputed decisions escalate to a guardian council vote. Council members are staked validators. The escalation threshold and vote mechanics are defined in the Economics spec.

**Section 3.4 — No Personal Wallet Screening**  
Aegis does not screen end-user personal wallets — only smart contract interactions submitted to the L2. Personal wallet activity is out of scope.

---

## Article IV — Validator Requirements

**Section 4.1 — Staking**  
Validators must stake a minimum amount (defined in the Economics spec) to participate. Stakes are slashable for malicious or negligent behavior.

**Section 4.2 — Screening Participation**  
Validators must run a guardian instance and participate in the screening protocol. Validators may run their own inference infrastructure or delegate to a trusted screening service.

**Section 4.3 — Model Freedom**  
Validators may choose their own screening model, subject to soul hash verification. No specific model is mandated. Better models earn trust; worse models lose stake.

**Section 4.4 — Transparency**  
Validators must publish their screening decisions (not user tx data — only flag/allow decisions). This creates a public record of guardian quality.

---

## Article V — Agent Conduct

**Section 5.1 — Identity and Accountability**  
AI agents operating on Aegis must be registered with a verifiable identity (public key or DID). Anonymous agents cannot participate in guardian consensus.

**Section 5.2 — No Automated Violence**  
Agents may flag and block transactions. They may not unilaterally seize funds, modify state, or take irreversible action without human validator confirmation for flagged cases.

**Section 5.3 — Disclosure**  
Agents must disclose when they are AI. End users interacting with AI agents on Aegis have a right to know.

---

## Article VI — Upgrade and Amendment

**Section 6.1 — Spec Versioning**  
All protocol specifications are versioned in `docs/specs/` on the public GitHub repo. Changes to screening logic require a spec update + public comment period.

**Section 6.2 — Hard Forks**  
Material changes to the screening protocol require a 30-day public comment period and approval by >66% of staked validators.

**Section 6.3 — Emergency Changes**  
Critical security patches may be fast-tracked with 48-hour notice + >50% validator approval. Emergency provisions expire after 90 days if not ratified.

---

## Article VII — Exploit Response

**Section 7.1 — Slashing**  
Validators who fail to screen known exploit patterns (where a Tier 1 rule exists) are slashable. Negligence vs malice is distinguished by intent.

**Section 7.2 — Retroactive Blocking**  
If an exploit is detected after the fact, the guardian set may vote to freeze affected contracts pending user notification. This is a last resort, not a standard tool.

**Section 7.3 — No Guarantee**  
Aegis reduces exploit risk. It does not eliminate it. Users must still exercise judgment. Aegis is not insurance.

---

## Article VIII — Participation Agreement

**By participating in Aegis — as a validator, contributor, agent, or user — you agree to:**

1. Operate in good faith to protect end users
2. Publish your screening decisions transparently
3. Accept slashing for negligent or malicious behavior
4. Follow the escalation protocol for disputed decisions
5. Disclose AI identity when acting as an agent
6. Accept that Aegis is a tool, not a guarantee

**Violations of this constitution may result in:**  
- Slashing of stake  
- Removal from the guardian set  
- Permanent ban from participation  
- Public disclosure of violator identity

---

## Open Questions for Review

1. Who has authority to interpret disputes? (Guardian council? Arbitration? On-chain governance?)
2. What is the minimum stake for Article IV participation?
3. Is the 30-day comment period for spec changes sufficient?
4. Should there be a minimum human validator count, or can AI-only guardian sets exist?
5. What happens when two competing interpretations of "malicious" conflict?

---

*This document is a draft. Signatories are not bound until a ratified version is approved by the founding guardian set.*
