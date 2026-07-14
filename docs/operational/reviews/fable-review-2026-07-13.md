---
title: "agentharness full repository review (Fable)"
reviewed_at: "2026-07-13"
reviewer: "Claude Fable 5"
repository_commit: "4f3e94b"
working_tree: "dirty — uncommitted CLAUDE.md table reformat + untracked docs/gpt-5.6-sol-4th-2026-07-14T021052Z.md"
previous_fable_review: "docs/operational/reviews/fable-review.md (2026-07-11)"
concurrent_review: "docs/gpt-5.6-sol-4th-2026-07-14T021052Z.md (same commit, independent)"
---

# agentharness — full repository review (idea, docs, implementation, usefulness)

## Executive verdict

**Overall: 7.2/10.** The idea is strong and the engineering culture around it
is unusually good — but the repo is now generating its own gravity: five full
review cycles in three days, a red self-verification gate at HEAD, three
confirmed destructive/unsafe installer boundaries, and one safety-relevant
policy contradiction that ships to every consumer. Meanwhile the two things
that would actually prove the product — a real dogfood project and a live
non-Claude session — still don't exist.

The single most important sentence in this review: **stop producing internal
evidence (reviews, adapters, generators) and start producing external evidence
(dogfood, live tests, eval runs).** The repo has reached the point where every
additional file makes the unproven surface larger, not the product better.

Everything below was verified directly against the tree at `4f3e94b` — see
the verification record at the end. Where a finding overlaps the concurrent
GPT-5.6 fourth-pass review, that's noted; I independently confirmed its four
P0s before repeating them, and found two significant items it missed (F-02,
F-07).

## Scorecard

| Dimension | Score | Why |
|---|---:|---|
| Idea / product thesis | 8.5 | One source of truth for agent-facing policy, referenced not copied, is a real and growing problem. Rigor tiers and opt-in publish authority are genuinely distinctive policy design. |
| Documentation structure | 8.0 | Router → manifest → status/limitations → decisions layering is excellent. DECISIONS.md is the best file in the repo. |
| Documentation correctness | 6.0 | Confirmed contradictions in STATUS, KNOWN_LIMITATIONS, CLIENT_COMPATIBILITY legend, profiles README, and one *skill that contradicts the trust model itself* (F-02). |
| Implementation | 7.5 | The lifecycle CLI, state file, generators, and profile enforcement are real engineering. Marred by the three unsafe boundaries (F-03/F-04/F-05). |
| Tests & CI | 8.0 | Behavioral bats tests, drift checks, hermetic fixtures — rare quality for a policy repo. But the committed tree fails its own gate (F-01). |
| Safety / reversibility | 6.0 | Consumer-file overwrite, secret-copying npm path, non-restoring forced hook install. All confirmed in code. |
| Usefulness today | 7.5 | Genuinely useful now for a careful Claude Code adopter. Multi-client value is structural, not demonstrated. |
| Evidence & adoption | 3.0 | Zero dogfood projects, zero live non-Claude sessions, zero eval runs. The weakest dimension by far, and the one no amount of code fixes. |

## The idea

The thesis holds up: per-project `CLAUDE.md` files drift, and a referenced
single source of truth fixes a real failure mode. Two design choices stand
out as better than the ecosystem baseline and worth protecting:

1. **Rigor tiers** (`CODING_GUIDELINES.md#rigor-tiers`) — acknowledging that
   uniform mandates teach agents to discount all mandates is sophisticated
   policy design, and the tier → YAML profile → mechanical `enforce-profile`
   pipeline makes it more than prose.
2. **Opt-in publish authority** (`.agentharness-publish-mode`, DECISIONS.md
   B1) — defaulting agents to verify-and-stage with explicit escalation is
   the right trust model, arrived at deliberately and documented well.

These two are the differentiators. Notably, they are exactly what the
planned instruction-quality evals (ROADMAP P2-03) would measure — which is
another reason those evals matter more than any further breadth.

The risk to the idea isn't correctness, it's **weight**: the value
proposition is "adopt this and stop thinking about conventions," but the
repo currently asks an adopter to trust an 8-platform compatibility claim,
a 4-mode installer, and a 26,500-line tree of which no line has been
exercised by anyone but its author. A smaller, proven kit would sell the
idea better than a larger, asserted one.

## Documentation

**What's good:** the layering (CLAUDE.md router → MANIFEST → STATUS /
KNOWN_LIMITATIONS → DECISIONS → dated reviews) is the right architecture,
and the honesty norms ("don't trust a directory tree in prose", every
generated file carrying its own not-live-tested caveat) are exemplary.
DECISIONS.md in particular — compact, retroactive, with status and
consequences — should be the template other repos copy.

**What's broken:** the hand-maintained summary layer has drifted from the
implementation again, days after P1-03 fixed the previous four
contradictions. Confirmed this pass:

- `docs/STATUS.md` says 6 skills; 7 exist (`port-agent-config` missing).
- `docs/STATUS.md` and `docs/KNOWN_LIMITATIONS.md` both state profile
  enforcement is "not wired into the pre-push hook"; `init
  --with-coverage-hook` (implemented, help-documented, state-tracked in
  `harness-link.sh`) generates exactly that hook. `patterns/profiles/README.md`
  doesn't mention it either.
- `docs/CLIENT_COMPATIBILITY.md` defines ✅ as "built and dogfooded in this
  repo" then uses ✅ for six adapters its own intro says are not dogfooded.
- `docs/ARCHITECTURE.md` remains largely aspirational template prose
  (metadata/complexity frontmatter "in every component", tools "add to
  PATH", README "in every directory" — none current), thinly covered by its
  disclaimer. It's the one top-level doc that reads generated rather than
  maintained.
- `.claude/skills/committing/SKILL.md` — see F-02 below; this one is a
  safety contradiction, not just a stale count.

The structural lesson: every contradiction above lives in a hand-written
summary of a machine-checkable fact. The repo already knows the fix — it
generated MANIFEST.md from `manifest.yaml` for exactly this reason — and
should extend that pattern to counts and capability claims rather than
scheduling another manual sweep.

## Implementation

`harness-link.sh` (~1,800 lines) is a real lifecycle CLI with state,
doctor/audit, four install modes, and profile enforcement; the test suite
around it (state transitions, hermetic remotes, push-rejection acceptance
tests) is genuinely strong. Three boundaries are unsafe, all verified by
code inspection this pass:

- `cmd_generate_clients` (line 1668) writes `AGENTS.md`, `GEMINI.md`,
  Copilot/Cursor/Kilo files straight into the target with no existence
  check, no backup, no `--force`, no state record.
- `copy_npm_durable_source` (line 323) tars **everything** in the source
  except `.git` and its own destination — a `--mode npm` init from a git
  checkout copies untracked files, including `.env`, into the consumer's
  `.agentharness-pkg`. The safety assumption (npm's `files` allowlist
  pruned the source) lives in a comment, not in code.
- Forced hook install records only the installed `hooks_path`; the
  pre-existing value is never persisted, so uninstall unsets rather than
  restores it.

And the gate is red: `tools/check.sh --offline` exits 1 at HEAD because
committed `AGENTS.md` (and per the bats suite, `GEMINI.md` and the Kilo
router) no longer match their generators after commit `4f3e94b` edited
`CLAUDE.md`. The uncommitted working-tree change (another `CLAUDE.md`
reformat) will re-create the same drift the moment it's committed. Two
consecutive `CLAUDE.md` edits missing the regeneration step is not a
discipline failure, it's a missing automation.

## Usefulness

For its stated first user — one person running several projects through
Claude Code — the harness is useful **today**: the skills are crisp and
actionable, the rigor tiers prevent over-mandating, install/uninstall is
reversible and tested, and the trunk-protection and coverage hooks do real
work. I'd caution a second adopter on exactly two things: don't run
`generate-clients` against a repo with existing instruction files (F-03),
and don't use `--mode npm` from a checkout containing secrets (F-04).

For the broader claim — a portable 8-platform policy kit — usefulness is
unproven and currently unprovable from inside this repo. That's not a
criticism of the code; it's a statement about what kind of work is left.

## Itemized actions

Ordered by what I'd do first. `[=GPT P0-xx]` marks overlap with the
concurrent fourth-pass review so dispositions can be merged; F-02 and F-07
are new findings of this review.

### Fix now (P0)

- **F-01 — Make the gate green and keep it green mechanically.**
  Regenerate `AGENTS.md`, `GEMINI.md`, `.kilo/rules/agentharness.md`;
  decide the uncommitted `CLAUDE.md` table reformat (commit it *with*
  regenerated adapters, or discard it — it's cosmetic and currently just
  pending drift). Then automate: either a pre-commit hook that regenerates
  adapters when `CLAUDE.md`/skills change, a `check.sh --fix` mode, or —
  worth genuine consideration — stop committing generated adapters at the
  repo root entirely and generate them only into consumers, which deletes
  this drift class instead of policing it. [=GPT P0-04, plus automation]
- **F-02 — Fix the `committing` skill's publish contradiction.** The skill
  body says "commit → push → PR. Don't stop at the commit" and "work is not
  done until the PR exists"; its frontmatter description repeats the
  mandate into every platform's always-on skill index. This directly
  contradicts the B1 decision (verify-and-stage default, publish gated on
  authority) that CLAUDE.md and COMMITTING_GUIDELINES.md already reflect —
  and unlike the other doc drift, this one instructs consumer agents to
  take an outward-facing action they may not be authorized to take, on all
  8 platforms. Fix body + description, regenerate `.cursor/rules/`, and add
  the publish-workflow claim to the semantic-contradiction checks P1-03
  proposed (the numeric detector can't see this class).
- **F-03 — Make `generate-clients` non-destructive.** Refuse when a target
  exists and isn't recognizably harness-generated; add `--force` and
  `--dry-run`; record generated paths+hashes in state so doctor/uninstall
  can manage them. [=GPT P0-01]
- **F-04 — Allowlist the npm durable copy.** Copy from an explicit
  manifest (or refuse `--mode npm` when the source isn't a packed
  artifact); always exclude `.env*`, VCS metadata, caches. A security
  boundary must not live in a comment about the caller. [=GPT P0-03]
- **F-05 — Persist and restore the pre-existing hooks path** across
  `--force` install → uninstall, including the "previously unset" case.
  [=GPT P0-02]

### Do next (P1)

- **F-06 — Fix the confirmed doc contradictions, then generate the facts.**
  The five items in the Documentation section above, by hand, in one PR;
  then extend the `manifest.yaml` pattern so counts (skills, languages,
  patterns) and capability rows (enforcement, hooks, clients) are rendered
  from structured data with a CI drift check, and adopt an explicit status
  vocabulary — `built` / `structurally tested` / `live-tested` — so the ✅
  legend can't mean two things again. [overlaps GPT P1-04]
- **F-07 — Cap the review loop.** This is the fifth full review in three
  days; `docs/operational/reviews/` holds 11 files / 220 KB, ROADMAP
  carries three colliding P1-xx/P2-xx numbering schemes that it must
  itself warn readers about, and this file is — knowingly — adding to the
  pile. Concretely: (a) archive completed cycles under a dated directory,
  (b) keep ONE live backlog with globally unique IDs (date-prefixed, e.g.
  `R260713-01`) instead of per-review P-numbers, (c) adopt a standing rule:
  **no new full review until the previous review's P0s are closed and at
  least one external-evidence item (dogfood run, live client test, eval
  run) has landed.** Review #6 has almost nothing left to find that #4 and
  #5 didn't; the marginal information is now in the field, not the tree.
- **F-08 — Produce external evidence (the highest-value item on this
  list).** In order of information-per-hour: (1) run the existing
  `docs/operational/planning/DOGFOODING.md` plan against one real
  non-fixture repo; (2) one live Codex CLI session against a consumer
  install — it validates or falsifies the entire `.agents/skills/` design
  in an afternoon; (3) one funded baseline/treatment eval run through the
  already-built runner. Until at least one of these exists, treat every
  feature addition as speculative inventory. [=GPT P1-02/P1-03]
- **F-09 — Put the always-on context on a budget.** `CLAUDE.md` is 181
  lines of which well over half is the workflow-completion/CI mandate —
  procedural mechanics (`gh` invocations, retry counts, poll commands)
  that belong in an on-demand skill, not in every session's context, and
  that get ported verbatim into adapters for platforms that may lack `gh`
  entirely. Keep always-on to routing, invariants, and authority rules;
  add a measured token budget per adapter to CI. [overlaps GPT P1-10]
- **F-10 — Rewrite ARCHITECTURE.md down to reality.** Keep the layering
  diagram and the actually-true principles; delete the aspirational
  component templates and metrics sections; link DECISIONS.md for the
  "why". It's the only top-level doc whose quality is below the repo's
  bar, and it's the first "philosophy" doc a new reader opens.
- **F-11 — File and disposition the fourth-pass GPT review.** It's
  untracked, and sitting in `docs/` rather than `docs/operational/reviews/`
  where the repo's own convention puts it. Move it, track it, and write its
  `*-status.md` disposition per the Recommendation Assessment mandate —
  merging with this review's overlapping items so the two don't spawn two
  parallel backlogs. (This review file already lives there and is indexed
  in `docs/operational/INDEX.md`.)

### Later (P2)

- **F-12 — Endorsed from the GPT review, correctly prioritized as
  post-evidence work:** state-schema migration contract before v2 fields
  land (F-05's `previous_hooks_path` is the natural trigger), decoupling
  package materialization from writable git state, install-time
  strict-enforcement policy (`--coverage-unsupported fail|warn|skip`),
  install/uninstall property tests (unrelated consumer files stay
  byte-identical), a threat model for untrusted instruction content, and
  Windows/macOS validation before claiming portability.
- **F-13 — Write the comparison/migration story (ROADMAP P2-08).** After
  one dogfood exists, "when to use this vs. a single CLAUDE.md vs. a
  plugin" becomes writable from experience instead of theory — and it's
  the doc a prospective adopter actually needs first.

## Suggested sequence

1. **Stabilize (hours):** F-01, F-02 — green gate, no self-contradicting
   safety policy. Both are small.
2. **Make the installer safe (a day):** F-03, F-04, F-05 with their
   acceptance tests. Release nothing before these.
3. **Prove (the real milestone):** F-08, with F-06/F-11 folded into the
   same working period. One dogfooded repo + one live Codex session +
   corrected docs is the "credible v0.3" bar.
4. **Only then expand** — and per F-07, without commissioning review #6
   first.

## Verification record

Independently performed at `4f3e94b` (working tree stashed for the run):

- `tools/check.sh --offline`: **exit 1** — `generate-agents-md` drift test
  failed; pre-push aggregate suite failed in consequence.
- `tools/generate-agents-md.sh` output vs. committed `AGENTS.md`: **drift
  confirmed** (commit `4f3e94b`'s "Reply to every comment" wording never
  regenerated).
- `.claude/skills/` inventory: **7 skills** vs. STATUS.md's claim of 6.
- `harness-link.sh:1668` (`cmd_generate_clients`): **no existence check,
  backup, or force gate** before writing consumer files — read directly.
- `harness-link.sh:323` (`copy_npm_durable_source`): **tar of entire
  source minus `.git`** — untracked-secret copy path confirmed by reading;
  safety assumption exists only as a comment.
- `harness-link.sh` state fields: hooks path recorded, **no previous-value
  field** — restore-on-uninstall impossible as implemented.
- `committing` skill vs. CLAUDE.md/COMMITTING_GUIDELINES.md: **publish
  contradiction confirmed** in body and frontmatter description, present
  identically in `.agents/skills/` (symlink) and `.cursor/rules/`.
- `--with-coverage-hook`: implemented in `harness-link.sh` (help text,
  state field, generator marker at line 382); **unmentioned or
  contradicted** in STATUS.md, KNOWN_LIMITATIONS.md, and
  `patterns/profiles/README.md`.
- Python suites (observed inside the check run): logging 37 passed
  (99.45%), agent loop 9 passed (100%), eval tools 15 passed (87.5%).

This review is an assessment; no findings were fixed as part of it.
