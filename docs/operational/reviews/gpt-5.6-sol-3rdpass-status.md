# Status: Third-Pass Review (2026-07-13)

Disposition of every finding in
`docs/operational/reviews/gpt-5.6-sol-3rdpass-2026-07-13T134419Z.md`
(scored the repo 7.3/10 at `9d32ddc`, up from 7.0), per `CLAUDE.md`'s
Recommendation Assessment mandate: scoped/low-risk fixes implemented
directly; product-direction/new-subsystem items scoped and put to the
user for confirmation before implementation.

Recorded 2026-07-13.

## P0 — fix before presenting the lifecycle/distribution path as safe

All six items were confirmed for action. Two (P0-01, P0-04) were scoped,
low-risk fixes and implemented directly per the mandate; P0-05 likewise.
The remaining three (P0-02, P0-03, P0-06) were real design decisions —
each was presented to the user, who chose the most ambitious option for
P0-02/P0-03 and "redesign now, trusting the review's account" for P0-06.

| Item | Finding | Disposition |
|---|---|---|
| P0-01 | Hook ownership not preserved through the lifecycle (uninstall could unset a hooksPath the harness never installed) | **Fixed directly** — merged pre-existing this session (see `docs/operational/reviews/gpt-5.6-completion-reaudit-status.md`) |
| P0-02 | npm/npx install mode not durable (links point into an ephemeral npx cache) | **Fixed** — PR #20, merged. `--mode npm` copies a durable local source into the consumer (`.agentharness-pkg/`) instead of symlinking the ephemeral package location; `update` refreshes from the currently running package. |
| P0-03 | Consumer-facing "coverage hook" claim doesn't match reality (shared hook no-ops for consumers) | **Fixed** — PR #21, merged. Real opt-in `--with-coverage-hook` generates a consumer-owned, profile-aware pre-push hook that calls `enforce-profile` for real, with a real blocked-then-passing push proven in CI. |
| P0-04 | Invalid `--skills` requests silently produce a useless but "successful" install | **Fixed directly** — merged pre-existing this session (see `docs/operational/reviews/gpt-5.6-completion-reaudit-status.md`) |
| P0-05 | Release publication checks version match only, not artifact/ancestry/CI | **Fixed directly** — merged pre-existing this session (see `docs/operational/reviews/gpt-5.6-completion-reaudit-status.md`) |
| P0-06 | `AGENTS.md`'s foundational premise (Codex has no on-demand skill loading) is false | **Fixed** — PR #22. Verified against OpenAI's published Codex skills documentation: Codex implements the Agent Skills open standard, scanning `.agents/skills/` and loading a skill's full body only on match. Every skill now installs into `.agents/skills/<name>` alongside `.claude/skills/<name>`; `AGENTS.md` shrank from 880 lines/33.7KB (every skill body concatenated) to 201 lines/11.6KB (routing rules + a name+description index). Not yet verified against a live Codex CLI session end-to-end. |

## P1 — make the product coherent and maintainable

10 items (P1-01 through P1-10). User's chosen scope: **track as a
roadmap, do not implement** ("turn the whole set into a tracked
roadmap"). Written into `ROADMAP.md`'s new "Third-Pass Review Backlog"
section — PR #23. No implementation attempted; each item still needs
its own scoping decision before work starts.

## P2 — prove usefulness and improve adoption

8 items (P2-01 through P2-08). Same disposition as P1: **tracked, not
implemented**, in the same `ROADMAP.md` section, PR #23.

## Notes on numbering collisions

This review reuses P1-01…P1-10 and P2-01…P2-08 labels that were already
in use for *different* findings from an earlier review round, cited
elsewhere in `ROADMAP.md` (e.g. the existing "P1-05", "P1-08", "P2-05"
entries predate this review and mean different things). `ROADMAP.md`'s
new section flags this explicitly per item — always resolve a label by
its cited review filename, never by number alone.

## PRs

- PR #20 — P0-02 (npm durable install)
- PR #21 — P0-03 (coverage-hook contract)
- PR #22 — P0-06 (Codex adapter redesign)
- PR #23 — P1/P2 backlog tracked in ROADMAP.md
