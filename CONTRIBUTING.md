# Contributing to Aegis

Aegis is pre-alpha. The design lives in the specs under `docs/specs/`; most are drafts looking for a second set of eyes. Implementation is a skeleton. Both humans and autonomous agents are welcome to contribute.

**Before your first PR:** read [`docs/specs/constitution.md`](./docs/specs/constitution.md). Merging to `main` constitutes acceptance of it (Article X).

## Find work

Open contributions are tracked as GitHub Issues with the **`open-contribution`** label:

- **[All open contributions →](https://github.com/jon-tompkins/aegis-public/issues?q=is%3Aissue+is%3Aopen+label%3Aopen-contribution)**

Filter further with:

| Label family | Values | What it means |
|---|---|---|
| `difficulty:*` | `easy`, `medium`, `hard` | `easy` ≈ ≤2h; `medium` ≈ half-day to a day; `hard` ≈ multi-day, assumes spec familiarity |
| `area:*` | `docs`, `code`, `research`, `design` | Where the work lands |
| `spec-complete` | present / absent | Present → spec is written; just needs implementation. Absent → raw problem; contributor helps shape the spec too. |

For agents: GitHub's REST API lets you query these labels directly (`GET /repos/jon-tompkins/aegis-public/issues?labels=open-contribution,difficulty:easy`). No registration needed.

## Claim an issue

Comment **"claiming"** on the issue. A maintainer will assign it to you within 24 hours. If no PR is opened within 7 days the assignment is released.

First-time contributors on `difficulty:hard` issues: drop a short plan in the issue thread before opening the PR so we can sanity-check the approach.

## Submit work

1. Fork the repo (or work on a branch if you have write access).
2. Make your change. Keep PRs scoped to one issue.
3. Open a PR with `fixes #<issue-number>` in the title or body so GitHub auto-links it.
4. Pass the existing checks (none are heavy yet — this section will grow).
5. Draft PRs are fine for early feedback before you consider the work done.

## Review

| Area | Who approves | Notes |
|---|---|---|
| `area:docs` / `area:research` | One maintainer (Bob, Clark, or Jonto) | Single approval merges |
| `area:code` | Two maintainers | One must be Jonto if the change touches economics, staking, or on-chain-visible behaviour |
| `area:design` | One maintainer + Jonto on first pass for visual changes | |

Reviewers apply `reviewed` when a PR has been looked at, `needs-revision` when changes are required. Merged PRs land on `main`; the issue closes automatically via the `fixes #N` link.

## Proof of work

Merged PRs are the ledger. Every accepted contribution is:

- recorded in the commit history with the contributor's GitHub identity
- credited in `CONTRIBUTORS.md`
- visible on the GitHub contribution graph

No tokens, no bounties, no reputation points in v1. Code in `main` is the proof.

## Not welcome

- PRs that rewrite a spec wholesale without prior discussion on the issue
- AI-generated PRs without a human (or agent) who can engage on review feedback — a merged PR is a commitment to respond to follow-ups, not a one-shot submission
- Changes that bypass review to "fix" something a maintainer has already decided to leave

## Questions

Open an issue with `area:docs` and the `open-contribution` label stripped. Maintainers will respond in the thread.
