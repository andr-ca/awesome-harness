---
date: 2026-07-16
last_updated: 2026-07-17
author: AI agent (GitHub Copilot, Claude Sonnet 4.6)
topic: status
purpose: Progress tracking for public-launch readiness plan
related: docs/operational/planning/public-launch-readiness-2026-07-16.md
---

# Public-Launch Readiness — Implementation Status

Tracks progress against
[public-launch-readiness-2026-07-16.md](./public-launch-readiness-2026-07-16.md).

## Legend

| Symbol | Meaning |
|---|---|
| ✅ | Complete — acceptance tests pass |
| 🔄 | In progress |
| ❌ | Not started |
| ⏸ | Blocked / requires owner action |

---

## Workstream 0 — Clearance record

| Item | Status | Notes |
|---|---|---|
| Employer policy confirmation | ⏸ | Requires owner to record determination in a dated personal note outside this repo |

---

## Workstream A — Close P0s

| Item | Status | Notes |
|---|---|---|
| F-01 automation caveat | ❌ | Addendum item 5: re-verify adapter-drift CI check is green in a clean checkout and formally close F-01’s “no automation” caveat in the disposition doc |
| F-02 committing skill | ✅ | Updated `.claude/skills/committing/SKILL.md`: removed 'commit → push → PR mandatory', replaced with completion-gate + publish-authority model |
| F-03 generate-clients safety | ✅ | Added `_gc_is_harness_generated()` + `_gc_check_file()`; non-harness files are skipped (with message); `--force` overwrites with warning; `--dry-run` shows plan; 4 new tests (12 total) |
| F-04 npm durable copy `.env*` | ✅ | `copy_npm_durable_source` now explicitly excludes `.env`, `.env.*`, `*.env`, `node_modules`, `__pycache__`, `*.pyc`, `.worktrees` |
| F-05 hooks path restoration | ✅ | `state_write` now records `previous_hooks_path`; `cmd_uninstall` restores it on uninstall (or unsets if no previous value was recorded) |
| Disposition wrap-up | ✅ | fable-gpt5-sol-disposition-2026-07-14.md F-02–F-05 entries updated to DONE with PR references; stale What/Action/Estimate blocks removed |
| F-01 automation caveat | ❌ | Addendum item 5: re-verify adapter-drift CI check is green in a clean checkout and formally close F-01’s “no automation” caveat in the disposition doc |

---

## Workstream E — Release integrity

| Item | Status | Notes |
|---|---|---|
| E1 label core experimental | ✅ | STATUS.md labels the core experimental/unreleased (PR #65). MANIFEST.md was **not** labeled by PR #65 despite this row's original claim — caught by the 2026-07-17 session-3 audit; `manifest.yaml` row for `src/agentharness/` added and MANIFEST.md regenerated 2026-07-17 |
| E2 reconcile versions | 🔄 | STATUS.md acknowledges the gap; versions now npm `v0.2.1` / pyproject `0.1.1` (still split, experimental status documented); full reconciliation + tagging deferred to post-launch (E2 is a label issue, not a breakage) |
| E3 dedupe acceptance verifiers | ✅ | Removed `tools/acceptance/verify_matrix.py` (underscore variant); `verify-matrix.py` is canonical |
| E4 check.sh parity | ✅ | `tools/check.sh` now runs `pytest tests/ --cov=src/agentharness --cov-fail-under=65` with same excludes as `check-completion.sh` |
| E5 SECURITY.md refresh | ✅ | SECURITY.md now covers: npm distribution, git-config mutations, GitHub protection boundary, private reporting advisory; logged 2026-07-16 but status table was not updated at the time |
| E6 setuptools CVE fix | ✅ | `pyproject.toml` and `requirements-dev.txt` bumped to `setuptools>=83.0.0` (CVE-2026-59890) |
| E7 secret/history scan | ⏸ | Requires owner to run gitleaks or trufflehog and record result |
| E8 RC smoke test | ⏸ | Requires clean environment: install packed npm artifact into a clean repo, exercise init/generate/update/doctor/uninstall, confirm current remote CI green. Owner-triggered. (Addendum E.8 + “clean-clone/packed-artifact/current-CI verification” from expanded DoD) |
| E9 prune .worktrees/ from markdown scan | ✅ | `tools/verify-content-quality.py` markdown rglob now skips `.worktrees/` parts the same way the YAML scan skips excluded dirs |

---

## Workstream D — Dogfood evidence

| Item | Status | Notes |
|---|---|---|
| Recalium dogfood run | ⏸ | Requires owner; procedure in DOGFOODING.md |
| Evidence bundle | ⏸ | Blocked on run |
| KNOWN_LIMITATIONS.md update | ⏸ | Blocked on run |

---

## Workstream C — Doc accuracy sweep

| Item | Status | Notes |
|---|---|---|
| STATUS.md re-verification | ✅ | Full row-by-row sweep completed via PR #74 (2026-07-17); STATUS.md now reads "Last verified against the tree: 2026-07-17 (commit `af36f2c`)" |
| KNOWN_LIMITATIONS.md re-verification | ❌ | Pending dogfood (D) and A/E items |
| F-07 archive review cycles | ✅ | Created `docs/operational/reviews/README.md` — cycle-by-cycle index (5 named cycles, all 16 files described); INDEX.md updated to reference it. Files kept flat to preserve cross-references |

---

## Workstream B — Front door

| Item | Status | Notes |
|---|---|---|
| Repo description | ✅ | Set to 'Portable engineering policies for coding agents — git, testing, logging, and language conventions written once and referenced everywhere' via `gh repo edit` |
| Topics | ✅ | Set: `ai-agents`, `claude-code`, `coding-agents`, `agent-skills`, `developer-tools` |
| Homepage | ✅ | Set to `https://andr.ca/agentharness` |
| README restructure | ✅ | Inserted '## What makes this different' section (3 governance mechanisms + DEMO.md link) before compatibility matrices; condensed duplicate governance text in Product Contract |
| Naming line | ✅ | Added '*Repository:* `agentharness` · *npm package:* `agentharness-toolkit`' immediately below the pitch paragraph |
| Provenance headers in generators | ✅ | All 11 generators now emit `(https://github.com/andr-ca/agentharness)` in their 'do not hand-edit' notice; all 18 generated output files regenerated |

---

## Addendum DoD gates (not in original workstreams)

From the Session 3 expanded definition of done in the plan file; no tracker row existed for these.

| Item | Status | Notes |
|---|---|---|
| Article factual/adversarial review | ⏸ | External pre-publish gate — owner reviews the article for accuracy, unmeasured efficacy claims, and employer implication before it links to this repo |

---

## Summary

| Workstream | ✅ | 🔄 | ❌ | ⏸ |
|---|---|---|---|---|
| 0 — Clearance | 0 | 0 | 0 | 1 |
| A — P0 fixes | 5 | 0 | 1 | 0 |
| E — Release integrity | 6 | 1 | 0 | 2 |
| D — Dogfood | 0 | 0 | 0 | 3 |
| C — Doc accuracy | 2 | 0 | 1 | 0 |
| B — Front door | 6 | 0 | 0 | 0 |
| Addendum DoD | 0 | 0 | 0 | 1 |
| **Total** | **19** | **1** | **2** | **7** |

---

## Implementation log

| Date | Item | Action |
|---|---|---|
| 2026-07-16 | Status file | Created; initial assessment of all items against HEAD |
| 2026-07-16 | F-02 | Fixed committing skill — opt-in publish authority model |
| 2026-07-16 | F-04 | npm durable copy now excludes .env*, caches, pyc files |
| 2026-07-16 | F-05 | Persist + restore previous_hooks_path on uninstall |
| 2026-07-16 | E1 | Experimental labels added to MANIFEST.md, STATUS.md |
| 2026-07-16 | E3 | Removed duplicate verify_matrix.py (underscore variant) |
| 2026-07-16 | E4 | check.sh now runs bootstrap policy pytest with coverage gate |
| 2026-07-16 | E6 | setuptools bumped to >=83.0.0 (CVE-2026-59890) |
| 2026-07-16 | E9 | verify-content-quality.py now prunes .worktrees/ from markdown scan |
| 2026-07-16 | C partial | STATUS.md last-verified date updated to 2026-07-16 |
| 2026-07-16 | F-03 | generate-clients: existence check, --force, --dry-run, provenance detection (4 new tests) |
| 2026-07-16 | E5 | SECURITY.md: added npm distribution, git config mutations, GitHub protection, supported boundary |
| 2026-07-16 | One-branch enforcement | feat: PR #68 — enforce multi-agent mutex; branch-keyed push locks, Claude Code PreToolUse guard, updated CLAUDE.md/AGENTS.md/GEMINI.md (4 new bats tests, docs, adapters regen) |
| 2026-07-17 | F-07 | Created `docs/operational/reviews/README.md`; INDEX.md updated to reference it |
| 2026-07-17 | B: README restructure | Inserted '## What makes this different' section; naming line added; governance text de-duplicated |
| 2026-07-17 | B: Provenance headers | All 11 generators + 18 generated files updated with GitHub URL |
| 2026-07-17 | B: GitHub metadata | Description, 5 topics, homepage set via `gh repo edit` |
| 2026-07-17 | check-completion.sh | Aligned shellcheck to `-S warning` (consistent with check.sh; pre-existing SC1091 info messages) |
| 2026-07-17 | Session 3: audit | Independent re-verification of all ✅ claims against `main` (`96ef3be`); findings appended as "Session 3" in the plan file (PR #75) |
| 2026-07-17 | Session 3: E1 fix | Added `src/agentharness/` EXPERIMENTAL row to `manifest.yaml`, regenerated MANIFEST.md — closing the half of E1 the original ✅ claimed but never shipped |
| 2026-07-17 | A: Disposition wrap-up | fable-gpt5-sol-disposition-2026-07-14.md F-02–F-05 updated to ✅ DONE with PR references; stale action/estimate blocks removed |
| 2026-07-17 | Status doc | Added F-01 automation caveat row, expanded E8 scope, added Addendum DoD section with article review gate; updated summary totals |
