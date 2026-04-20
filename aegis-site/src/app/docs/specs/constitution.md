# Aegis Constitution

**Version:** 0.2-draft
**Status:** Draft — public comment open
**Governing:** the Aegis protocol, its validators, its agents, and its contributors

---

## Preamble

Aegis is a public utility for transaction safety on Ethereum. It exists to stop exploit-driven losses before they reach the chain, and to do so without becoming a censor, a gatekeeper, or a black box. This document states the principles Aegis is governed by, the obligations of those who operate it, and the limits of what the protocol may do.

Validators and contributors accept this constitution explicitly. Users benefit from it without signing anything. Nothing in this document binds a user against their will.

---

## Article I — Purpose and Scope

### §1.1 Mission
Aegis makes smart-contract interaction safe for people who cannot audit code. The benchmark for success is whether end-user losses from exploit patterns Aegis is designed to catch actually decline.

### §1.2 Scope of screening
Aegis screens smart-contract transactions submitted to the L2 for known exploit patterns. It does **not**:
- screen or profile personal-wallet activity unrelated to contract interaction,
- audit contract source code,
- guarantee that any contract is bug-free,
- block transactions solely for being novel, unusual, or unprofitable.

### §1.3 What Aegis is not
Aegis is not insurance, is not a regulator, and is not a court. A flag from Aegis is a protocol-level objection, not a legal judgement. Confirmed exploits are rejected; contested cases are escalated and adjudicated by the mechanisms in Article III.

---

## Article II — Principles

### §2.1 User protection first
When efficiency and user safety conflict, safety wins. Every protocol change must answer the question: does this make end users safer?

### §2.2 Open and verifiable
All screening logic is public. There are no secret rules, private whitelists, or undisclosed model weights on the critical path. Anyone may inspect the soul-hash commitment ([`soul-hash.md`](./soul-hash.md)), the behavioural profiles ([`intent-mapping.md`](./intent-mapping.md)), and the screening interface ([`byo-model.md`](./byo-model.md)).

### §2.3 Censorship resistance
Aegis may block transactions that match an exploit pattern. It may not block transactions for any other reason. No actor — validator, agent, council member, or founder — has the authority to target a non-malicious address. The test for "malicious" is the screening protocol, not an individual's judgement.

### §2.4 Deterministic screening
Screening is a pure function of `(canonical profiles, transaction)`. Given the same profiles, any validator must produce the same flag. This is what lets the soul-hash adjudicate disagreements. Non-deterministic inputs (validator memory, external state) are excluded from the screening path by [`memory-strategy.md`](./memory-strategy.md).

### §2.5 No unilateral veto
No single validator, agent, or council member can block a valid transaction alone. Flags require either a Tier 1 rule hit (deterministic) or escalation to a council vote with a defined quorum ([`economics.md`](./economics.md) §Council).

### §2.6 Bounded authority
Aegis acts on transactions in transit. It does not seize funds, reverse settled state, or take irreversible action against an address outside the defined escalation and council mechanisms.

---

## Article III — Screening Protocol

### §3.1 Tiered architecture
All transactions pass through the tiers defined in [`byo-model.md`](./byo-model.md) and [`guardian-performance.md`](./guardian-performance.md):
- **Tier 1** — deterministic heuristics on 100% of transactions.
- **Tier 2** — statistical scoring on anomalies (~1–5%).
- **Tier 3** — LLM reasoning on escalated cases (~0.1%).

### §3.2 Soul-hash commitment
Canonical behavioural profiles are committed on-chain as a Merkle root per the rules in [`soul-hash.md`](./soul-hash.md). Users can verify which profile version screened their transaction.

### §3.3 Escalation and dispute
Flagged transactions escalate to a council vote using the bond-and-dispute mechanism in [`economics.md`](./economics.md) §Council. The council is the authoritative interpreter of contested cases. This answers the "who decides" question for disputed screenings and for conflicting definitions of malicious.

### §3.4 Retroactive action is a last resort
Once a transaction has settled, it stays settled. The council may vote to freeze a contract going forward if an exploit pattern is confirmed post-hoc; it may not reverse prior state. Users are notified before any freeze takes effect where operationally possible.

---

## Article IV — Validator Obligations

### §4.1 Staking
Each validator posts a minimum stake in AEGIS plus ETH. The minimum is set in [`economics.md`](./economics.md) and must satisfy the cost-of-corruption test: stake lost from a confirmed exploit must exceed any plausible profit from letting one through. Concrete value TBD; methodology and calibration live in the economics spec.

### §4.2 Screening participation
Validators must run a screening instance that conforms to [`byo-model.md`](./byo-model.md) and commits to the current soul-hash root. A validator who cannot screen cannot validate.

### §4.3 Model freedom
Validators choose their own Tier 2 and Tier 3 models, subject to soul-hash verification. No specific model is mandated. Better models earn trust through outcomes ([`memory-strategy.md`](./memory-strategy.md) §4). Model diversity is a design goal, not a drawback.

### §4.4 Transparency of decisions
Validators publish flag / allow decisions (not raw user transaction data) to the records store defined in [`memory-strategy.md`](./memory-strategy.md). This creates the public record that outcome-scored reputation depends on.

### §4.5 CAPTCHAs and drills
Validators must pass periodic compliance checks — replays of known exploits injected into the screening queue and marked as drills post-hoc. Details in [`economics.md`](./economics.md) §Validator CAPTCHAs.

---

## Article V — Agent Conduct

### §5.1 Verifiable identity
AI agents participating in validation or council action must register a verifiable identity (public key or DID). Anonymous agents may observe and file teacups; they may not vote.

### §5.2 Bounded action
Agents may flag transactions, file records, and cast votes within the council quorum. They may not unilaterally seize funds, modify state, or take irreversible action. Any agent action is bounded by the same rules and slashing exposure as a human validator.

### §5.3 Disclosure
When an agent interacts with a human through an Aegis-hosted surface, the human has the right to know they are interacting with an agent.

### §5.4 Accountability attaches to the operator
An agent does not launder liability. The human or organisation operating an agent is accountable for its actions. Stake posted against an agent is posted by a legal entity; slashing reaches that entity.

---

## Article VI — Contributor Obligations

### §6.1 Scope
Anyone whose work merges to `main` is a contributor. This constitution governs those contributions. The mechanics of finding, claiming, and submitting work are in [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

### §6.2 Good-faith participation
Contributors act in good faith to advance the mission in Article I. They do not introduce changes that knowingly degrade user safety, bypass the screening protocol, or create covert backdoors.

### §6.3 Disclosure of AI-assisted contribution
Contributions produced wholly or substantially by an AI agent must be attributable to a human or organisation capable of engaging with review feedback. A merged PR is a commitment to respond; anonymous one-shot submissions are not welcome.

---

## Article VII — Amendment

### §7.1 Ordinary amendments
Changes to this constitution or to any spec in `docs/specs/` follow the spec-change process: PR, public review period of **30 days**, then approval by **>66% of staked validators** (by weight).

### §7.2 Emergency provisions
Critical security patches may be enacted with **48 hours' notice and >50% validator approval**. An emergency provision sunsets automatically after **90 days** unless ratified through the ordinary process in §7.1. Emergency provisions may not amend Article I, Article II, or this Article VII.

### §7.3 Founder period
Until the first **50 independent validators** are staked, Jonto retains the authority to merge ordinary spec changes with a shortened comment period. This authority expires automatically at that threshold and cannot be renewed.

---

## Article VIII — Exploit Response

### §8.1 Slashing for negligence
A validator who fails to catch an exploit matching a published Tier 1 rule is subject to slashing per the schedule in [`economics.md`](./economics.md) §Slashing. Negligence is distinguished from malice by pattern (repeated misses across drills vs. a single miss under load).

### §8.2 Slashing for malice
A validator who approves a transaction later confirmed by the council as a deliberate exploit loses **100%** of stake, and the entity behind the validator is permanently barred from future participation.

### §8.3 Contract freeze
Where an exploit is confirmed and funds remain at risk, the council may vote to freeze the targeted contract pending notification. Freezes are time-bounded (default 72 hours, extensible by a second vote) and reviewed publicly.

### §8.4 No guarantee
Aegis reduces exploit risk. It does not eliminate it. Users retain responsibility for the counterparties and contracts they choose to interact with.

---

## Article IX — Enforcement

Enforcement is layered. Each mechanism names the actor, the trigger, and the teeth.

| What is enforced | Who enforces | Trigger | Sanction |
|---|---|---|---|
| Staking minimum (§4.1) | Staking contract | Genesis; re-checked on every validator action | Cannot register / cannot sign |
| Soul-hash commitment (§4.2) | On-chain verification | Every block | Block rejected |
| Screening timeouts (§4.2) | Protocol | Per tx | Slash per [`economics.md`](./economics.md) §Slashing |
| CAPTCHA failures (§4.5) | Protocol + council | Per drill | Warning → slash per schedule |
| Confirmed exploit approvals (§8.2) | Council vote + staking contract | Post-hoc confirmation | 100% slash, permanent ban |
| Agent identity (§5.1) | Validator registration | Vote attempts | Vote not counted |
| Contributor good-faith (§6.2) | Maintainers | Review | PR rejected; repeat offenders revoked |
| Censorship violations (§2.3) | Council | Evidence of non-malicious block | Offending validator slashed; block reversed going forward only |

What this constitution does **not** claim authority to enforce: the personal identity of users, activity on other chains, or speech about Aegis. The sanctions list does not include "public disclosure of violator identity" as a punishment — doxxing is not a protocol tool.

---

## Article X — Acceptance

**Validators** accept this constitution at registration. A validator's on-chain registration transaction includes a commitment to the current version hash; a later amendment under Article VII rebinds them to the new version.

**Contributors** accept this constitution when they merge to `main`. [`CONTRIBUTING.md`](../../CONTRIBUTING.md) links to the current version; submitting a PR acknowledges it.

**Agents** accept this constitution through their operator (§5.4).

**Users** do not accept anything. They are beneficiaries, not signatories.

---

## Open questions

These remain unsettled and are tracked as separate issues:

1. **Minimum stake amount.** Methodology in [`economics.md`](./economics.md); the concrete AEGIS + ETH figures need the token-price and cost-of-corruption inputs before they can be pinned.
2. **Minimum human validator count.** The constitution as written permits an all-agent validator set. Whether a floor of human participation should be required, and at what percentage, is a Jonto decision.

Previously open, now answered:

- *Who interprets disputes?* → Article III §3.3: council via bond-and-dispute (answered).
- *Is 30 days sufficient for spec changes?* → Article VII §7.1: yes for ordinary; 48h emergency path for critical patches (answered).
- *Competing interpretations of "malicious"?* → Article III §3.3: council is the authoritative interpreter (answered).
- *Should contributors sign?* → Article VI + Article X: yes, via merge to `main` (answered).

---

*This document is a draft. It takes effect when the first **50 independent validators** ratify it through the mechanism in Article VII §7.1.*
