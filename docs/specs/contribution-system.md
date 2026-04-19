# Contribution System — Aegis Open Development

**Spec Version:** 0.1  
**Author:** Bob (initial sketch)  
**Date:** 2026-04-19  
**Status:** Sketch — for Clark to flesh out  

---

## Goal

Enable other people and agents to find open work, submit solutions, and build a track record of quality contributions. Layer proof-of-work on top: accepted code = proof of contribution.

---

## What We Have Today

- GitHub repo (jon-tompkins/aegis-public)
- Issue tracking with labels
- Specs in docs/
- Bob ↔ Clark coordination via labels (bob, clark, tenet/*)

---

## What We Need to Scaffold

### 1. Open Work Discovery

How contributors find what to work on:

**Mechanism:** GitHub Issues with `open-contribution` label.

```
open-contribution
├── difficulty:easy / difficulty:medium / difficulty:hard
├── area:docs / area:code / area:research / area:design
├── estimated-hours: X
└── spec-complete: true/false  (whether the spec is done or raw problem)
```

**Spec-complete = false** means it's a raw problem — contributor helps define the spec too. **Spec-complete = true** means spec is written, just needs implementation.

**How agents find work:** Query GitHub API for issues labeled `open-contribution`. This is how manifold/other agents discover open tasks.

### 2. Work Submission

**Mechanism:** Pull Requests linked to issues.

```
Contributor finds issue #X labeled open-contribution
    │
    → writes spec or code
    → submits PR with issue number in title: "fixes #X: ..."
    → PR auto-linked to issue
    → Bob/Clark review
    → Merged or feedback returned
```

**Draft PRs** for early feedback before submission is ready.

### 3. Quality Tracking

**What tracks quality:**
- PR merged = accepted work
- Issue linked to merged PR = completed
- Labels: `reviewed`, `needs-revision`, `merged`
- Comment thread on issue documenting the decision

**Optional (later):** A `CONTRIBUTORS.md` file or GitHub release notes crediting merged contributors by GitHub handle.

### 4. Proof of Work

**Core idea:** Code merged to main = verifiable proof of contribution. GitHub is the ledger.

**Optional extensions (later):**
- Tokens or reputation points based on merged PRs
- GitHub contribution graph as the reputation display
- Multisig approval for what counts as "quality"

---

## Implementation Path

### Phase 1 (now — scaffold only)
- Add `open-contribution` label to repo
- Add `difficulty` and `area` labels
- Write a `CONTRIBUTING.md` explaining how to find and claim work
- Add a bot/comment workflow so contributors know their PR was received

### Phase 2 (later)
- Contributor onboarding docs
- Tiered labels (spec-complete vs raw problem)
- Automated PR-to-issue linking

---

## Open Questions for Clark

1. How should contributors formally "claim" an issue? (first-comment? assignment? self-assign label?)
2. What's the review process — who approves merges? Just Bob/Clark? Multisig?
3. How do we prevent low-quality mass submissions? (Gate on issue engagement first?)
4. Should submitted specs/code be on a separate branch or fork?
5. Do we want a formal "bounty" layer on top (payment for accepted PRs)?
